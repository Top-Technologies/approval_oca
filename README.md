# Custom Approval Module for Odoo 18 Community

![Odoo Version](https://img.shields.io/badge/Odoo-18.0-purple)
![License](https://img.shields.io/badge/license-LGPL--3-blue)

A complete approval workflow system equivalent to the Odoo Enterprise Approval module, designed specifically for Odoo 18 Community Edition.

## 📝 Description

This module brings robust approval management capabilities to Odoo Community. It allows organizations to define custom approval requests, manage workflows, and handle multi-step approvals without needing the Enterprise edition. It integrates seamlessly with Odoo's chatter and activity system.

## ✨ Features

-   **Multi-step Approval Workflows**: Define complex approval routes.
-   **Configurable Approval Categories**: Create different types of approvals (e.g., Leave, Purchase, Expense).
-   **Sequential & Parallel Modes**: Flexible approval ordering.
-   **Document Attachments**: Require or allow attachments for evidence.
-   **Chatter Integration**: Full history and communication tracking on requests.
-   **Activity Scheduling**: Automated activities for approvers.
-   **Multi-company Support**: Works in multi-company environments.
-   **Department & User-based Approvals**: Flexible approver assignment.
-   **Purchase Integration**: Link approvals to Purchase Orders.
-   **OWL Components**: Modern frontend interface.

## ⚙️ Installation

1.  Clone this repository into your Odoo custom addons directory:
    ```bash
    git clone <repository_url> custom_approval
    ```
2.  Update your Odoo configuration file (`odoo.conf`) to include the addons path.
3.  Restart the Odoo service.
4.  Go to **Apps**, click **Update App List**, and search for "Custom Approval".
5.  Click **Activate/Install**.

## 🔧 Configuration

1.  Navigate to **Approvals > Configuration > Approval Categories**.
2.  Create a new category (e.g., "Office Supplies").
3.  Configure the approval settings:
    -   **Approval Type**: Required, Optional, etc.
    -   **Approvers**: Define who needs to approve (Managers, Specific Users).
    -   **Minimum Amount**: Set thresholds if needed.

## 🚀 Usage

1.  **Create Request**: Go to the **Approvals** dashboard and click on a category or "New Request".
2.  **Fill Details**: Provide description, dates, amounts, and attachments if required.
3.  **Submit**: Click the submit button to initiate the workflow.
4.  **Approve/Refuse**: Designated approvers will receive notifications/activities to review the request.
5.  **Status Tracking**: Track the status from "Submitted" to "Approved" or "Refused".

## 📋 Dependencies

-   `base`
-   `mail`
-   `portal`
-   `web`
-   `purchase`

## 👤 Author

**Custom Development from TopTech**
