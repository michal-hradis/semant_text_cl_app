"""Reset a user's password directly in the database.

Usage:
    python reset_password.py user@example.com            # prompts for password
    python reset_password.py user@example.com NEWPASS    # password as argument

Uses DATABASE_URL from the environment (same as the app).
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select

from text_classifier.config import config
from text_classifier.database import User, async_session_maker, engine


async def reset_password(email: str, password: str) -> bool:
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.hashed_password = PasswordHelper().hash(password)
        await session.commit()
    await engine.dispose()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset a user's password.")
    parser.add_argument("email")
    parser.add_argument("password", nargs="?", help="New password (prompted if omitted)")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    if not password:
        print("Empty password not allowed.", file=sys.stderr)
        return 1

    if not asyncio.run(reset_password(args.email, password)):
        print(f"User '{args.email}' not found in {config.DATABASE_URL}", file=sys.stderr)
        return 1
    print(f"Password for '{args.email}' updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
