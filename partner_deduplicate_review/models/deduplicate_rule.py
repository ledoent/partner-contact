# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import ValidationError


class DeduplicateRule(models.Model):
    _inherit = "deduplicate.rule"

    @api.constrains("res_model_id", "merge_action")
    def _check_partner_merge_action(self):
        for rule in self:
            if rule.res_model_name == "res.partner" and rule.merge_action == "archive":
                raise ValidationError(
                    self.env._(
                        "Merged contacts are always deleted: the contact merge "
                        "removes them once everything has moved."
                    )
                )
