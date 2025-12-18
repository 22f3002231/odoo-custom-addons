from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'user_id' not in vals or not vals.get('user_id'):
                vals['user_id'] = self.env.user.id
        return super(ResPartner, self).create(vals_list)
