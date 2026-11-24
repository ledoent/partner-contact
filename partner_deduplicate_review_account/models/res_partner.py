# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError

ALLOW_LEDGER_CONTEXT = "deduplicate_allow_ledger_move"


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _deduplicate_check_merge(self, master, sources):
        """Refuse a merge that moves posted journal items to another customer.

        Merging two contacts of one customer leaves its ledger alone. Merging
        two *customers* rewrites one ledger into the other: every posted
        journal item of the merged customer -- and of its contacts, whose
        commercial entity changes with it -- now reads as the kept customer's.
        That is an accounting decision, so it is refused unless the caller
        passes ``deduplicate_allow_ledger_move`` in the context.
        """
        res = super()._deduplicate_check_merge(master, sources)
        if self.env.context.get(ALLOW_LEDGER_CONTEXT):
            return res
        foreign = sources.filtered(
            lambda p: p.commercial_partner_id != master.commercial_partner_id
        )
        if not foreign:
            return res
        count = (
            self.env["account.move.line"]
            .sudo()
            .search_count(
                [
                    ("partner_id", "child_of", foreign.ids),
                    ("parent_state", "=", "posted"),
                ]
            )
        )
        if count:
            raise UserError(
                self.env._(
                    "Merging %(names)s into %(master)s would move %(count)s posted "
                    "journal items to another customer's ledger. Ask accounting "
                    "to review it first.",
                    names=", ".join(foreign.mapped("display_name")),
                    master=master.display_name,
                    count=count,
                )
            )
        return res
