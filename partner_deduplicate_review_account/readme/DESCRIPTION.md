Installed automatically with *Contact Deduplication Review* and *Invoicing*.

A contact merge that would move **posted journal items between two
different customers** is refused: merging two customers rewrites one ledger
into the other, including the items of the merged customer's contacts, whose
commercial entity changes with it. That is a decision for accounting.

Contacts of the same customer merge as usual. To allow a cross-customer merge
deliberately, pass `deduplicate_allow_ledger_move=True` in the context.
