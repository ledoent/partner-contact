# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestLedgerGuard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.keep = Partner.create({"name": "PDA Keep"})
        cls.gone = Partner.create({"name": "PDA Gone"})
        cls.invoice = cls._create_invoice(partner_id=cls.gone, post=True)

    def merge(self, master, sources, **ctx):
        return (
            self.env["res.partner"]
            .with_context(**ctx)
            ._deduplicate_merge(master, sources)
        )

    def test_another_customers_posted_items_are_refused(self):
        with self.assertRaisesRegex(UserError, "journal items"):
            self.merge(self.keep, self.gone)
        self.assertTrue(self.gone.exists())
        self.assertEqual(self.invoice.partner_id, self.gone)

    def test_a_contact_of_the_merged_customer_counts_too(self):
        contact = self.env["res.partner"].create(
            {"name": "PDA Contact", "parent_id": self.keep.id}
        )
        other = self.env["res.partner"].create({"name": "PDA Other"})
        child = self.env["res.partner"].create(
            {"name": "PDA Child", "parent_id": other.id}
        )
        self._create_invoice(partner_id=child, post=True)
        with self.assertRaisesRegex(UserError, "journal items"):
            self.merge(contact, other)

    def test_accounting_can_allow_it_explicitly(self):
        self.merge(self.keep, self.gone, deduplicate_allow_ledger_move=True)
        self.assertFalse(self.gone.exists())
        self.assertEqual(self.invoice.partner_id, self.keep)

    def test_contacts_of_one_customer_merge_freely(self):
        one = self.env["res.partner"].create(
            {"name": "PDA One", "parent_id": self.keep.id}
        )
        two = self.env["res.partner"].create(
            {"name": "PDA Two", "parent_id": self.keep.id}
        )
        self._create_invoice(partner_id=two, post=True)
        self.merge(one, two)
        self.assertFalse(two.exists())

    def test_draft_items_do_not_block(self):
        draft_only = self.env["res.partner"].create({"name": "PDA Draft"})
        self._create_invoice(partner_id=draft_only, post=False)
        self.merge(self.keep, draft_only)
        self.assertFalse(draft_only.exists())
