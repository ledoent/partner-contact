# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Contact Deduplication Review",
    "summary": "Review duplicate contacts and merge them without losing followers",
    "version": "20.0.1.0.0",
    "author": "Ledo Enterprises, Odoo Community Association (OCA)",
    "maintainers": ["dnplkndll"],
    "development_status": "Alpha",
    "website": "https://github.com/OCA/partner-contact",
    "category": "Productivity/Data Cleaning",
    "license": "AGPL-3",
    "depends": ["base_deduplicate_review", "contacts"],
    "data": [
        "data/deduplicate_rule_data.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
}
