"""Run: python -m scripts.seed_admin (from backend/ directory)"""
import asyncio

from src.core.config import get_settings
from src.core.database import AsyncSessionLocal
from src.core.security import hash_password
from src.repositories.user_repo import UserRepository


async def seed() -> None:
    settings = get_settings()
    username = settings.admin_username
    password = settings.admin_password

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_username(username)
        if existing:
            print(f"[seed_admin] User '{username}' already exists — skipping.")
            return
        hashed = hash_password(password)
        user = await repo.create(username=username, hashed_pw=hashed, role="admin")
        await session.commit()
        print(f"[seed_admin] Created admin user '{user.username}' (id={user.id}).")


if __name__ == "__main__":
    asyncio.run(seed())
