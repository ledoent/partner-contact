# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Contacts merge through Odoo's own partner merge, with its gaps closed.

The core merge (``base.partner.merge.automatic.wizard._merge``) is kept on
purpose: every application hooks into it -- website visitors, loyalty cards,
course members, account ranks and the accounting audit, the chatter log -- and
a reimplementation would silently skip them. What it gets wrong is fixed
around it:

* When a moved row collides with one the record kept already has (both follow
  the same document, both were notified of the same message), it deletes
  *every* row of the source in that table, or aborts the transaction when the
  table only has a unique *index*. Before each core merge, only the rows that
  genuinely duplicate the kept record's are removed, so the core UPDATE moves
  all the others.
* It takes at most three contacts at a time; larger groups are merged in
  chunks.
* It re-points a handful of ``(model, res_id)`` references only; afterwards
  every other ``Many2oneReference`` and ``Reference`` field is re-pointed.
"""

from odoo import models
from odoo.tools import split_every

# The core merge takes the record kept plus at most two others.
CORE_CHUNK = 2


class ResPartner(models.Model):
    _inherit = "res.partner"

    _deduplicate_has_strategy = True

    def _deduplicate_merge_records(self, master, sources):
        wizard = self.env["base.partner.merge.automatic.wizard"]
        fks = wizard._get_fk_on(self._table)
        references = list(self._deduplicate_reference_fields())
        for chunk_ids in split_every(CORE_CHUNK, sources.ids):
            chunk = self.browse(chunk_ids)
            for source in chunk:
                self._deduplicate_drop_conflicts_everywhere(
                    fks, references, source.id, master.id
                )
            self.env.flush_all()
            wizard._merge((master | chunk).ids, dst_partner=master, extra_checks=False)
            for source_id in chunk_ids:
                self._deduplicate_repoint_references(references, source_id, master.id)
        self.env.invalidate_all()
        return {}

    def _deduplicate_log_merge(self, master, summary, aliases):
        # The core merge already logs the merge on the contact kept; add a note
        # only for the identifiers that now resolve to it.
        if aliases.identifier_ids:
            return super()._deduplicate_log_merge(master, summary, aliases)
