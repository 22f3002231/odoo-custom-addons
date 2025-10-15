# -*- coding: utf-8 -*-
# FILE: tradeindia_integration/models/tradeindia_fetch_leads_wizard.py

import requests
import logging
from datetime import datetime, timedelta
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
import urllib.parse

_logger = logging.getLogger(__name__)

class TradeIndiaFetchLeadsWizard(models.TransientModel):
    _name = 'tradeindia.fetch.leads.wizard'
    _description = 'TradeIndia Fetch Leads Wizard'

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.today()
    )
    end_date = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: fields.Date.today()
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError("Start Date must be before End Date.")
            if (record.end_date - record.start_date).days > 0:
                raise ValidationError("Date range cannot exceed 1 day due to API limitations.")

    def action_fetch_leads(self):
        '''Manual fetch - NO duplicate check'''
        log_vals = {'is_manual': True}
        errors = []
        
        try:
            settings = self.env['tradeindia.settings'].search([], limit=1)
            if not settings or not settings.userid or not settings.profile_id or not settings.api_key:
                raise UserError("API credentials not configured.")

            start_str = self.start_date.strftime('%Y-%m-%d')
            end_str = self.end_date.strftime('%Y-%m-%d')
            
            _logger.info(f"=== Manual Fetch: {start_str} to {end_str} ===")
            
            api_url = "https://www.tradeindia.com/utils/my_inquiry.html"
            params = {
                'userid': settings.userid,
                'profile_id': settings.profile_id,
                'key': settings.api_key,
                'from_date': start_str,
                'to_date': end_str,
                'limit': 100
            }

            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            leads_data = data if isinstance(data, list) else []
            
            total_received = len(leads_data)
            log_vals['leads_fetched'] = total_received
            _logger.info(f"API returned {total_received} leads")

            new_leads_count = 0
            skipped_no_id = 0
            Lead = self.env['crm.lead']
            
            for idx, lead in enumerate(leads_data, 1):
                unique_id = lead.get('rfi_id')
                sender_name = lead.get('sender_name', 'Unknown')
                
                if not unique_id:
                    skipped_no_id += 1
                    errors.append(f"{sender_name}: No RFI ID")
                    continue

                product_name = lead.get('product_name') or lead.get('subject', 'Inquiry')
                
                vals = {
                    'type': 'lead',
                    'name': f"{sender_name} - {product_name}",
                    'tradeindia_unique_id': str(unique_id),
                    'contact_name': sender_name,
                    'probability': 50,
                    'user_id': False,
                    'team_id': False,
                    'x_lead_source': 'TradeIndia',
                }
                
                if lead.get('sender_co'):
                    vals['partner_name'] = lead.get('sender_co')
                if lead.get('sender_email'):
                    vals['email_from'] = lead.get('sender_email')
                if lead.get('sender_mobile'):
                    phone = lead.get('sender_mobile', '').replace('<a href="tel:', '').replace('">', '').replace('</a>', '').strip()
                    if phone:
                        vals['phone'] = phone
                if lead.get('sender_city'):
                    vals['city'] = lead.get('sender_city')
                if lead.get('address'):
                    vals['street'] = lead.get('address')
                
                if lead.get('sender_state'):
                    state = self.env['res.country.state'].search([('name', '=', lead.get('sender_state'))], limit=1)
                    if state:
                        vals['state_id'] = state.id
                
                if lead.get('sender_country'):
                    country = self.env['res.country'].search([('name', '=', lead.get('sender_country'))], limit=1)
                    if country:
                        vals['country_id'] = country.id
                
                inquiry_date = f"{lead.get('generated_date', 'N/A')} {lead.get('generated_time', '')}"
                vals['description'] = (
                    f"TradeIndia Lead\n{'='*50}\n"
                    f"Product: {product_name}\n"
                    f"Subject: {lead.get('subject', 'N/A')}\n"
                    f"Message: {lead.get('message', 'N/A')}\n\n"
                    f"Date/Time: {inquiry_date}\n"
                    f"Source: {lead.get('source', 'N/A')}\n"
                    f"Type: {lead.get('inquiry_type', 'N/A')}\n"
                    f"Location: {lead.get('sender_city', '')}, {lead.get('sender_state', '')}\n"
                    f"RFI ID: {unique_id}\n"
                )
                
                try:
                    new_lead = Lead.with_context(
                        default_user_id=False,
                        default_team_id=False,
                        mail_create_nosubscribe=True,
                    ).create(vals)
                    new_leads_count += 1
                    _logger.info(f"✓ Created lead {idx}/{total_received}: {sender_name} (ID: {new_lead.id})")
                except Exception as e:
                    errors.append(f"{sender_name}: {str(e)[:50]}")
                    _logger.error(f"✗ Failed: {str(e)}")

            summary = (
                f"API returned {total_received} leads\n"
                f"✓ Created: {new_leads_count}\n"
                f"⊗ Skipped (No ID): {skipped_no_id}\n"
                f"✗ Failed: {len(errors)}"
            )
            
            if errors and len(errors) <= 5:
                summary += "\n\nErrors:\n" + "\n".join(errors)
            
            log_vals.update({
                'status': 'success' if new_leads_count > 0 else 'failure',
                'leads_created': new_leads_count,
                'response_message': summary
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Fetch Complete',
                    'message': summary,
                    'type': 'success' if new_leads_count > 0 else 'warning',
                    'sticky': True
                }
            }

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Fetch failed: {error_msg}", exc_info=True)
            log_vals.update({'status': 'failure', 'response_message': error_msg})
            raise UserError(f"Fetch failed: {error_msg}")
        finally:
            self.env['tradeindia.api.log'].create(log_vals)