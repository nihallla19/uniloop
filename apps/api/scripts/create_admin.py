"""Promote an existing account to admin: `uv run python -m scripts.create_admin you@college.edu`.

The person signs in once first so they accept the terms themselves.
"""

import sys

from sqlalchemy import Connection, text

from app.db import get_engine


def promote(conn: Connection, email: str) -> bool:
    row = conn.execute(
        text(
            "UPDATE identity.users SET role = 'admin' "
            "WHERE email = :email AND status = 'active' RETURNING id"
        ),
        {"email": email.strip().lower()},
    ).first()
    return row is not None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.create_admin <email>")
    with get_engine().begin() as conn:
        if not promote(conn, sys.argv[1]):
            sys.exit("No active account with that email. Sign in once first, then rerun.")
    print("Promoted to admin.")
