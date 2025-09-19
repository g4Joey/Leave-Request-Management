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
| **API** | Django REST Framework 3.15.2 | RESTful API |
| **Database** | MySQL with PyMySQL | Data storage |
| **Authentication** | JWT (Simple JWT) | Secure authentication |
| **Environment** | Python 3.13.3 | Runtime environment |

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

**Test Accounts:**
- **Employee**: `john.doe@company.com` / `password123`
- **Manager**: `manager@company.com` / `password123` 
- **HR**: `hr@company.com` / `password123`

## 🔧 Development

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

### Production Settings

1. Set `DEBUG=False` in `.env`
2. Configure proper `SECRET_KEY`
3. Set up production database
4. Configure static files serving
5. Use `gunicorn` for WSGI server

### Docker Deployment (Future)
```bash
# Coming soon
docker-compose up -d
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

- [ ] Frontend UI (React/Vue.js)
- [ ] Calendar view integration
- [ ] Email notifications
- [ ] Advanced reporting
- [ ] Mobile app
- [ ] Integration with HR systems

---

**⭐ Star this repository if you find it helpful!**