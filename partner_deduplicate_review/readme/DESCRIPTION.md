Duplicate contacts, reviewed and merged with the *Deduplication Review*
engine, through Odoo's own contact merge so every application's merge logic
still runs. Around it, the core merge's gaps are closed:

- **Followers and notifications survive.** When the contact kept and a
  merged one follow the same document, or were notified of the same message,
  the core merge deletes every follower row of the merged contact, or aborts
  when the table is protected by a unique index. Only the rows that genuinely
  duplicate the kept contact's are removed; all others move.
- **Any number of contacts.** The core merge takes three at a time; larger
  groups are merged in steps.
- **Every reference moves.** References the core merge does not know about
  (ratings, mailing traces, calendar events, scheduled messages, cleaning
  suggestions, any other `Many2oneReference`) are re-pointed too.
- **Identifiers stay resolvable**, through the engine's merged-record aliases.

It adds a *Duplicates* menu to Contacts, a *Review as Duplicates* action on
contact lists, and two inactive rules to start from: same e-mail, and same
name under the same company.
