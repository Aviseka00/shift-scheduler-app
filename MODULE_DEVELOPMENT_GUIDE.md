# Module Development Guide

This guide explains how to add new modules and features to the Shift Scheduler application.

## Architecture Overview

The application follows a modular architecture with clear separation of concerns:

```
app.py                    # Application factory
├── core/                 # Core components (base classes, exceptions, middleware)
├── services/             # Business logic layer
├── models/               # Data models (if needed)
├── validators/           # Input validation
├── middleware/         # Request/response processing
├── auth/                 # Authentication module
├── manager/             # Manager module
├── member/               # Member module
└── project/             # Project module
```

## Adding a New Module

### Step 1: Create Module Structure

Create a new directory for your module:

```
new_module/
├── __init__.py          # Module initialization
├── routes.py            # Route definitions
├── services.py          # Business logic (optional, can use shared services)
└── validators.py        # Input validation (optional)
```

### Step 2: Create Blueprint

In `new_module/__init__.py`:

```python
from flask import Blueprint

new_module_bp = Blueprint(
    "new_module",
    __name__,
    template_folder="../templates/new_module",
    url_prefix="/new-module"
)

from . import routes
```

### Step 3: Define Routes

In `new_module/routes.py`:

```python
from flask import render_template, request, jsonify, session
from . import new_module_bp
from core.middleware import require_role
from services.your_service import YourService

@new_module_bp.route("/dashboard")
@require_role("manager")  # or require_roles("manager", "member")
def dashboard():
    service = YourService()
    data = service.get_data()
    return render_template("new_module/dashboard.html", data=data)

@new_module_bp.route("/api/data")
@require_role("manager")
def api_data():
    service = YourService()
    data = service.get_data()
    return jsonify(data)
```

### Step 4: Create Service (if needed)

In `services/your_service.py`:

```python
from services.base_service import BaseService
from core.exceptions import ValidationError, NotFoundError

class YourService(BaseService):
    def __init__(self):
        super().__init__("your_collection")
    
    def validate_data(self, data):
        # Validation logic
        if not data.get("field"):
            raise ValidationError("Field is required")
        return True
    
    def get_data(self):
        return self.find_many()
```

### Step 5: Register Module

In `app.py`:

```python
from new_module import new_module_bp

def create_app():
    app = Flask(__name__)
    # ... existing code ...
    
    # Register new module
    app.register_blueprint(new_module_bp)
    
    return app
```

## Using Services

Services contain business logic and database operations. Use them in routes:

```python
from services.shift_service import ShiftService

@route("/shifts")
def get_shifts():
    service = ShiftService()
    shifts = service.get_user_shifts(user_id="...")
    return jsonify(shifts)
```

## Using Validators

Create validators for input validation:

```python
from core.base import BaseValidator

class ShiftValidator(BaseValidator):
    def validate(self, data):
        if not data.get("date"):
            return False, "Date is required"
        return True, None
```

## Using Middleware

The application includes built-in middleware:

- `AuthMiddleware`: Adds user info to request
- `LoggingMiddleware`: Logs requests and responses

To create custom middleware:

```python
from core.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request):
        # Process request
        return None
    
    def process_response(self, request, response):
        # Process response
        return response
```

## Error Handling

Use custom exceptions:

```python
from core.exceptions import ValidationError, NotFoundError, UnauthorizedError

# In your service or route
if not found:
    raise NotFoundError("Resource", resource_id)

if not valid:
    raise ValidationError("Invalid data", field="field_name")
```

## Constants

Add application-wide constants to `constants.py`:

```python
# Your constants
YOUR_CONSTANTS = {
    "KEY1": "value1",
    "KEY2": "value2",
}
```

## Best Practices

1. **Separation of Concerns**: Keep routes thin, move logic to services
2. **Reusability**: Use base classes and shared services
3. **Validation**: Always validate input data
4. **Error Handling**: Use custom exceptions for better error messages
5. **Logging**: Use the logger for debugging and monitoring
6. **Testing**: Write tests for services and routes
7. **Documentation**: Document your module's purpose and usage

## Example: Complete Module

See `examples/example_module/` for a complete example module implementation.

## Questions?

Refer to existing modules (`auth/`, `manager/`, `member/`, `project/`) for examples of how modules are structured.

