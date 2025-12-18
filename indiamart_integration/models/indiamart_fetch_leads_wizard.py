# -*- coding: utf-8 -*-
# FILE: indiamart_integration/models/indiamart_fetch_leads_wizard.py

import requests
import logging
from datetime import datetime, timedelta
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class IndiaMARTFetchLeadsWizard(models.TransientModel):
    _name = 'indiamart.fetch.leads.wizard'
    _description = 'IndiaMART Fetch Leads Wizard'

    start_time = fields.Datetime(
        string="Start Date",
        required=True,
        default=lambda self: datetime.now() - timedelta(days=1)
    )
    end_time = fields.Datetime(
        string="End Date",
        required=True,
        default=lambda self: datetime.now()
    )

    @api.constrains('start_time', 'end_time')
    def _check_dates(self):
        for record in self:
            if record.start_time >= record.end_time:
                raise ValidationError("Error: Start Date must be before End Date.")
            if record.end_time - record.start_time > timedelta(days=7):
                raise ValidationError("Error: The date range cannot be more than 7 days.")

    def action_fetch_leads(self):
        '''Manual fetch with date range - HAS duplicate check to avoid backfill duplicates'''
        log_vals = {'is_manual': True}
        errors = []
        
        try:
            settings = self.env['indiamart.settings'].search([], limit=1)
            if not settings or not settings.api_key:
                raise UserError("IndiaMART API Key is not set.")

            import pytz
            ist_tz = pytz.timezone('Asia/Kolkata')
            utc_tz = pytz.utc
            
            start_time_ist = utc_tz.localize(self.start_time).astimezone(ist_tz)
            end_time_ist = utc_tz.localize(self.end_time).astimezone(ist_tz)
            
            start_str = start_time_ist.strftime('%d-%m-%Y%H:%M:%S')
            end_str = end_time_ist.strftime('%d-%m-%Y%H:%M:%S')

            _logger.info(f"Manual fetch (IST): {start_str} to {end_str}")
            
            api_url = "https://mapi.indiamart.com/wservce/crm/crmListing/v2/"
            params = {
                'glusr_crm_key': settings.api_key,
                'start_time': start_str,
                'end_time': end_str
            }

            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('STATUS') == 'FAILURE':
                raise UserError(f"IndiaMART API Error: {data.get('MESSAGE')}")

            leads_data = data.get('RESPONSE', [])
            total_received = len(leads_data)
            log_vals['leads_fetched'] = total_received
            
            _logger.info(f"API returned {total_received} leads")

            new_leads_count = 0
            skipped_no_id = 0
            skipped_duplicates = 0
            failed_count = 0
            Lead = self.env['crm.lead']
            
            # Get or create IndiaMART source
            indiamart_source = self.env['utm.source'].search([('name', '=', 'IndiaMART')], limit=1)
            if not indiamart_source:
                indiamart_source = self.env['utm.source'].create({'name': 'IndiaMART'})
            indiamart_source_id = indiamart_source.id
            
            for idx, lead in enumerate(leads_data, 1):
                unique_id = lead.get('UNIQUE_QUERY_ID')
                sender_name = lead.get('SENDER_NAME', 'Unknown')
                
                if not unique_id:
                    skipped_no_id += 1
                    errors.append(f"{sender_name}: Missing ID")
                    continue

                # Check for duplicates during manual fetch (when backfilling)
                existing_lead = Lead.search([('indiamart_unique_id', '=', unique_id)], limit=1)
                if existing_lead:
                    skipped_duplicates += 1
                    _logger.info(f"» Duplicate: {sender_name} (ID: {unique_id}) - Already exists as Lead #{existing_lead.id}")
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
                    state = self.env['res.country.state'].search([
                        ('name', '=', lead.get('SENDER_STATE'))
                    ], limit=1)
                    if state:
                        vals['state_id'] = state.id
                
                if lead.get('SENDER_COUNTRY_ISO'):
                    country = self.env['res.country'].search([
                        ('code', '=', lead.get('SENDER_COUNTRY_ISO'))
                    ], limit=1)
                    if country:
                        vals['country_id'] = country.id
                
                if query_type:
                    try:
                        vals['indiamart_query_type'] = query_type
                    except:
                        pass
                
                description = (
                    f"IndiaMART Lead\n"
                    f"{'='*50}\n"
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
                    _logger.info(f"✓ Created lead: {sender_name} (ID: {new_lead.id})")
                    
                except Exception as e:
                    error_msg = str(e)
                    failed_count += 1
                    _logger.error(f"✗ Failed to create lead {unique_id}: {error_msg}")
                    errors.append(f"{sender_name}: {error_msg[:50]}")

            summary = (
                f"API returned {total_received} leads\n"
                f"✓ Created: {new_leads_count}\n"
                f"» Skipped (Duplicate): {skipped_duplicates}\n"
                f"» Skipped (No ID): {skipped_no_id}\n"
                f"✗ Failed: {failed_count}"
            )
            
            if errors:
                summary += "\n\nErrors:\n" + "\n".join(errors[:5])
            
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
            _logger.error(f"IndiaMART fetch failed: {error_msg}", exc_info=True)
            log_vals.update({'status': 'failure', 'response_message': error_msg})
            raise UserError(error_msg)
        finally:
            self.env['indiamart.api.log'].create(log_vals)