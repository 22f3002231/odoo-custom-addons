# -*- coding: utf-8 -*-
from odoo import fields, models

class IndiaMARTApiLog(models.Model):
    _name = 'indiamart.api.log'
    _description = 'IndiaMART API Call Log'
    _order = 'request_time desc'

    name = fields.Char(string="Request", compute='_compute_name', store=True)
    request_time = fields.Datetime(string="Request Time", default=fields.Datetime.now, readonly=True)
    status = fields.Selection(
        [('success', 'Success'), ('failure', 'Failure')],
        string="Status",
        readonly=True
    )
    is_manual = fields.Boolean(string="Manual Fetch", readonly=True)
    leads_fetched = fields.Integer(string="Leads Fetched", readonly=True)
    leads_created = fields.Integer(string="Leads Created", readonly=True)
    response_message = fields.Text(string="API Response Message", readonly=True)

    def _compute_name(self):
        for log in self:
            log.name = f"Log @ {log.request_time}"