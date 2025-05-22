# Event Scheduling API

A RESTful API for event scheduling with collaborative editing features, built with Django and Django REST Framework.

## Features

- Secure authentication with JWT tokens
- Role-based access control (Owner, Editor, Viewer)
- CRUD operations for events
- Recurring events support
- Conflict detection
- Batch operations
- Real-time notifications
- Version control with rollback capability
- Changelog with diff visualization
- Event conflict resolution

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with:
```
DEBUG=True
SECRET_KEY=your-secret-key
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

## Testing

Run the test suite:
```bash
python manage.py test
```

## API Endpoints


### Authentication
- POST /api/auth/register - Register a new user
- POST /api/auth/login - Login and receive an authentication token
- POST /api/auth/refresh - Refresh an authentication token
- POST /api/auth/logout - Invalidate the current token

### Event Management
- POST /api/events - Create a new event
- GET /api/events - List all events
- GET /api/events/{id} - Get a specific event
- PUT /api/events/{id} - Update an event
- DELETE /api/events/{id} - Delete an event
- POST /api/events/batch - Create multiple events

### Collaboration
- POST /api/events/{id}/share - Share an event
- GET /api/events/{id}/permissions - List permissions
- PUT /api/events/{id}/permissions/{userId} - Update permissions
- DELETE /api/events/{id}/permissions/{userId} - Remove access

### Version History
- GET /api/events/{id}/history/{versionId} - Get a specific version
- POST /api/events/{id}/rollback/{versionId} - Rollback to a previous version

### Changelog & Diff
- GET /api/events/{id}/changelog - Get change history
- GET /api/events/{id}/diff/{versionId1}/{versionId2} - Get diff between versions 
