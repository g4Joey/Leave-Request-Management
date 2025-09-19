# Technology Stack Documentation

## Leave Management System - Technology Stack

### Overview
This leave management system is built using the following technology stack:

**Backend Framework:** Python + Django + MySQL

### Technology Components

#### 1. **Python 3.13.3**
- **Purpose**: Primary programming language
- **Environment**: Virtual environment setup in `.venv/`
- **Why chosen**: Excellent for rapid development, great ecosystem, strong community support

#### 2. **Django 5.0.7**
- **Purpose**: Web framework for building the backend API and admin interface
- **Features**: 
  - Built-in admin interface
  - ORM for database operations
  - Authentication and authorization
  - Security features (CSRF, XSS protection)
- **Why chosen**: "Batteries included" framework, perfect for business applications

#### 3. **Django REST Framework 3.15.2**
- **Purpose**: Building RESTful APIs for frontend consumption
- **Features**:
  - Serialization
  - Authentication (JWT)
  - API browsing interface
  - Pagination
- **Why chosen**: Industry standard for Django APIs

#### 4. **MySQL Database**
- **Driver**: PyMySQL 1.1.1 (Pure Python MySQL client)
- **Purpose**: Primary data storage
- **Features**:
  - ACID compliance
  - Scalability
  - Data integrity
- **Why chosen**: Reliable, well-supported, suitable for HR data

#### 5. **Additional Packages**

##### Security & Configuration
- **python-decouple**: Environment variable management
- **djangorestframework-simplejwt**: JWT authentication
- **django-cors-headers**: Cross-origin resource sharing

##### Development & Testing
- **pytest**: Testing framework
- **pytest-django**: Django-specific testing utilities

##### Production
- **gunicorn**: WSGI HTTP Server for production deployment

### Project Structure
```
Leave management/
├── .venv/                    # Virtual environment
├── .env                      # Environment variables
├── .env.example              # Environment template
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── leave_management/         # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Main configuration
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
├── app/                      # Custom applications will go here
└── tests/                    # Test files
```

### Development Environment Setup

#### Prerequisites
- Python 3.13.3 installed
- MySQL Server installed and running
- Git for version control

#### Setup Steps
1. **Clone and navigate to project**
   ```bash
   cd "d:\Desktop\Leave management"
   ```

2. **Activate virtual environment**
   ```bash
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. **Configure environment**
   - Copy `.env.example` to `.env`
   - Update database credentials in `.env`

5. **Database setup**
   ```bash
   .venv\Scripts\python.exe manage.py makemigrations
   .venv\Scripts\python.exe manage.py migrate
   ```

6. **Create superuser**
   ```bash
   .venv\Scripts\python.exe manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   .venv\Scripts\python.exe manage.py runserver
   ```

### Key Configuration Features

#### Database Configuration
- Uses PyMySQL as MySQL driver (pure Python, no compilation needed)
- Environment-based configuration
- Connection pooling and optimization settings

#### API Configuration
- JWT-based authentication
- CORS enabled for frontend integration
- Pagination configured (20 items per page)
- REST API standards compliance

#### Security Features
- Environment-based secret key management
- CORS configuration
- Django's built-in security middleware
- JWT token-based authentication

### Next Steps for Development
1. Create Django apps for core functionality (users, leaves, notifications)
2. Design database models based on requirements
3. Implement API endpoints
4. Add frontend integration
5. Implement business logic and validation rules

### Architecture Benefits
- **Scalable**: Django can handle growth from small teams to large enterprises
- **Secure**: Built-in security features and best practices
- **Maintainable**: Clear separation of concerns, well-documented
- **Testable**: Comprehensive testing framework support
- **Deployable**: Production-ready with gunicorn and standard deployment options

### Requirements Mapping
This technology stack directly supports all the Must/Should requirements:
- **R1-R3**: Django models and ORM for leave tracking
- **R4**: Django admin + custom views for manager approval
- **R5**: Django signals and email backend for notifications
- **R8**: Django's security framework
- **R10**: Role-based permissions and filtering