# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class ApprovalPortal(http.Controller):
    """Portal controller for approval requests"""

    @http.route('/my/approvals', type='http', auth='user', website=True)
    def portal_my_approvals(self, **kw):
        """Portal page for user's approval requests"""
        return request.render('custom_approval.portal_my_approvals', {
            'page_name': 'approvals',
        })

