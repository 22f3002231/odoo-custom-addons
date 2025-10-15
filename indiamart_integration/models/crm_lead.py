# -*- coding: utf-8 -*-
from odoo import fields, models

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    indiamart_unique_id = fields.Char(string="IndiaMART Unique ID", readonly=True, index=True)
    
    # ADD THIS NEW FIELD
    indiamart_query_type = fields.Selection(
        [
            ('W', 'Direct Enquiry'),
            ('B', 'Buy-Lead'),
            ('P', 'PNS Call'),
            ('BIZ', 'Catalog View'),
            ('WA', 'WhatsApp Enquiry')
        ],
        string="IndiaMART Lead Type",
        readonly=True
    )