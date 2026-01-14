# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = 'Approval Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    has_date = fields.Boolean(string='Has Date', default=True, help='Request date field is required')
    has_period = fields.Boolean(string='Has Period', default=False, help='Request period fields are required')
    has_quantity = fields.Boolean(string='Has Quantity', default=False, help='Request quantity field is required')
    has_amount = fields.Boolean(string='Has Amount', default=False, help='Request amount field is required')
    has_reference = fields.Boolean(string='Has Reference', default=False, help='Request reference field is required')
    has_payment_method = fields.Boolean(string='Has Payment Method', default=False)
    has_location = fields.Boolean(string='Has Location', default=False)
    has_partner = fields.Boolean(string='Has Contact', default=False)
    has_product = fields.Boolean(string='Has Product', default=False, help='Request product field is required')
    approval_type = fields.Selection([
        ('user', 'Users'),
        ('manager', 'Manager'),
        ('both', 'Both'),
    ], string='Approval Type', required=True, default='user', tracking=True)
    approval_minimum = fields.Integer(string='Minimum Approvals', default=1, required=True, tracking=True)
    approval_sequence = fields.Boolean(string='Sequential Approval', default=False, tracking=True,
                                       help='If enabled, approvals must be done in sequence')
    require_my_approval = fields.Boolean(string='Require My Approval', default=False,
                                         help='If enabled, the requester must also approve')
    require_employee_manager = fields.Boolean(string="Require Employee's Manager", default=False, tracking=True,
                                             help="If enabled, the employee's manager will be required as an approver")
    request_to_validate_count = fields.Integer(compute='_compute_request_to_validate_count')
    request_count = fields.Integer(compute='_compute_request_count')
    approver_ids = fields.One2many('approval.approver', 'category_id', string='Approvers')
    request_ids = fields.One2many('approval.request', 'category_id', string='Requests')
    description = fields.Html(string='Description')

    @api.depends('request_ids')
    def _compute_request_count(self):
        for category in self:
            category.request_count = len(category.request_ids)

    @api.depends('request_ids', 'request_ids.state')
    def _compute_request_to_validate_count(self):
        for category in self:
            category.request_to_validate_count = len(
                category.request_ids.filtered(lambda r: r.state == 'pending')
            )

    @api.constrains('approval_minimum', 'approver_ids', 'approval_type')
    def _check_approval_minimum(self):
        for category in self:
            if category.approval_minimum < 1:
                raise ValidationError(_('Minimum approvals must be at least 1'))
            
            # Get category-level approvers (template approvers without request_id)
            category_approvers = category.approver_ids.filtered(lambda a: not a.request_id)
            
            # Validate approvers are defined when required
            if category.approval_type in ('user', 'both'):
                if not category_approvers:
                    raise ValidationError(_('Approvers must be defined when Approval Type is "Users" or "Both". Please add at least one approver in the Approvers section.'))
            
            # Validate minimum approvals doesn't exceed number of approvers
            if category.approval_type in ('user', 'both') and category_approvers:
                if category.approval_minimum > len(category_approvers):
                    raise ValidationError(_('Minimum approvals (%d) cannot exceed the number of approvers (%d).') % (category.approval_minimum, len(category_approvers)))

    def action_view_requests(self):
        """Open requests for this category"""
        self.ensure_one()
        return {
            'name': _('Approval Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form,kanban',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }

    def action_view_to_validate(self):
        """Open pending requests for this category"""
        self.ensure_one()
        return {
            'name': _('Requests to Validate'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form,kanban',
            'domain': [('category_id', '=', self.id), ('state', '=', 'pending')],
            'context': {'default_category_id': self.id},
        }

