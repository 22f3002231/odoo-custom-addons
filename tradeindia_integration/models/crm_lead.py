# -*- coding: utf-8 -*-
# FILE: tradeindia_integration/models/crm_lead.py

from odoo import fields, models

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Set the default sorting for all leads to show newest first
    _order = 'create_date desc'

    tradeindia_unique_id = fields.Char(
        string="TradeIndia Unique ID",
        readonly=True,
        index=True,
        help="Unique inquiry ID from TradeIndia"
    )

    # Add a new field to store the lead source
    x_lead_source = fields.Char(string="Source", readonly=True, index=True)