#!/usr/bin/env python
"""Create a new user in the database."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
from sqlalchemy import select

from app.database import async_session_maker, create_tables
from app.models.user import User


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def create_user(email: str, password: str, full_name: str | None = None) -> None:
    """Create a new user in the database."""
    # Ensure tables exist
    await create_tables()
    
    async with async_session_maker() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"❌ User with email '{email}' already exists!")
            return
        
        # Create new user
        hashed_password = hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
        )
        
        session.add(user)
        await session.commit()
        
        print(f"✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {full_name or 'N/A'}")


def main() -> None:
    """Parse arguments and create user."""
    parser = argparse.ArgumentParser(description="Create a new NerdsIQ user")
    parser.add_argument("--email", "-e", required=True, help="User email address")
    parser.add_argument("--password", "-p", required=True, help="User password (min 8 chars)")
    parser.add_argument("--name", "-n", help="User full name (optional)")
    
    args = parser.parse_args()
    
    if len(args.password) < 8:
        print("❌ Password must be at least 8 characters!")
        sys.exit(1)
    
    asyncio.run(create_user(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
