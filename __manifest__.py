{
    'name': 'Custom Approval',
    'version': '18.0.1.0.3',
    'category': 'Approvals',
    'summary': 'Enterprise-equivalent Approval Module for Odoo 18 Community',
    'description': """
Custom Approval Module for Odoo 18 Community
============================================

This module provides a complete approval workflow system equivalent to Odoo Enterprise Approval module.

Features:
---------
* Multi-step approval workflows
* Configurable approval categories
* Sequential and parallel approval modes
* Document attachments
* Chatter integration
* Activity scheduling
* Multi-company support
* Department-based approvals
* User-based approvals

Workflow:
---------
* Draft → Submitted → Approved/Refused → Cancelled

Technical:
----------
* Built for Odoo 18 Community
* No Enterprise dependencies
* OWL components for frontend
* Full mail.thread integration
    """,
    'author': 'Custom Development from TopTech',
    'website': '',
    'depends': [
        'base',
        'mail',
        'portal',
        'web',
        'purchase',
    ],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'data/approval_category_data.xml',
        'views/approval_category_views.xml',
        'views/approval_request_views.xml',
        'views/approval_refuse_wizard_views.xml',
        'views/approval_dashboard_views.xml',
        'views/approval_menus.xml',
        'views/purchase_order_views.xml',
        'data/approval_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_approval/static/src/js/approval_request_form.js',
            'custom_approval/static/src/js/approval_kanban.js',
            'custom_approval/static/src/xml/approval_request_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

