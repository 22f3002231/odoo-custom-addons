# -*- coding: utf-8 -*-
{
    'name': 'TradeIndia Integration',
    'version': '19.0.1.0.0',
    'summary': 'Integrate TradeIndia API to fetch leads into Odoo CRM.',
    'author': 'Rohitkumar Singh',
    'website': 'https://www.tradeindia.com',
    'category': 'Sales/CRM',
    'icon': 'static/description/icon.png',
    'depends': [
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/tradeindia_settings_data.xml',
        'data/tradeindia_cron.xml',
        'views/crm_lead_views.xml',
        'views/tradeindia_settings_views.xml',
        'views/tradeindia_fetch_leads_wizard_views.xml',
        'views/tradeindia_api_log_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}