# 🏖️ Leave Request Management System

A comprehensive Django-based leave management system that streamlines employee leave requests, approvals, and tracking for organizations.

## 🌟 Features

### ✅ Core Functionality (Requirements R1-R12)

- **📝 Leave Request Submission (R1)**: Employees can submit leave requests with start/end dates
- **📊 Dashboard & Balance Tracking (R2, R3)**: Real-time leave balance calculation and dashboard display
- **👨‍💼 Manager Approval Workflow (R4)**: Managers can approve/reject pending leave requests
- **🔔 Notification System (R5)**: Automated notifications for requests and status updates
- **📅 Leave History (R12)**: Complete history of all leave requests with status tracking
- **🔒 Data Security (R8)**: JWT authentication, role-based permissions, and data integrity
- **👩‍💼 HR Global View (R10)**: HR dashboard with filtering by department, date range, and leave type

### 🛠️ Technical Features

- **RESTful API**: Comprehensive API endpoints for all operations
- **Role-Based Access**: Employee, Manager, and HR role permissions
- **Business Logic Validation**: Leave balance checks, overlap detection, working day calculations
- **MySQL Database**: Robust data storage with proper relationships
- **JWT Authentication**: Secure token-based authentication
- **Admin Interface**: Django admin for system management

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- MySQL Server 5.7+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/g4Joey/Leave-Request-Management.git
   cd Leave-Request-Management
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Set up database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py create_test_data  # Optional: Create sample data
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - API: http://127.0.0.1:8000/api/
   - Admin: http://127.0.0.1:8000/admin/

## 📖 API Documentation

### Authentication
```bash
POST /api/auth/token/          # Get JWT token
POST /api/auth/token/refresh/  # Refresh JWT token
```

### Leave Management
```bash
# Employee Endpoints
POST /api/leaves/requests/           # Submit leave request (R1)
GET  /api/leaves/requests/           # List my leave requests
GET  /api/leaves/requests/dashboard/ # Dashboard summary (R2)
GET  /api/leaves/requests/history/   # Leave history (R12)
GET  /api/leaves/balances/           # View leave balances (R2, R3)
GET  /api/leaves/types/              # Available leave types

# Manager Endpoints
GET  /api/leaves/manager/                    # View all requests (R4)
GET  /api/leaves/manager/pending_approvals/ # Pending approvals
PUT  /api/leaves/manager/{id}/approve/       # Approve request (R4)
PUT  /api/leaves/manager/{id}/reject/        # Reject request (R4)
```

### Example API Usage

**Get Authentication Token:**
```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe@company.com", "password": "password123"}'
```

**Submit Leave Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/leaves/requests/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type": 1,
    "start_date": "2025-10-01",
    "end_date": "2025-10-05",
    "reason": "Family vacation"
  }'
```

## 🏗️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Django 5.0.7 | Web framework |
| **Frontend** | React 18.2.0 + Tailwind CSS | Modern UI/UX |
| **API** | Django REST Framework 3.15.2 | RESTful API |
| **Database** | MySQL 8.0 (Production & Dev) | Data storage |
| **Authentication** | JWT (Simple JWT) | Secure authentication |
| **Deployment** | DigitalOcean App Platform | Cloud hosting |

## 🖥️ Frontend Features

- **🎨 Modern React UI** with Tailwind CSS styling
- **🔐 JWT Authentication** with automatic token refresh
- **📱 Responsive Design** works on all devices
- **⚡ Real-time Updates** for leave requests and approvals
- **👥 Role-based Interface** (Employee, Manager, HR views)
- **📊 Dashboard Analytics** with leave balance tracking

### Frontend Structure
```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Login.js        # Authentication page
│   │   ├── Dashboard.js    # Employee dashboard
│   │   ├── LeaveRequest.js # Submit leave requests
│   │   ├── LeaveHistory.js # View request history
│   │   └── ManagerDashboard.js # Manager approvals
│   ├── contexts/           # React contexts
│   │   └── AuthContext.js  # Authentication state
│   ├── services/           # API services
│   │   └── api.js          # Axios API client
│   └── App.js              # Main app component
├── public/                 # Static files
└── package.json           # Dependencies
```

## 📁 Project Structure

```
Leave-Request-Management/
├── leave_management/          # Django project settings
│   ├── settings.py           # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
├── users/                    # User management app
│   ├── models.py            # User and Department models
│   └── admin.py             # Admin interface
├── leaves/                   # Leave management app
│   ├── models.py            # Leave, Balance, Request models
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   ├── urls.py              # Leave API URLs
│   └── management/commands/ # Management commands
├── notifications/            # Notification system
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── manage.py                # Django management script
└── README.md                # This file
```

## 🧪 Test Data

The system includes a management command to create test data:

```bash
python manage.py create_test_data
```

**Test Accounts (development only):**
- **Employee**: `john.doe@company.com` / `password123`
- **Manager**: `manager@company.com` / `password123` 
- **HR**: `hr@company.com` / `password123`

Note: These are intended for local/dev use. The login UI now hides demo credentials in production builds by default. To show them locally, set `REACT_APP_SHOW_DEMO_LOGINS=true` in your env before `npm start`.

## � Seeding real users safely (no passwords in Git)

Use the management command `setup_production_data` to create/update real users from environment variables or a local, gitignored file. Credentials are never committed.

Options:
- Set `SEED_USERS` env var to a JSON array during deploy/runtime
- Or set `SEED_USERS_FILE` to a path of a JSON file on disk (e.g., mounted secret)
- Local dev: put a JSON file at `local/seed_users.json` (this path is ignored by Git) and run the command

Example JSON (do NOT commit real credentials):

```json
[
   {
      "username": "manager1",
      "first_name": "Ato",
      "last_name": "Lastname",
      "email": "manager1@example.com",
      "role": "manager",
      "department": "IT",
      "password": "<set-at-deploy>"
   },
   {
      "username": "staff1",
      "first_name": "Augustine",
      "last_name": "Lastname",
      "email": "staff1@example.com",
      "role": "staff",
      "department": "IT",
      "password": "<set-at-deploy>"
   },
   {
      "username": "staff2",
      "first_name": "George",
      "last_name": "Lastname",
      "email": "staff2@example.com",
      "role": "staff",
      "department": "IT",
      "password": "<set-at-deploy>"
   }
]
```

Run:

```bash
python manage.py setup_production_data
```

This command is idempotent and also ensures default leave types and balances for all active users.

## �🔧 Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Checking Code Quality
```bash
python manage.py check
```

## 📋 Requirements Mapping

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **R1** | POST /api/leaves/requests/ | ✅ |
| **R2** | Dashboard API with calculations | ✅ |
| **R3** | Balance tracking and display | ✅ |
| **R4** | Manager approval workflow | ✅ |
| **R5** | Notification system | 🔄 |
| **R6** | Calendar view | 📅 Future |
| **R7** | Admin policy management | 📅 Future |
| **R8** | Security and data integrity | ✅ |
| **R9** | Management reports | 📅 Future |
| **R10** | HR global view | 🔄 |
| **R11** | Complex policy rules | 📅 Future |
| **R12** | Leave request history | ✅ |

## 🚀 Deployment

### DigitalOcean App Platform (Recommended)

This project is configured for easy deployment on DigitalOcean App Platform using the included `.do/app.yaml` configuration.

#### 🔧 Manual Deployment Steps:

1. **Create DigitalOcean Account**
   - Sign up at [DigitalOcean](https://digitalocean.com)
   - Navigate to App Platform

2. **Deploy from GitHub**
   ```bash
   # Fork the repository to your GitHub account
   # In DigitalOcean App Platform:
   # 1. Click "Create App" 
   # 2. Choose "GitHub" as source
   # 3. Select your forked repository
   # 4. DigitalOcean will auto-detect the .do/app.yaml config
   ```

3. **Environment Variables**
   Set these in DigitalOcean App Platform:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=your-app-domain.ondigitalocean.app
   CORS_ALLOWED_ORIGINS=https://your-frontend-domain.ondigitalocean.app
   ```

4. **Database**
   - DigitalOcean will automatically create a MySQL 8.0 database
   - Database credentials are auto-injected via `DATABASE_URL`
   - PyMySQL driver used for pure Python MySQL connectivity

#### 🚀 One-Click Deployment:

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/g4Joey/Leave-Request-Management/tree/main)

### Alternative Production Deployments

#### Railway
```bash
# Create account at railway.app
# Connect GitHub repository
# Configure environment variables
# Deploy automatically
```

#### Heroku
```bash
# Install Heroku CLI
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

### Local Production Testing
```bash
# Set environment variables
export DJANGO_SETTINGS_MODULE=leave_management.settings_production
export DEBUG=False
export SECRET_KEY=your-secret-key

# Install production dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn leave_management.wsgi:application
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**g4Joey** - [GitHub Profile](https://github.com/g4Joey)

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/g4Joey/Leave-Request-Management/issues) page
2. Create a new issue with detailed description
3. Contact the maintainer

## 🎯 Roadmap

### ✅ Completed Features
- [x] **Django Backend API** - Complete REST API with authentication
- [x] **React Frontend** - Modern UI with Tailwind CSS
- [x] **JWT Authentication** - Secure token-based auth
- [x] **Leave Management** - Submit, approve, track requests
- [x] **Role-based Access** - Employee, Manager, HR permissions
- [x] **Dashboard Analytics** - Real-time leave balance tracking
- [x] **Production Deployment** - DigitalOcean ready configuration

### 🔄 In Development
- [ ] **Live Deployment** - DigitalOcean App Platform hosting
- [ ] **CI/CD Pipeline** - Automated deployments
- [ ] **Email Notifications** - Request status updates

### 📅 Future Enhancements
- [ ] **Calendar View** - Visual leave calendar
- [ ] **Advanced Reporting** - Analytics and insights
- [ ] **Mobile App** - React Native application
- [ ] **HR Integration** - HRIS system connectors
- [ ] **Approval Workflows** - Multi-level approvals
- [ ] **Leave Policies** - Complex rule engine

---

**⭐ Star this repository if you find it helpful!**