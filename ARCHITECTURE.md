# Application Architecture

## Overview

The Shift Scheduler application is built with scalability and modularity in mind. The architecture follows best practices for Flask applications and allows for easy addition of new features.

## Directory Structure

```
shift_scheduler_app/
├── app.py                 # Application factory
├── config.py             # Configuration management
├── constants.py          # Application-wide constants
├── extensions.py        # Flask extensions initialization
│
├── core/                 # Core application components
│   ├── __init__.py
│   ├── base.py           # Base classes (BaseModule, BaseService, BaseValidator)
│   ├── exceptions.py     # Custom exceptions
│   ├── logger.py         # Logging configuration
│   ├── middleware.py     # Request/response middleware
│   └── module_registry.py # Module registration system
│
├── services/             # Business logic layer
│   ├── __init__.py
│   ├── base_service.py  # Base service class
│   ├── user_service.py  # User business logic
│   ├── shift_service.py # Shift business logic
│   ├── project_service.py # Project business logic
│   └── notification_service.py # Notification business logic
│
├── auth/                 # Authentication module
│   ├── __init__.py
│   └── routes.py
│
├── manager/              # Manager module
│   ├── __init__.py
│   └── routes.py
│
├── member/               # Member module
│   ├── __init__.py
│   └── routes.py
│
├── project/              # Project module
│   ├── __init__.py
│   └── routes.py
│
├── utils/                # Utility functions
│   ├── __init__.py
│   └── email_utils.py
│
├── static/               # Static files
│   ├── css/
│   └── uploads/
│
└── templates/            # Jinja2 templates
    ├── base.html
    ├── auth/
    ├── manager/
    ├── member/
    └── project/
```

## Architecture Layers

### 1. Presentation Layer (Routes)
- **Location**: `auth/`, `manager/`, `member/`, `project/`
- **Responsibility**: Handle HTTP requests, validate input, call services, return responses
- **Best Practice**: Keep routes thin, delegate business logic to services

### 2. Business Logic Layer (Services)
- **Location**: `services/`
- **Responsibility**: Business logic, data validation, database operations
- **Best Practice**: Services should be independent and reusable

### 3. Data Access Layer
- **Location**: Services use MongoDB through `extensions.mongo`
- **Responsibility**: Database operations, data persistence
- **Best Practice**: Use service methods instead of direct database access in routes

### 4. Core Components
- **Location**: `core/`
- **Responsibility**: Base classes, exceptions, middleware, module registry
- **Best Practice**: Extend base classes for consistency

## Key Components

### Base Classes

#### BaseService
- Provides common database operations
- All services should inherit from this
- Example: `ShiftService`, `UserService`

#### BaseValidator
- Provides validation framework
- All validators should inherit from this
- Example: `ShiftValidator`, `UserValidator`

#### BaseModule
- Provides module registration framework
- For future module system expansion

### Services

Services encapsulate business logic:

- **UserService**: User management, authentication helpers
- **ShiftService**: Shift creation, validation, conflict checking
- **ProjectService**: Project management, member assignment
- **NotificationService**: Notification creation and management

### Middleware

- **AuthMiddleware**: Adds user info to requests
- **LoggingMiddleware**: Logs requests and responses
- **Custom Middleware**: Easy to add new middleware

### Module Registry

The module registry allows dynamic module loading:

```python
from core.module_registry import registry

# Register a new module
registry.register_module(module_instance, blueprint, url_prefix="/module")
```

## Adding New Features

### Quick Start

1. **Create Service** (if needed): `services/your_service.py`
2. **Create Routes**: `your_module/routes.py`
3. **Register Blueprint**: In `app.py` or via module registry
4. **Create Templates**: `templates/your_module/`

See `MODULE_DEVELOPMENT_GUIDE.md` for detailed instructions.

## Configuration

Configuration is managed through:
- `config.py`: Application configuration class
- `.env`: Environment variables (not committed)
- `constants.py`: Application-wide constants

## Error Handling

Custom exceptions in `core/exceptions.py`:
- `AppException`: Base exception
- `ValidationError`: Input validation errors
- `NotFoundError`: Resource not found
- `UnauthorizedError`: Authentication errors
- `ForbiddenError`: Authorization errors

## Logging

Logging is configured in `core/logger.py`:
- Development: Console logging
- Production: File logging with rotation

## Testing

Services are designed to be easily testable:
- Services can be instantiated independently
- Database operations are abstracted
- Mock services can be created for testing

## Scalability Features

1. **Modular Architecture**: Easy to add/remove modules
2. **Service Layer**: Business logic separated from routes
3. **Base Classes**: Consistent patterns across modules
4. **Module Registry**: Dynamic module loading
5. **Middleware System**: Easy to add cross-cutting concerns
6. **Error Handling**: Centralized error management
7. **Logging**: Comprehensive logging system
8. **Configuration Management**: Environment-based config

## Future Enhancements

Potential areas for expansion:
- Caching layer (Redis)
- Message queue (Celery)
- API versioning
- Rate limiting
- API documentation (Swagger)
- Unit and integration tests
- Docker containerization
- CI/CD pipeline

