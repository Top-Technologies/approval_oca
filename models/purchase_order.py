# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_request_ids = fields.One2many('approval.request', 'res_id', string='Approval Requests',
                                         domain=lambda self: [('res_model', '=', self._name)])
    approval_request_count = fields.Integer(compute='_compute_approval_request_count')
    approval_status = fields.Selection([
        ('no', 'No Approval'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Approval Status', compute='_compute_approval_status', store=False)

    @api.depends('approval_request_ids.state')
    def _compute_approval_request_count(self):
        for order in self:
            order.approval_request_count = len(order.approval_request_ids)

    @api.depends('approval_request_ids.state')
    def _compute_approval_status(self):
        for order in self:
            if not order.approval_request_ids:
                order.approval_status = 'no'
            elif any(r.state == 'approved' for r in order.approval_request_ids):
                order.approval_status = 'approved'
            elif any(r.state == 'refused' for r in order.approval_request_ids):
                order.approval_status = 'refused'
            elif any(r.state == 'pending' for r in order.approval_request_ids):
                order.approval_status = 'to_approve'
            else:
                order.approval_status = 'no'

    def action_create_approval_request(self):
        """Create an approval request for this purchase order"""
        self.ensure_one()
        # Find a suitable category (e.g. Purchase Request)
        category = self.env['approval.category'].search([('name', 'ilike', 'Purchase')], limit=1)
        if not category:
            category = self.env['approval.category'].search([], limit=1)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'context': {
                'default_category_id': category.id if category else False,
                'default_name': _('Approval for %s', self.name),
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_amount': self.amount_total,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'current',
        }

    def button_confirm(self):
        """Override to check approval status before confirmation"""
        for order in self:
            if order.approval_request_ids and order.approval_status != 'approved':
                raise UserError(_('You cannot confirm this order because the approval request is not approved.'))
        return super(PurchaseOrder, self).button_confirm()

    def action_view_approval_requests(self):
        """View approval requests for this purchase order"""
        self.ensure_one()
        return {
            'name': _('Approval Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }
