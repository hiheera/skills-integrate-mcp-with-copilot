import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials

from src import app as activities_app


class TeacherAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_teachers_file = activities_app.TEACHERS_FILE
        activities_app.TEACHERS_FILE = Path(self.temp_dir.name) / "teachers.json"
        activities_app.teacher_sessions.clear()

        salt, password_hash = activities_app.hash_password("correct horse battery")
        activities_app.TEACHERS_FILE.write_text(
            json.dumps({
                "teachers": [{
                    "username": "teacher",
                    "salt": salt,
                    "password_hash": password_hash,
                }]
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        activities_app.TEACHERS_FILE = self.original_teachers_file
        activities_app.teacher_sessions.clear()
        self.temp_dir.cleanup()

    def test_valid_teacher_can_login_and_logout(self):
        response = activities_app.teacher_login(
            activities_app.TeacherCredentials(
                username="teacher", password="correct horse battery"
            )
        )
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=response["access_token"]
        )

        self.assertEqual(activities_app.require_teacher(credentials), "teacher")
        activities_app.teacher_logout(credentials, "teacher")
        with self.assertRaises(HTTPException) as error:
            activities_app.require_teacher(credentials)
        self.assertEqual(error.exception.status_code, 401)

    def test_missing_credentials_are_rejected(self):
        with self.assertRaises(HTTPException) as error:
            activities_app.require_teacher(None)
        self.assertEqual(error.exception.status_code, 401)

    def test_invalid_credentials_are_rejected(self):
        with self.assertRaises(HTTPException) as error:
            activities_app.teacher_login(
                activities_app.TeacherCredentials(
                    username="teacher", password="incorrect"
                )
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_signup_and_unregister_routes_require_teacher_authentication(self):
        protected_routes = {
            route.endpoint.__name__: route
            for route in activities_app.app.routes
            if isinstance(route, APIRoute) and route.endpoint.__name__ in {
                "signup_for_activity",
                "unregister_from_activity",
            }
        }

        self.assertEqual(
            set(protected_routes),
            {"signup_for_activity", "unregister_from_activity"},
        )
        for route in protected_routes.values():
            self.assertIn(
                activities_app.require_teacher,
                [dependency.call for dependency in route.dependant.dependencies],
            )


if __name__ == "__main__":
    unittest.main()
