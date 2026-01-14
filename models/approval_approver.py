# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ApprovalApprover(models.Model):
    _name = 'approval.approver'
    _description = 'Approval Approver'
    _order = 'sequence, id'

    category_id = fields.Many2one('approval.category', string='Category', required=True, ondelete='cascade')
    request_id = fields.Many2one('approval.request', string='Request', required=False, ondelete='cascade', default=False)
    user_id = fields.Many2one('res.users', string='Approver', required=True, tracking=True)
    status = fields.Selection([
        ('new', 'Initial'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Status', default='new', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Datetime(string='Date')
    comment = fields.Text(string='Comment')
    can_approve = fields.Boolean(compute='_compute_can_approve', string='Can Approve')

    @api.depends('user_id', 'request_id.state', 'status', 'request_id.category_id.approval_sequence')
    def _compute_can_approve(self):
        """Check if current user can approve this approver line"""
        for approver in self:
            can_approve = False
            if approver.request_id and approver.request_id.state == 'pending':
                if approver.user_id == self.env.user:
                    if approver.status == 'pending':
                        # Check sequential approval if enabled
                        if approver.request_id.category_id.approval_sequence:
                            # Check if previous approvers are approved
                            previous_approvers = approver.request_id.approver_ids.filtered(
                                lambda a: a.sequence < approver.sequence
                            )
                            if all(a.status == 'approved' for a in previous_approvers):
                                can_approve = True
                        else:
                            can_approve = True
            approver.can_approve = can_approve

    def action_approve(self):
        """Approve the request"""
        self.ensure_one()
        if not self.request_id:
            raise UserError(_('Cannot approve a category-level approver.'))
        if not self.can_approve:
            raise UserError(_('You cannot approve this request.'))
        if self.request_id.state != 'pending':
            raise UserError(_('This request is not pending approval.'))
        
        vals = {
            'status': 'approved',
        }
        if not self.date:
            vals['date'] = fields.Datetime.now()
        
        self.write(vals)
        
        # Check if request should be auto-approved
        self.request_id._check_auto_approval()

    def action_refuse(self, comment=None):
        """Refuse the request"""
        self.ensure_one()
        if not self.request_id:
            raise UserError(_('Cannot refuse a category-level approver.'))
        if not self.can_approve:
            raise UserError(_('You cannot refuse this request.'))
        if self.request_id.state != 'pending':
            raise UserError(_('This request is not pending approval.'))
        
        self.write({
            'status': 'refused',
            'date': fields.Datetime.now(),
            'comment': comment or '',
        })
        
        # Refuse the entire request - directly update state
        self.request_id.write({
            'state': 'refused',
            'reason': comment or '',
        })
        
        # Send email
        try:
            template = self.env.ref('custom_approval.email_template_approval_request_refused_v2', raise_if_not_found=False)
            if template:
                if self.request_id.request_owner_id.email:
                    template.send_mail(self.request_id.id, force_send=True, email_values={
                        'email_to': self.request_id.request_owner_id.email,
                        'email_from': self.request_id.company_id.email or self.env.user.email,
                    })
        except Exception as e:
            self.request_id.message_post(body=_("Could not send refusal email: %s") % str(e))
        
        # Post message
        self.request_id.message_post(
            body=_('Request refused by %s.') % self.user_id.name + (f'\n{comment}' if comment else ''),
            subtype_xmlid='mail.mt_note',
        )

    @api.model
    def create(self, vals):
        """Override create to set default user and category based on request/context"""
        # Ensure category_id is set
        if not vals.get('category_id'):
            # Try to get from context first
            if self.env.context.get('default_category_id'):
                vals['category_id'] = self.env.context.get('default_category_id')
            # If still missing, try to get from request_id
            elif vals.get('request_id'):
                request = self.env['approval.request'].browse(vals['request_id'])
                if request.exists() and request.category_id:
                    vals['category_id'] = request.category_id.id
        
        # For category-level approvers (templates), ensure request_id is explicitly False
        is_category_level = False
        if not vals.get('request_id'):
            vals['request_id'] = False
            is_category_level = True
        
        # Only set manager for request-level approvers, not category-level template approvers
        if 'user_id' not in vals and vals.get('request_id') and vals.get('category_id'):
            try:
                category = self.env['approval.category'].browse(vals['category_id'])
                if category.exists() and category.approval_type == 'manager':
                    request = self.env['approval.request'].browse(vals['request_id'])
                    if request.exists() and request.request_owner_id:
                        if hasattr(request.request_owner_id, 'employee_id') and request.request_owner_id.employee_id:
                            if request.request_owner_id.employee_id.parent_id:
                                manager = request.request_owner_id.employee_id.parent_id.user_id
                                if manager:
                                    vals['user_id'] = manager.id
            except Exception:
                pass
        
        if 'status' not in vals:
            vals['status'] = 'new'
        
        if is_category_level:
            return super(ApprovalApprover, self.sudo()).create(vals)
            
        return super().create(vals)

