# Mergington High School Activities API

A simple FastAPI application that allows students to view extracurricular activities and teachers to manage student registrations.

## Features

- View all available extracurricular activities
- Teachers can sign students up for activities and unregister them
- Students can view activity rosters without logging in

## Teacher accounts

Teacher credentials are stored in `src/teachers.json` as salted PBKDF2 password
hashes; plaintext passwords are not stored. Create or replace an account with:

```
python src/manage_teachers.py
```

The tool prompts for the username and password without echoing the password.
Keep `teachers.json` access limited to trusted staff and back it up securely.
Teacher sessions expire after eight hours and are invalidated when the server
restarts. The sample application stores activities and sessions in memory, so
this lightweight authentication setup is intended for the demo rather than a
production deployment. Use HTTPS when exposing the app beyond localhost.

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python -m uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                             | Description                                              |
| ------ | -------------------------------------------------------------------- | -------------------------------------------------------- |
| GET    | `/activities`                                                        | View activities and current participant lists           |
| POST   | `/auth/login`                                                        | Log a teacher in and receive a temporary bearer token    |
| POST   | `/auth/logout`                                                       | Invalidate the current teacher session                  |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu`    | Register a student (teacher bearer token required)        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher bearer token required)     |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
