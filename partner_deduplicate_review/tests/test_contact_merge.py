# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestContactMerge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.reviewer = new_test_user(
            cls.env,
            login="pdr_reviewer",
            groups="base.group_user,base_deduplicate_review.group_deduplicate_reviewer",
        )
        cls.manager = new_test_user(
            cls.env,
            login="pdr_manager",
            groups="base.group_user,base_deduplicate_review.group_deduplicate_manager",
        )
        cls.Partner = cls.env["res.partner"]

    def setUp(self):
        super().setUp()
        self.master = self.Partner.create(
            {"name": "PD Keep", "email": "keep@example.com"}
        )
        self.source = self.Partner.create(
            {"name": "PD Gone", "email": "gone@example.com"}
        )

    def merge(self, master=None, sources=None):
        return self.Partner._deduplicate_merge(
            master or self.master, sources or self.source
        )

    def test_following_a_shared_document_does_not_wipe_other_follows(self):
        """Core alone deletes EVERY follower row of the source as soon as one
        collides; here only the colliding one goes."""
        shared = self.Partner.create({"name": "PD Shared"})
        only = self.Partner.create({"name": "PD Only the source"})
        shared.message_subscribe(partner_ids=(self.master | self.source).ids)
        only.message_subscribe(partner_ids=self.source.ids)
        self.merge()
        self.assertIn(self.master, only.message_partner_ids)
        self.assertEqual(
            self.env["mail.followers"].search_count(
                [
                    ("res_model", "=", "res.partner"),
                    ("res_id", "=", shared.id),
                    ("partner_id", "=", self.master.id),
                ]
            ),
            1,
        )

    def test_a_shared_notification_does_not_abort_the_merge(self):
        """mail_notification is protected by a unique INDEX, not a constraint;
        core runs a bare UPDATE into it and the transaction aborts."""
        message = self.Partner.create({"name": "PD Doc"}).message_post(body="hi")
        for partner in self.master | self.source:
            self.env["mail.notification"].create(
                {
                    "mail_message_id": message.id,
                    "res_partner_id": partner.id,
                    "notification_type": "inbox",
                }
            )
        self.merge()
        self.assertEqual(
            self.env["mail.notification"].search_count(
                [("mail_message_id", "=", message.id)]
            ),
            1,
        )

    def test_more_contacts_than_the_core_limit_merge_in_chunks(self):
        sources = self.Partner.create(
            [{"name": f"PD Gone {n}", "email": f"g{n}@example.com"} for n in range(4)]
        )
        children = self.Partner.create(
            [{"name": f"PD Kid {n}", "parent_id": s.id} for n, s in enumerate(sources)]
        )
        self.merge(sources=sources)
        self.assertFalse(sources.exists())
        self.assertEqual(children.parent_id, self.master)

    def test_references_the_core_merge_misses_are_repointed(self):
        recycle = self.env["data_recycle.model"].create(
            {
                "name": "PD recycle",
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        suggestion = self.env["data_recycle.record"].create(
            {"recycle_model_id": recycle.id, "res_id": self.source.id}
        )
        self.merge()
        self.assertEqual(suggestion.res_id, self.master.id)

    def test_the_core_merge_and_its_log_still_run(self):
        self.merge()
        self.assertFalse(self.source.exists())
        self.assertTrue(
            any(
                "Merged with the following partners" in (m.body or "")
                for m in self.master.message_ids
            )
        )

    def test_different_e_mails_are_not_a_refusal(self):
        # core's extra check (identical e-mails) is the reviewer's job here
        self.merge()
        self.assertEqual(self.master.email, "keep@example.com")

    def test_the_core_refusal_of_a_parent_child_merge_still_applies(self):
        child = self.Partner.create({"name": "PD Child", "parent_id": self.master.id})
        with self.assertRaises(UserError):
            self.merge(sources=child)

    def test_identifiers_of_the_merged_contact_are_kept(self):
        self.source.ref = "EXT-77"
        with patch.object(
            type(self.Partner), "_deduplicate_alias_fields", lambda self: ["ref"]
        ):
            self.merge()
        self.assertEqual(
            self.env["deduplicate.alias"].resolve_identifiers(
                "res.partner", "ref", ["EXT-77"]
            ),
            {"EXT-77": self.master.id},
        )

    def test_contact_rules_always_delete(self):
        with self.assertRaises(ValidationError):
            self.env["deduplicate.rule"].create(
                {
                    "name": "PD archive",
                    "res_model_id": self.env["ir.model"]._get("res.partner").id,
                    "merge_action": "archive",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "field_id": self.env["ir.model.fields"]
                                ._get("res.partner", "email")
                                .id,
                                "match_mode": "email",
                            },
                        )
                    ],
                }
            )

    def test_the_review_flow_merges_contacts_without_any_override(self):
        twin = self.Partner.create({"name": "PD Keep", "email": "KEEP@example.com"})
        rule = self.env.ref("partner_deduplicate_review.rule_contact_email")
        self.assertFalse(rule.active)
        rule.write({"active": True, "domain": "[('name', '=like', 'PD %')]"})
        rule._find_duplicates()
        group = self.env["deduplicate.group"].search(
            [("rule_id", "=", rule.id), ("record_ids.res_id", "=", twin.id)]
        )
        self.assertEqual(
            set(group.record_ids.mapped("res_id")), {self.master.id, twin.id}
        )
        group.with_user(self.reviewer).action_validate()
        group.with_user(self.manager).action_merge()
        self.assertEqual(group.state, "merged")
        self.assertFalse(twin.exists())

    def test_selected_contacts_can_be_sent_to_review(self):
        action = (
            (self.master | self.source)
            .with_user(self.reviewer)
            ._deduplicate_review_selection()
        )
        group = self.env["deduplicate.group"].browse(action["res_id"])
        self.assertEqual(group.source, "manual")
        self.assertEqual(len(group.record_ids), 2)
