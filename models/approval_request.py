# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Request Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'), tracking=True)
    category_id = fields.Many2one('approval.category', string='Category', required=True, tracking=True,
                                 check_company=True)
    request_owner_id = fields.Many2one('res.users', string='Request Owner', required=True,
                                       default=lambda self: self.env.user, tracking=True)
    date = fields.Date(string='Request Date', required=True, default=fields.Date.context_today, tracking=True)
    date_start = fields.Date(string='Period Start', tracking=True)
    date_end = fields.Date(string='Period End', tracking=True)
    quantity = fields.Float(string='Quantity', tracking=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    reference = fields.Char(string='Reference', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    location = fields.Char(string='Location', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    payment_method_id = fields.Many2one('approval.payment.method', string='Payment Method', tracking=True)
    res_model = fields.Char(string='Resource Model', index=True)
    res_id = fields.Integer(string='Resource ID', index=True)
    res_reference = fields.Reference(selection='_selection_target_model', string='Source Document', compute='_compute_res_reference', store=False)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    request_status = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], string='Request Status', compute='_compute_request_status')
    approver_ids = fields.One2many('approval.approver', 'request_id', string='Approvers', copy=True)
    has_access_to_request = fields.Boolean(compute='_compute_has_access_to_request', store=False)
    request_link = fields.Char(string='Request Link', compute='_compute_request_link', store=False)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    description = fields.Html(string='Description', tracking=True)
    reason = fields.Text(string='Reason', tracking=True)
    approval_minimum = fields.Integer(related='category_id.approval_minimum', string='Minimum Approvals', readonly=True)
    approval_type = fields.Selection(related='category_id.approval_type', string='Approval Type', readonly=True)
    approval_sequence = fields.Boolean(related='category_id.approval_sequence', string='Sequential Approval', readonly=True)
    has_date = fields.Boolean(related='category_id.has_date', string='Has Date', readonly=True)
    has_period = fields.Boolean(related='category_id.has_period', string='Has Period', readonly=True)
    has_quantity = fields.Boolean(related='category_id.has_quantity', string='Has Quantity', readonly=True)
    has_amount = fields.Boolean(related='category_id.has_amount', string='Has Amount', readonly=True)
    has_reference = fields.Boolean(related='category_id.has_reference', string='Has Reference', readonly=True)
    has_payment_method = fields.Boolean(related='category_id.has_payment_method', string='Has Payment Method', readonly=True)
    has_location = fields.Boolean(related='category_id.has_location', string='Has Location', readonly=True)
    has_partner = fields.Boolean(related='category_id.has_partner', string='Has Contact', readonly=True)
    has_product = fields.Boolean(related='category_id.has_product', string='Has Product', readonly=True)

    @api.depends('state')
    def _compute_request_status(self):
        """Map state to request_status"""
        for request in self:
            if request.state == 'draft':
                request.request_status = 'new'
            else:
                request.request_status = request.state

    @api.depends('request_owner_id', 'approver_ids.user_id')
    def _compute_has_access_to_request(self):
        """Check if current user has access to this request"""
        for request in self:
            has_access = (
                request.request_owner_id == self.env.user or
                self.env.user in request.approver_ids.mapped('user_id') or
                self.env.user.has_group('base.group_system')
            )
            request.has_access_to_request = has_access

    @api.depends('name')
    def _compute_request_link(self):
        """Generate request link"""
        for request in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            request.request_link = f"{base_url}/web#id={request.id}&model=approval.request&view_type=form"

    def _compute_attachment_number(self):
        """Compute number of attachments"""
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'approval.request'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id']
        )
        attachment_dict = {data['res_id']: data['res_id_count'] for data in attachment_data}
        for request in self:
            request.attachment_number = attachment_dict.get(request.id, 0)

    @api.model
    def create(self, vals):
        """Override create to generate sequence and create approvers"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or _('New')
        
        request = super().create(vals)
        
        # Create approvers based on category if not already provided (e.g. via UI onchange)
        if not vals.get('approver_ids'):
            request._create_approvers()
        
        return request

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Update approvers when category changes"""
        if self.category_id:
            # Store current approver IDs for comparison
            existing_approvers = [(5, 0, 0)]  # Command to clear all approvers
            self.approver_ids = existing_approvers
            
            # Prepare approver data based on category
            approver_data = self._prepare_approver_data()
            self.approver_ids = approver_data

    @api.onchange('request_owner_id')
    def _onchange_request_owner_id(self):
        """Update approvers when request owner changes (for manager-based approvals)"""
        if self.category_id and self.category_id.approval_type in ('manager', 'both'):
            # Refresh approvers
            approver_data = self._prepare_approver_data()
            self.approver_ids = approver_data

    def _prepare_approver_data(self):
        """Prepare approver data based on category configuration"""
        self.ensure_one()
        if not self.category_id:
            return [(5, 0, 0)]  # Clear approvers
        
        category = self.category_id
        approver_commands = []
        
        # Get category-level template approvers
        category_approvers = category.approver_ids.filtered(lambda a: not a.request_id)
        
        if category.approval_type == 'user':
            # Use category approvers
            if not category_approvers:
                # Return empty, will validate on submit
                return [(5, 0, 0)]
            for approver in category_approvers:
                approver_commands.append((0, 0, {
                    'category_id': category.id,
                    'user_id': approver.user_id.id,
                    'sequence': approver.sequence,
                    'status': 'new',
                }))
        elif category.approval_type == 'manager':
            # Use manager of request owner
            if self.request_owner_id and self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                if manager:
                    approver_commands.append((0, 0, {
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': 10,
                        'status': 'new',
                    }))
        elif category.approval_type == 'both':
            # Combine both
            if self.request_owner_id and self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                if manager:
                    approver_commands.append((0, 0, {
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': 5,
                        'status': 'new',
                    }))
            
            for approver in category_approvers:
                approver_commands.append((0, 0, {
                    'category_id': category.id,
                    'user_id': approver.user_id.id,
                    'sequence': approver.sequence + 10,
                    'status': 'new',
                }))
        
        # Add employee's manager if required
        if category.require_employee_manager:
            if self.request_owner_id and self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                # Check if manager is not already added
                if manager and manager.id not in [cmd[2].get('user_id') for cmd in approver_commands if cmd[0] == 0]:
                    max_sequence = max([cmd[2].get('sequence', 0) for cmd in approver_commands if cmd[0] == 0], default=0)
                    approver_commands.append((0, 0, {
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': max_sequence + 10,
                        'status': 'new',
                    }))
        
        # Add requester if required
        if category.require_my_approval and self.request_owner_id:
            # Check if requester is not already added
            if self.request_owner_id.id not in [cmd[2].get('user_id') for cmd in approver_commands if cmd[0] == 0]:
                approver_commands.append((0, 0, {
                    'category_id': category.id,
                    'user_id': self.request_owner_id.id,
                    'sequence': 0,
                    'status': 'new',
                }))
        
        return approver_commands

    def _create_approvers(self):
        """Create approver lines based on category configuration"""
        self.ensure_one()
        if not self.category_id:
            return
        
        # Clear existing approvers
        self.approver_ids.unlink()
        
        category = self.category_id
        category_approvers = category.approver_ids.filtered(lambda a: not a.request_id)
        
        if category.approval_type == 'user':
            # Use category approvers (only those without request_id, i.e., template approvers)
            if not category_approvers:
                raise UserError(_('No approvers defined for category "%s". Please define approvers in the category configuration before creating requests.') % category.name)
            for approver in category_approvers:
                self.env['approval.approver'].create({
                    'request_id': self.id,
                    'category_id': category.id,
                    'user_id': approver.user_id.id,
                    'sequence': approver.sequence,
                    'status': 'new',
                })
        elif category.approval_type == 'manager':
            # Use manager of request owner
            if self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                if manager:
                    self.env['approval.approver'].create({
                        'request_id': self.id,
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': 10,
                        'status': 'new',
                    })
                else:
                    raise UserError(_('No manager found for user "%s". Please ensure the user has an employee record with a manager assigned.') % self.request_owner_id.name)
            else:
                raise UserError(_('No manager found for user "%s". Please ensure the user has an employee record with a manager assigned.') % self.request_owner_id.name)
        elif category.approval_type == 'both':
            # Combine both (Manager + specific users)
            manager_created = False
            if self.request_owner_id and self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                if manager:
                    self.env['approval.approver'].create({
                        'request_id': self.id,
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': 5,
                        'status': 'new',
                    })
                    manager_created = True
            
            for approver in category_approvers:
                self.env['approval.approver'].create({
                    'request_id': self.id,
                    'category_id': category.id,
                    'user_id': approver.user_id.id,
                    'sequence': approver.sequence + 10,
                    'status': 'new',
                })
            
            if not manager_created and not category_approvers:
                raise UserError(_('No approvers found for category "%s". Please ensure the category has approvers defined or the requester has a manager.') % category.name)
        
        # Check if employee's manager is required as additional approver
        if category.require_employee_manager:
            if self.request_owner_id.employee_id and self.request_owner_id.employee_id.parent_id:
                manager = self.request_owner_id.employee_id.parent_id.user_id
                if manager and manager not in self.approver_ids.mapped('user_id'):
                    # Find the highest sequence to add manager after existing approvers
                    max_sequence = max(self.approver_ids.mapped('sequence')) if self.approver_ids else 0
                    self.env['approval.approver'].create({
                        'request_id': self.id,
                        'category_id': category.id,
                        'user_id': manager.id,
                        'sequence': max_sequence + 10,
                        'status': 'new',
                    })
                elif not manager:
                    raise UserError(_('No manager found for employee "%s". Please ensure the employee has a manager assigned.') % self.request_owner_id.name)
            else:
                raise UserError(_('No employee record found for user "%s". Please ensure the user has an employee record with a manager assigned.') % self.request_owner_id.name)
        
        # Check if requester must approve
        if category.require_my_approval and self.request_owner_id not in self.approver_ids.mapped('user_id'):
            self.env['approval.approver'].create({
                'request_id': self.id,
                'category_id': category.id,
                'user_id': self.request_owner_id.id,
                'sequence': 0,
                'status': 'new',
            })

    def action_confirm(self):
        """Submit the request for approval"""
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            
            if not request.approver_ids:
                raise UserError(_('No approvers configured. Please contact your administrator.'))
            
            # Validate required fields
            request._validate_required_fields()
            
            # Set approvers to pending
            request.approver_ids.write({'status': 'pending'})
            
            # Change state to pending
            request.write({'state': 'pending'})
            
            # Send notification to approvers
            request._notify_approvers()
            
            # Post message
            request.message_post(
                body=_('Request submitted for approval.'),
                subtype_xmlid='mail.mt_note',
            )
            
            # Send email
            try:
                template = self.env.ref('custom_approval.email_template_approval_request_submitted_v2', raise_if_not_found=False)
                if template:
                    email_to = ','.join(request.approver_ids.filtered(lambda a: a.user_id.email).mapped('user_id.email'))
                    if email_to:
                        template.send_mail(request.id, force_send=True, email_values={
                            'email_to': email_to,
                            'email_from': request.company_id.email or request.request_owner_id.email,
                        })
            except Exception as e:
                # Log error but don't crash the whole transaction
                request.message_post(body=_("Could not send submission email: %s") % str(e))

    def action_approve(self):
        """Approve the request"""
        for request in self:
            if request.state != 'pending':
                raise UserError(_('Only pending requests can be approved.'))
            
            # Check if current user can approve
            approver = request.approver_ids.filtered(lambda a: a.user_id == self.env.user and a.can_approve)
            if not approver:
                raise UserError(_('You cannot approve this request.'))
            
            approver.action_approve()

    def action_refuse(self, comment=None):
        """Refuse the request"""
        for request in self:
            if request.state != 'pending':
                raise UserError(_('Only pending requests can be refused.'))
            
            # Check if current user can refuse
            approver = request.approver_ids.filtered(lambda a: a.user_id == self.env.user and a.can_approve)
            if not approver:
                raise UserError(_('You cannot refuse this request.'))
            
            approver.action_refuse(comment)
            
            # Post message
            request.message_post(
                body=_('Request refused.') + (f'\n{comment}' if comment else ''),
                subtype_xmlid='mail.mt_note',
            )

    def action_refuse_wizard(self):
        """Open refuse wizard"""
        self.ensure_one()
        return {
            'name': _('Refuse Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_cancel(self):
        """Cancel the request"""
        for request in self:
            if request.state in ('approved', 'refused'):
                raise UserError(_('Cannot cancel an approved or refused request.'))
            
            request.write({'state': 'cancel'})
            
            # Post message
            request.message_post(
                body=_('Request cancelled.'),
                subtype_xmlid='mail.mt_note',
            )

    def action_withdraw(self):
        """Withdraw the request back to draft"""
        for request in self:
            if request.state != 'pending':
                raise UserError(_('Only pending requests can be withdrawn.'))
            
            if request.request_owner_id != self.env.user:
                raise UserError(_('Only the request owner can withdraw the request.'))
            
            request.write({'state': 'draft'})
            request.approver_ids.write({'status': 'new'})
            
            # Post message
            request.message_post(
                body=_('Request withdrawn.'),
                subtype_xmlid='mail.mt_note',
            )

    def _check_auto_approval(self):
        """Check if request should be auto-approved based on minimum approvals"""
        self.ensure_one()
        if self.state != 'pending':
            return
        
        approved_count = len(self.approver_ids.filtered(lambda a: a.status == 'approved'))
        
        if approved_count >= self.approval_minimum:
            self.write({'state': 'approved'})
            self.message_post(
                body=_('Request automatically approved.'),
                subtype_xmlid='mail.mt_note',
            )
            
            # Send email
            try:
                template = self.env.ref('custom_approval.email_template_approval_request_approved_v2', raise_if_not_found=False)
                if template:
                    if self.request_owner_id.email:
                        template.send_mail(self.id, force_send=True, email_values={
                            'email_to': self.request_owner_id.email,
                            'email_from': self.company_id.email or self.env.user.email,
                        })
            except Exception as e:
                self.message_post(body=_("Could not send approval email: %s") % str(e))

    def _validate_required_fields(self):
        """Validate required fields based on category configuration"""
        self.ensure_one()
        category = self.category_id
        
        if category.has_date and not self.date:
            raise ValidationError(_('Request date is required.'))
        
        if category.has_period:
            if not self.date_start or not self.date_end:
                raise ValidationError(_('Period start and end dates are required.'))
            if self.date_start > self.date_end:
                raise ValidationError(_('Period start date must be before end date.'))
        
        if category.has_quantity and not self.quantity:
            raise ValidationError(_('Quantity is required.'))
        
        if category.has_amount and not self.amount:
            raise ValidationError(_('Amount is required.'))
        
        if category.has_reference and not self.reference:
            raise ValidationError(_('Reference is required.'))
        
        if category.has_location and not self.location:
            raise ValidationError(_('Location is required.'))
        
        if category.has_partner and not self.partner_id:
            raise ValidationError(_('Contact is required.'))
        
        if category.has_product and not self.product_id:
            raise ValidationError(_('Product is required.'))

    def _notify_approvers(self):
        """Send notification to approvers"""
        self.ensure_one()
        approvers = self.approver_ids.filtered(lambda a: a.status == 'pending')
        
        if not approvers:
            return
        
        # Get partner IDs of approvers
        approver_partners = approvers.mapped('user_id.partner_id')
        
        # Send notification message to approvers
        message_body = _(
            '<p>A new approval request <strong>%s</strong> has been submitted and requires your approval.</p>'
            '<p><strong>Category:</strong> %s<br/>'
            '<strong>Request Owner:</strong> %s<br/>'
            '<strong>Date:</strong> %s</p>'
            '<p>Please review and take action on this request.</p>'
        ) % (
            self.name,
            self.category_id.name,
            self.request_owner_id.name,
            self.date.strftime('%Y-%m-%d') if self.date else '',
        )
        
        # Post message with notification to approvers
        self.message_post(
            body=message_body,
            partner_ids=approver_partners.ids,
            subtype_xmlid='mail.mt_comment',
            subject=_('Approval Request: %s', self.name),
        )
        
        # Create activity for each approver
        for approver in approvers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Approval Request: %s', self.name),
                note=_('Please review and approve the request: %s', self.name),
                user_id=approver.user_id.id,
            )

    def action_get_attachment_view(self):
        """Open attachment view"""
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'domain': [('res_model', '=', 'approval.request'), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'context': {'default_res_model': 'approval.request', 'default_res_id': self.id},
        }

    def action_attach_document(self):
        """Open attachment form to attach a document"""
        self.ensure_one()
        if not self.id:
            raise UserError(_('Please save the request before attaching documents.'))
        return {
            'name': _('Attach Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'approval.request',
                'default_res_id': self.id,
                'default_res_name': self.name,
            },
        }

    @api.constrains('date_start', 'date_end')
    def _check_period(self):
        """Validate period dates"""
        for request in self:
            if request.date_start and request.date_end and request.date_start > request.date_end:
                raise ValidationError(_('Period start date must be before end date.'))

    @api.model
    def _selection_target_model(self):
        """Get models available for approval linking"""
        # Use sudo to avoid access errors for non-admin users
        # Filter for models that are likely to be used for approvals
        domain = [('transient', '=', False), ('model', 'not ilike', 'base')]
        models = self.env['ir.model'].sudo().search(domain)
        return [(model.model, model.name) for model in models]

    @api.depends('res_model', 'res_id')
    def _compute_res_reference(self):
        """Compute the reference to the source document"""
        for request in self:
            if request.res_model and request.res_id:
                request.res_reference = f"{request.res_model},{request.res_id}"
            else:
                request.res_reference = False

    def action_open_source(self):
        """Open the source document"""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }


