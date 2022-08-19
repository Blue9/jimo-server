import uuid

from app.core.database.models import FCMTokenRow
from sqlalchemy import select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def register_fcm_token(db: AsyncSession, user_id: uuid.UUID, token: str):
    query = select(FCMTokenRow).where(FCMTokenRow.user_id == user_id, FCMTokenRow.token == token)
    exists_query = await db.execute(exists(query).select())
    existing = exists_query.scalar()
    if existing:
        return
    fcm_token = FCMTokenRow(user_id=user_id, token=token)
    db.add(fcm_token)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()


async def remove_fcm_token(db: AsyncSession, user_id: uuid.UUID, token: str):
    query = delete(FCMTokenRow).where(FCMTokenRow.token == token, FCMTokenRow.user_id == user_id)
    await db.execute(query)
    await db.commit()
