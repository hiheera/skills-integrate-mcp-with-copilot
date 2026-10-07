"""Add or replace a teacher login in the local teacher account file."""

import json
from getpass import getpass
from pathlib import Path

from app import hash_password, load_teacher_accounts, TEACHERS_FILE


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass("Teacher password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")

    salt, password_hash = hash_password(password)
    teachers = [account for account in load_teacher_accounts()
                if account["username"] != username]
    teachers.append(
        {"username": username, "salt": salt, "password_hash": password_hash}
    )
    TEACHERS_FILE.write_text(
        json.dumps({"teachers": teachers}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Teacher account '{username}' saved to {Path(TEACHERS_FILE).name}.")


if __name__ == "__main__":
    main()
