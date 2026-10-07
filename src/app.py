"""
High School Activities Management API

A simple FastAPI application that allows students to view activities and
teachers to manage student registrations at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing activities and teacher-managed student registrations")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
PASSWORD_HASH_ITERATIONS = 310_000
TEACHER_SESSION_SECONDS = 8 * 60 * 60
bearer_scheme = HTTPBearer(auto_error=False)
teacher_sessions: dict[str, tuple[str, float]] = {}


class TeacherCredentials(BaseModel):
    username: str
    password: str


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return a randomly salted PBKDF2 password hash and its salt, both hex-encoded."""
    if salt is None:
        salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return salt.hex(), password_hash.hex()


def load_teacher_accounts() -> list[dict[str, str]]:
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
        teachers = data["teachers"]
        if not isinstance(teachers, list):
            raise ValueError("The 'teachers' property must be a list.")
        for teacher in teachers:
            if not isinstance(teacher, dict) or not all(
                isinstance(teacher.get(key), str)
                for key in ("username", "salt", "password_hash")
            ):
                raise ValueError("Each teacher needs username, salt, and password_hash.")
        return teachers
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration is missing or invalid.",
        ) from error


def require_teacher(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = teacher_sessions.get(credentials.credentials)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Teacher session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username, expires_at = session
    if expires_at <= time.time():
        del teacher_sessions[credentials.credentials]
        raise HTTPException(
            status_code=401,
            detail="Teacher session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


@app.post("/auth/login")
def teacher_login(login: TeacherCredentials):
    teacher = next(
        (account for account in load_teacher_accounts()
         if account["username"] == login.username),
        None,
    )
    if teacher is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    try:
        salt = bytes.fromhex(teacher["salt"])
        expected_hash = bytes.fromhex(teacher["password_hash"])
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration is missing or invalid.",
        ) from error

    _, password_hash = hash_password(login.password, salt)
    if not hmac.compare_digest(bytes.fromhex(password_hash), expected_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    now = time.time()
    expired_sessions = [
        token for token, (_, expires_at) in teacher_sessions.items()
        if expires_at <= now
    ]
    for expired_token in expired_sessions:
        del teacher_sessions[expired_token]

    token = secrets.token_urlsafe(32)
    teacher_sessions[token] = (login.username, now + TEACHER_SESSION_SECONDS)
    return {"access_token": token, "token_type": "bearer", "username": login.username}


@app.post("/auth/logout")
def teacher_logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    _: str = Depends(require_teacher),
):
    teacher_sessions.pop(credentials.credentials, None)
    return {"message": "Logged out"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _: str = Depends(require_teacher)):
    """Register a student for an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _: str = Depends(require_teacher)
):
    """Unregister a student from an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
