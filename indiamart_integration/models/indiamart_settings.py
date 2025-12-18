# -*- coding: utf-8 -*-
# FILE: indiamart_integration/models/indiamart_settings.py

import requests
import logging
from datetime import datetime, timedelta
from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class IndiaMARTSettings(models.Model):
    _name = 'indiamart.settings'
    _description = 'IndiaMART API Settings'

    name = fields.Char(default='IndiaMART API Configuration', readonly=True, required=True)
    api_key = fields.Char(string="IndiaMART API Key", help="The Pull API Key from IndiaMART seller panel.")

    def action_test_connection(self):
        self.ensure_one()
        if not self.api_key:
            raise UserError("Please enter an IndiaMART API Key before testing.")
            
        api_url = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"
        params = {'glusr_crm_key': self.api_key}
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('STATUS') == 'FAILURE':
                raise UserError(f"IndiaMART API Error:\n\n{data.get('MESSAGE')}")
                
            success_message = data.get('MESSAGE', 'Successfully connected!')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful!',
                    'message': success_message,
                    'type': 'success',
                    'sticky': False
                }
            }
        except requests.exceptions.RequestException as e:
            raise UserError(f"Network error: {e}")
        except ValueError:
            raise UserError("Invalid response from IndiaMART API.")

    @api.model
    def _run_scheduled_fetch(self):
        '''Cron job - runs every 5 minutes using API's built-in last-24h logic'''
        _logger.info("=== IndiaMART Scheduled Fetch Started ===")
        log_vals = {'is_manual': False}
        
        try:
            settings = self.env['indiamart.settings'].search([], limit=1)
            if not settings or not settings.api_key:
                raise Exception("API Key not configured")

            _logger.info("Fetching NEW leads (API will return leads since last API call)")
            
            # Use the simple approach: API without start_time and end_time
            # This automatically returns leads from the last 24 hours,
            # or from last API call if called within 24 hours
            api_url = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"
            params = {
                'glusr_crm_key': settings.api_key
                # No start_time or end_time needed!
            }

            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('STATUS') == 'FAILURE':
                raise Exception(f"IndiaMART API Error: {data.get('MESSAGE')}")

            leads_data = data.get('RESPONSE', [])
            total_received = len(leads_data)
            log_vals['leads_fetched'] = total_received
            
            _logger.info(f"API returned {total_received} leads")

            new_leads_count = 0
            failed_count = 0
            
            if leads_data:
                Lead = self.env['crm.lead']
                
                # Get or create IndiaMART source
                indiamart_source = self.env['utm.source'].search([('name', '=', 'IndiaMART')], limit=1)
                if not indiamart_source:
                    indiamart_source = self.env['utm.source'].create({'name': 'IndiaMART'})
                indiamart_source_id = indiamart_source.id
                
                for lead in leads_data:
                    unique_id = lead.get('UNIQUE_QUERY_ID')
                    sender_name = lead.get('SENDER_NAME', 'Unknown')
                    
                    if not unique_id:
                        _logger.warning(f"» Skipped: {sender_name} - No UNIQUE_QUERY_ID")
                        continue

                    query_type = lead.get('QUERY_TYPE')
                    probability_map = {'P': 75, 'W': 50, 'WA': 40, 'B': 25, 'BIZ': 10}
                    
                    vals = {
                        'type': 'lead',
                        'name': f"{sender_name} - {lead.get('SUBJECT', 'Inquiry')}",
                        'indiamart_unique_id': unique_id,
                        'contact_name': sender_name,
                        'probability': probability_map.get(query_type, 10),
                        'user_id': False,
                        'team_id': False,
                        'source_id': indiamart_source_id,
                    }
                    
                    if lead.get('SENDER_COMPANY'):
                        vals['partner_name'] = lead.get('SENDER_COMPANY')
                    if lead.get('SENDER_EMAIL'):
                        vals['email_from'] = lead.get('SENDER_EMAIL')
                    if lead.get('SENDER_MOBILE'):
                        vals['phone'] = lead.get('SENDER_MOBILE')
                    if lead.get('SENDER_CITY'):
                        vals['city'] = lead.get('SENDER_CITY')
                    if lead.get('SENDER_ADDRESS'):
                        vals['street'] = lead.get('SENDER_ADDRESS')
                    if lead.get('SENDER_PINCODE'):
                        vals['zip'] = lead.get('SENDER_PINCODE')
                    
                    if lead.get('SENDER_STATE'):
                        state = self.env['res.country.state'].search([('name', '=', lead.get('SENDER_STATE'))], limit=1)
                        if state:
                            vals['state_id'] = state.id
                    
                    if lead.get('SENDER_COUNTRY_ISO'):
                        country = self.env['res.country'].search([('code', '=', lead.get('SENDER_COUNTRY_ISO'))], limit=1)
                        if country:
                            vals['country_id'] = country.id
                    
                    if query_type:
                        try:
                            vals['indiamart_query_type'] = query_type
                        except:
                            pass
                    
                    description = (
                        f"IndiaMART Lead\n{'='*50}\n"
                        f"Subject: {lead.get('SUBJECT', 'N/A')}\n"
                        f"Message: {lead.get('QUERY_MESSAGE', 'N/A')}\n\n"
                        f"Product: {lead.get('QUERY_PRODUCT_NAME', 'N/A')}\n"
                        f"Category: {lead.get('QUERY_MCAT_NAME', 'N/A')}\n"
                        f"Location: {lead.get('SENDER_CITY', '')}, {lead.get('SENDER_STATE', '')}\n"
                        f"Query Type: {query_type}\n"
                        f"Query Time: {lead.get('QUERY_TIME', 'N/A')}\n"
                        f"IndiaMART ID: {unique_id}\n"
                    )
                    vals['description'] = description
                    
                    try:
                        new_lead = Lead.with_context(
                            default_user_id=False,
                            default_team_id=False,
                            mail_create_nosubscribe=True,
                        ).create(vals)
                        new_leads_count += 1
                        _logger.info(f"✓ Created: {sender_name} (Lead ID: {new_lead.id})")
                    except Exception as e:
                        failed_count += 1
                        _logger.error(f"✗ Failed to create lead {unique_id}: {str(e)}")
            
            message = f"Created {new_leads_count} new leads (API returned {total_received} total)"
            if failed_count > 0:
                message += f", {failed_count} failed"
            
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
            self.env['indiamart.api.log'].create(log_vals)