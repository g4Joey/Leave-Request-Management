# Leave Request Management System - User Manual

**Version 2.0** | **Updated:** October 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [User Roles and Permissions](#user-roles-and-permissions)
3. [Getting Started](#getting-started)
4. [Employee Workflows](#employee-workflows)
5. [Manager Workflows](#manager-workflows)
6. [HR Workflows](#hr-workflows)
7. [CEO Workflows](#ceo-workflows)
8. [Administrative Tasks](#administrative-tasks)
9. [Notifications System](#notifications-system)
10. [Deployment and Operations](#deployment-and-operations)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)

---

## System Overview

The Leave Request Management System is a comprehensive web application designed to streamline the leave approval process within organizations. The system implements a three-tier approval workflow (Manager → HR → CEO) with role-based access control and automated notifications.

### Key Features
- **Multi-tier Approval Workflow**: Manager → HR → CEO approval chain
- **Role-based Access Control**: Employee, Manager, HR, CEO permissions
- **Real-time Notifications**: In-app notifications for all workflow events
- **Leave Balance Tracking**: Automatic calculation and balance management
- **Dashboard Analytics**: Visual insights into leave patterns and approvals
- **Audit Trail**: Complete history of all leave requests and approvals

### Technology Stack
- **Backend**: Django 5.x + Django REST Framework
- **Frontend**: React with Tailwind CSS
- **Authentication**: JWT (JSON Web Tokens)
- **Database**: MySQL (production) / SQLite (development)
- **Deployment**: DigitalOcean App Platform

---

## User Roles and Permissions

### Employee
- Submit leave requests
- View own leave history and status
- Check leave balances
- Receive notifications about request status
- Update profile information

### Manager
- All Employee permissions
- Approve/reject leave requests from direct reports
- View team leave calendar
- Receive notifications for team leave submissions
- Access team dashboard analytics

### HR (Human Resources)
- All Manager permissions
- Approve/reject leave requests after manager approval
- Manage leave types and policies
- View organization-wide leave analytics
- Manage user profiles and roles
- Access admin panel for system configuration

### CEO (Chief Executive Officer)
- All HR permissions
- Final approval authority for all leave requests
- Access complete system analytics
- Override any approval decisions
- System-wide administrative access

---

## Getting Started

### First-Time Login

1. **Access the Application**
   - Navigate to your organization's leave management URL
   - Example: `https://your-company.ondigitalocean.app`

2. **Login Credentials**
   - Use the credentials provided by your administrator
   - Default admin credentials are set during deployment

3. **Profile Setup**
   - Complete your profile information
   - Upload profile picture (optional)
   - Set notification preferences

### Dashboard Overview

The dashboard provides a quick overview of:
- **Pending Requests**: Leave requests awaiting your action
- **Recent Activity**: Latest leave submissions and approvals
- **Leave Balance**: Current available leave days by type
- **Quick Actions**: Submit new request, view calendar
- **Notifications**: Recent system notifications

---

## Employee Workflows

### Submitting a Leave Request

1. **Navigate to Leave Submission**
   - Click "Submit Leave Request" from the dashboard
   - Or use the navigation menu: Leave → Submit Request

2. **Fill Request Details**
   ```
   Leave Type: [Annual Leave/Sick Leave/Emergency/etc.]
   Start Date: [Select date]
   End Date: [Select date]
   Reason: [Detailed explanation]
   Emergency Contact: [Optional]
   ```

3. **Submit Request**
   - Review all details carefully
   - Click "Submit Request"
   - Receive confirmation notification

4. **Track Status**
   - Monitor request progress in "My Requests"
   - Receive notifications at each approval stage

### Viewing Leave History

1. **Access Leave History**
   - Navigate to Leave → My Requests
   - Filter by status: Pending, Approved, Rejected
   - Filter by date range or leave type

2. **Request Details**
   - Click on any request to view full details
   - See approval timeline and comments
   - Download request summary (if needed)

### Checking Leave Balance

1. **Balance Overview**
   - View current balances on dashboard
   - Navigate to Leave → Balance for detailed view

2. **Balance Details**
   - Annual leave remaining
   - Sick leave available
   - Emergency leave quota
   - Leave year reset dates

---

## Manager Workflows

### Reviewing Team Requests

1. **Access Pending Approvals**
   - Navigate to Approvals → Pending Requests
   - Or click notification alerts

2. **Review Request Details**
   ```
   Employee Information
   Leave Type and Duration
   Reason for Leave
   Team Impact Assessment
   Employee Leave History
   ```

3. **Make Decision**
   - **Approve**: Add comments (optional) and click "Approve"
   - **Reject**: Add detailed rejection reason and click "Reject"

4. **Post-Approval Actions**
   - Request automatically forwarded to HR
   - Employee and HR receive notifications
   - Update team calendar

### Managing Team Calendar

1. **Team Leave Overview**
   - Navigate to Team → Calendar
   - View all team members' leave schedules
   - Identify potential coverage gaps

2. **Planning Tools**
   - Color-coded leave types
   - Filter by team member or date range
   - Export calendar for external planning

---

## HR Workflows

### Processing Leave Requests

1. **HR Review Queue**
   - Navigate to Approvals → HR Queue
   - Filter by priority or submission date

2. **Comprehensive Review**
   ```
   Manager Approval Status
   Employee Leave History
   Policy Compliance Check
   Organizational Impact
   Leave Balance Verification
   ```

3. **HR Decision Process**
   - **Approve**: Forward to CEO with recommendations
   - **Reject**: Provide detailed policy-based reasoning
   - **Request More Info**: Send back to employee for clarification

### Managing Leave Policies

1. **Leave Types Administration**
   - Navigate to Admin → Leave Types
   - Configure: Annual, Sick, Emergency, Maternity, etc.
   - Set allocation rules and carryover policies

2. **Policy Updates**
   - Update leave quotas
   - Modify approval workflows
   - Communicate policy changes to users

### User Management

1. **User Administration**
   - Navigate to Admin → Users
   - Create new user accounts
   - Update roles and permissions
   - Deactivate departing employees

2. **Bulk Operations**
   - Import users from CSV
   - Bulk role assignments
   - Annual leave balance updates

---

## CEO Workflows

### Final Approvals

1. **CEO Approval Queue**
   - Navigate to Approvals → CEO Queue
   - Review HR-approved requests

2. **Strategic Review**
   ```
   Business Impact Assessment
   Resource Planning Implications
   Policy Precedent Considerations
   Executive Discretion Factors
   ```

3. **Final Decision**
   - **Approve**: Complete the approval chain
   - **Reject**: Override with executive reasoning
   - **Delegate**: Assign to specific executive

### Executive Dashboard

1. **Organization-wide Analytics**
   - Leave utilization trends
   - Department-wise patterns
   - Cost impact analysis
   - Workforce planning insights

2. **Strategic Reports**
   - Monthly leave summaries
   - Annual trend analysis
   - Predictive workforce planning
   - Policy effectiveness metrics

---

## Administrative Tasks

### System Configuration

1. **Email Templates**
   - Navigate to Admin → Email Templates
   - Customize notification messages
   - Configure automatic reminders

2. **System Settings**
   ```
   Leave Year Configuration
   Approval Workflow Rules
   Notification Preferences
   Security Settings
   Integration Parameters
   ```

### Data Management

1. **Database Operations**
   - Regular backups (automated)
   - Data export for reporting
   - Historical data archival

2. **User Data Privacy**
   - GDPR compliance tools
   - Data retention policies
   - User data export/deletion

### Audit and Compliance

1. **Audit Trails**
   - Navigate to Admin → Audit Logs
   - Track all system activities
   - Generate compliance reports

2. **Security Monitoring**
   - Failed login attempts
   - Permission changes
   - Data access logs

---

## Notifications System

### Notification Types

1. **Leave Workflow Notifications**
   - Leave request submitted
   - Manager approval/rejection
   - HR approval/rejection
   - CEO final decision
   - Request cancellation

2. **System Notifications**
   - Leave balance warnings
   - Policy updates
   - System maintenance alerts
   - Security notifications

### Notification Preferences

1. **User Settings**
   - Navigate to Profile → Notifications
   - Configure email preferences
   - Set notification frequency
   - Choose notification types

2. **Admin Configuration**
   - System-wide notification rules
   - Email template management
   - Notification delivery settings

---

## Deployment and Operations

### DigitalOcean App Platform Deployment

1. **Application Setup**
   ```bash
   # The application deploys automatically from source
   # via .do/app.yaml specification
   ```

2. **Environment Configuration**
   ```
   DJANGO_SETTINGS_MODULE=leave_management.settings_production
   SECRET_KEY=[your-production-secret]
   DATABASE_URL=[mysql-connection-string]
   DEBUG=False
   ALLOWED_HOSTS=[your-domain.ondigitalocean.app]
   ```

3. **Database Setup**
   - DigitalOcean Managed MySQL database
   - Automatic SSL/TLS encryption
   - Connection via DATABASE_URL environment variable

### Initial Data Seeding

1. **First Deployment Setup**
   ```
   RUN_SEED_ON_DEPLOY=1
   SEED_USERS=[JSON array of initial users]
   DJANGO_SUPERUSER_USERNAME=admin
   DJANGO_SUPERUSER_PASSWORD=[secure-password]
   ```

2. **Production Data Setup**
   - Leave types and categories
   - Initial user accounts
   - Default system settings
   - Email templates

### Maintenance Operations

1. **Regular Maintenance**
   ```bash
   # Database migrations (automated in pre-deploy)
   python manage.py migrate
   
   # Static files collection (automated)
   python manage.py collectstatic
   
   # Leave data setup (automated)
   python manage.py setup_production_leave_data
   ```

2. **Monitoring and Logs**
   - Application logs via DigitalOcean console
   - Database performance monitoring
   - Error tracking and alerting

---

## Troubleshooting

### Common Issues

1. **Login Problems**
   - **Issue**: Cannot log in with credentials
   - **Solution**: Check with administrator, verify account status
   - **Admin Action**: Reset password via admin panel

2. **Leave Balance Incorrect**
   - **Issue**: Balance doesn't match expected amount
   - **Solution**: Contact HR for balance review
   - **Admin Action**: Run balance verification command

3. **Notification Not Received**
   - **Issue**: Missing email notifications
   - **Solution**: Check spam folder, verify email in profile
   - **Admin Action**: Check email configuration and logs

### Administrative Troubleshooting

1. **Database Issues**
   ```bash
   # Verify database connection
   python manage.py verify_db
   
   # Fix production data inconsistencies
   python manage.py fix_production_data
   
   # Ensure leave balances are correct
   python manage.py ensure_leave_balances
   ```

2. **User Management Issues**
   ```bash
   # Fix user role mismatches
   python manage.py fix_user_mismatches
   
   # Update user roles
   python manage.py update_user_roles
   
   # Setup fresh database (development only)
   python manage.py setup_fresh_database
   ```

### Performance Issues

1. **Slow Response Times**
   - Check database query performance
   - Review server resource utilization
   - Optimize database indexes

2. **High Load Handling**
   - Scale DigitalOcean App Platform resources
   - Implement database connection pooling
   - Add Redis caching layer

---

## FAQ

### General Questions

**Q: How long does the approval process take?**
A: The approval timeline depends on your organization's workflow. Typically: Manager (1-2 days) → HR (2-3 days) → CEO (1-2 days).

**Q: Can I cancel a submitted leave request?**
A: Yes, you can cancel requests that haven't been fully approved. Navigate to "My Requests" and click "Cancel" on pending requests.

**Q: What happens if I exceed my leave balance?**
A: The system will prevent submission of requests that exceed your balance. Contact HR if you need to request additional leave.

### Technical Questions

**Q: Why can't I access certain features?**
A: Features are role-based. Contact your administrator if you need additional permissions.

**Q: How do I change my password?**
A: Navigate to Profile → Security → Change Password, or use the "Forgot Password" link on the login page.

**Q: Can I use the system on mobile devices?**
A: Yes, the application is responsive and works on mobile browsers. A dedicated mobile app may be available in the future.

### Administrative Questions

**Q: How do I add new leave types?**
A: HR and CEO roles can add leave types via Admin → Leave Types → Add New Type.

**Q: How do I export leave data for payroll?**
A: Navigate to Reports → Export Data, select date range and employees, then download the CSV export.

**Q: How do I backup the system?**
A: The DigitalOcean managed database includes automated backups. Additional backup procedures can be configured in the admin panel.

---

## Support and Contact

For technical support or questions about this user manual:

- **System Administrator**: Contact your organization's IT department
- **HR Questions**: Reach out to your Human Resources team
- **Technical Issues**: Submit a support ticket through the system
- **Emergency Access**: Contact your designated system administrator

---

**Document Version**: 2.0  
**Last Updated**: October 16, 2025  
**Next Review**: January 2026

---

*This manual covers the standard configuration of the Leave Request Management System. Your organization may have customizations that differ from this documentation. Contact your administrator for organization-specific procedures.*