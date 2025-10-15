# -*- coding: utf-8 -*-
{
    'name': 'IndiaMART Integration',
    'version': '19.0.1.0.0',
    'summary': 'Integrate IndiaMART Pull API to fetch leads into Odoo CRM.',
    'author': 'Your Name',
    'website': 'Your Website',
    'category': 'Sales/CRM',
    'icon': 'static/description/icon.png',
    'depends': [
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/indiamart_settings_data.xml',
        'data/indiamart_cron.xml',
        'views/crm_lead_views.xml',
        'views/indiamart_settings_views.xml',
        'views/indiamart_fetch_leads_wizard_views.xml',
        'views/indiamart_api_log_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}