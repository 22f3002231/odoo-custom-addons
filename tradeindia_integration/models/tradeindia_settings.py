# -*- coding: utf-8 -*-
# FILE: tradeindia_integration/models/tradeindia_settings.py

import requests
import logging
from datetime import datetime, timedelta
from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class TradeIndiaSettings(models.Model):
    _name = 'tradeindia.settings'
    _description = 'TradeIndia API Settings'

    name = fields.Char(default='TradeIndia API Configuration', readonly=True, required=True)
    userid = fields.Char(string="User ID", help="Your TradeIndia User ID")
    profile_id = fields.Char(string="Profile ID", help="Your TradeIndia Profile ID")
    api_key = fields.Char(string="API Key", help="Your TradeIndia API Key")

    def action_test_connection(self):
        self.ensure_one()
        if not self.userid or not self.profile_id or not self.api_key:
            raise UserError("Please enter all required fields before testing.")
        
        api_url = "https://www.tradeindia.com/utils/my_inquiry.html"
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'userid': self.userid,
            'profile_id': self.profile_id,
            'key': self.api_key,
            'from_date': today_str,
            'to_date': today_str,
            'limit': 10
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful!',
                    'message': f"✓ Connected!\n\nFound {count} inquiries for today.",
                    'type': 'success',
                    'sticky': False
                }
            }
        except Exception as e:
            raise UserError(f"Connection failed: {e}")

    @api.model
    def _run_scheduled_fetch(self):
        '''Cron job - runs every 5 minutes to fetch NEW leads only'''
        _logger.info("=== TradeIndia Scheduled Fetch Started ===")
        log_vals = {'is_manual': False}
        
        try:
            settings = self.env['tradeindia.settings'].search([], limit=1)
            if not settings or not settings.userid or not settings.profile_id or not settings.api_key:
                raise Exception("API credentials not configured")

            today_str = datetime.now().strftime('%Y-%m-%d')
            _logger.info(f"Fetching NEW leads for: {today_str}")
            
            api_url = "https://www.tradeindia.com/utils/my_inquiry.html"
            params = {
                'userid': settings.userid,
                'profile_id': settings.profile_id,
                'key': settings.api_key,
                'from_date': today_str,
                'to_date': today_str,
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
            skipped_duplicates = 0
            
            if leads_data:
                Lead = self.env['crm.lead']
                
                # Get or create TradeIndia source
                tradeindia_source = self.env['utm.source'].search([('name', '=', 'TradeIndia')], limit=1)
                if not tradeindia_source:
                    tradeindia_source = self.env['utm.source'].create({'name': 'TradeIndia'})
                tradeindia_source_id = tradeindia_source.id
                
                for lead in leads_data:
                    unique_id = lead.get('rfi_id')
                    sender_name = lead.get('sender_name', 'Unknown')
                    
                    if not unique_id:
                        skipped_no_id += 1
                        _logger.warning(f"» Skipped: {sender_name} - No RFI ID")
                        continue

                    # Check for duplicates
                    existing_lead = Lead.search([('tradeindia_unique_id', '=', str(unique_id))], limit=1)
                    if existing_lead:
                        skipped_duplicates += 1
                        _logger.info(f"» Duplicate: {sender_name} (ID: {unique_id}) - Already exists as Lead #{existing_lead.id}")
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
                        'source_id': tradeindia_source_id,  # ADDED: Use source_id field
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
                        _logger.info(f"✓ Created: {sender_name} - {product_name} (Lead ID: {new_lead.id})")
                    except Exception as e:
                        _logger.error(f"✗ Failed to create lead for {sender_name}: {str(e)}")
            
            message = f"Created {new_leads_count} new leads (API returned {total_received}, {skipped_duplicates} duplicates, {skipped_no_id} without ID)"
            log_vals.update({
                'status': 'success',
                'leads_created': new_leads_count,
                'response_message': message
            })
            _logger.info(f"✓ {message}")

        except Exception as e:
            log_vals.update({'status': 'failure', 'response_message': str(e)})
            _logger.error(f"✗ Failed: {e}", exc_info=True)
        finally:
            self.env['tradeindia.api.log'].create(log_vals)