"""Basic admin endpoints."""
import uuid
from collections import namedtuple
from typing import Optional

import shared.stores.utils
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from app.api.utils import get_user_store
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, select, func
from sqlalchemy.exc import IntegrityError

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from shared.models import models

router = APIRouter()

Page = namedtuple("Page", ["offset", "limit"])


async def get_admin_or_raise(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
) -> schemas.internal.InternalUser:
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, uid=firebase_user.uid)
    if not user.is_admin:
        raise HTTPException(403)
    return user


def get_page(page: int = Query(1, gt=0), limit: int = Query(100, gt=0, le=1000)) -> Page:
    return Page(offset=(page - 1) * limit, limit=limit)


# User endpoints
@router.get("/users", response_model=schemas.admin.Page[schemas.admin.User])
async def get_users(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all users."""
    total_query = await db.execute(select(func.count(models.User.id)))
    total = total_query.scalar()
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    data = (await db.execute(query)).scalars().all()
    return schemas.admin.Page(total=total, data=data)


@router.post("/users", response_model=schemas.admin.User)
async def create_user(
    request: schemas.admin.CreateUserRequest,
    user_store: UserStore = Depends(get_user_store),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise),
):
    """Create a user."""
    created, error = await user_store.create_user(request.uid, request.username, request.first_name, request.last_name)
    if created:
        return created
    elif error:
        raise HTTPException(400, error.json())
    else:
        raise HTTPException(500)


@router.get("/users/{username}", response_model=schemas.admin.User)
async def get_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get the given user."""
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .where(models.User.username_lower == username.lower())
    user = (await db.execute(query)).scalars().first()
    if user is None:
        raise HTTPException(404)
    return user


@router.post("/users/{username}", response_model=schemas.admin.User)
async def update_user(
    username: str,
    request: schemas.admin.UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Update the given user."""
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .where(models.User.username_lower == username.lower())
    executed = await db.execute(query)
    to_update: Optional[models.User] = executed.scalars().first()
    if not to_update:
        raise HTTPException(404)
    if request.username:
        to_update.username = request.username
    if request.first_name:
        to_update.first_name = request.first_name
    if request.last_name:
        to_update.last_name = request.last_name
    to_update.is_featured = request.is_featured
    if admin.id != to_update.id:
        # Avoid getting into a state where there are 0 admins
        to_update.deleted = request.deleted
        to_update.is_admin = request.is_admin
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(400)
    await db.refresh(to_update)
    return to_update


@router.get("/admins", response_model=schemas.admin.Page[schemas.admin.User])
async def get_admins(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all admin users."""
    total_query = await db.execute(select(func.count()).where(models.User.is_admin))
    total = total_query.scalar()
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .where(models.User.is_admin) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    admins_query = await db.execute(query)
    admins = admins_query.scalars().all()
    return schemas.admin.Page(total=total, data=admins)


# Featured users
@router.get("/featuredUsers", response_model=schemas.admin.Page[schemas.admin.User])
async def get_featured_users(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get featured users."""
    total_query = await db.execute(select(func.count()).where(models.User.is_featured))
    total = total_query.scalar()
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .where(models.User.is_featured) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    rows = await db.execute(query)
    featured_users = rows.scalars().all()
    return schemas.admin.Page(total=total, data=featured_users)


# Posts
@router.get("/posts", response_model=schemas.admin.Page[schemas.admin.Post])
async def get_all_posts(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all posts."""
    total_query = await db.execute(select(func.count()).select_from(models.Post))
    total = total_query.scalar()
    query = select(models.Post) \
        .options(*shared.stores.utils.eager_load_post_options()) \
        .order_by(models.Post.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    rows = await db.execute(query)
    posts = rows.scalars().all()
    return schemas.admin.Page(total=total, data=posts)


@router.get("/posts/{post_id}", response_model=schemas.admin.Post)
async def get_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    query = select(models.Post) \
        .options(*shared.stores.utils.eager_load_post_options()) \
        .where(models.Post.id == post_id)
    rows = await db.execute(query)
    post = rows.scalars().first()
    if post is None:
        raise HTTPException(404)
    return post


@router.post("/posts/{post_id}", response_model=schemas.admin.Post)
async def update_post(
    post_id: uuid.UUID,
    request: schemas.admin.UpdatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    query = select(models.Post) \
        .options(*shared.stores.utils.eager_load_post_options()) \
        .where(models.Post.id == post_id)
    rows = await db.execute(query)
    post: Optional[models.Post] = rows.scalars().first()
    if post is None:
        raise HTTPException(404)
    if request.content:
        post.content = request.content
    if request.deleted is not None:
        post.deleted = request.deleted
    await db.commit()
    updated_post_result = await db.execute(query)
    updated_post: models.Post = updated_post_result.scalars().first()
    if updated_post.image is not None:
        if updated_post.deleted:
            await firebase_user.shared_firebase.make_image_private(updated_post.image_blob_name)
        else:
            await firebase_user.shared_firebase.make_image_public(updated_post.image_blob_name)
    return updated_post


# Waitlist
@router.get("/waitlist", response_model=schemas.admin.Page[schemas.admin.Waitlist])
async def get_waitlist(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all users on the waitlist that haven't been invited yet."""
    total_query = select(func.count()) \
        .select_from(models.Waitlist) \
        .where(~exists().where(models.Waitlist.phone_number == models.Invite.phone_number))
    total = (await db.execute(total_query)).scalar()
    query = select(models.Waitlist) \
        .where(~exists().where(models.Waitlist.phone_number == models.Invite.phone_number)) \
        .order_by(models.Waitlist.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    rows = await db.execute(query)
    waitlist = rows.scalars().all()
    return schemas.admin.Page(total=total, data=waitlist)


# Invites
@router.get("/invites", response_model=schemas.admin.Page[schemas.admin.Invite])
async def get_all_invites(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get invited phone numbers that haven't signed up yet."""
    total_query = select(func.count()) \
        .select_from(models.Invite) \
        .where(~exists().where(models.Invite.phone_number == models.User.phone_number))
    total = (await db.execute(total_query)).scalar()
    query = select(models.Invite) \
        .where(~exists().where(models.Invite.phone_number == models.User.phone_number)) \
        .order_by(models.Invite.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    rows = await db.execute(query)
    invites = rows.scalars().all()
    return schemas.admin.Page(total=total, data=invites)


@router.post("/invites", response_model=schemas.admin.Invite)
async def create_invite(
    request: schemas.admin.CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Create invite."""
    invite = models.Invite(phone_number=request.phone_number, invited_by=admin.id)
    try:
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite
    except IntegrityError:
        raise HTTPException(400, "Phone number exists")


@router.delete("/invites", response_model=list[schemas.admin.Invite])
async def remove_invites(
    request: schemas.user.PhoneNumberList,
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Remove invites."""
    query = select(models.Invite).where(models.Invite.phone_number.in_(request.phone_numbers))
    to_delete = (await db.execute(query)).scalars().all()
    for invite in to_delete:
        await db.delete(invite)
    await db.commit()
    return to_delete


# Reports + Feedback
@router.get("/reports", response_model=schemas.admin.Page[schemas.admin.Report])
async def get_post_reports(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all post reports."""
    total_query = await db.execute(select(func.count()).select_from(models.PostReport))
    total = total_query.scalar()
    query = select(models.PostReport) \
        .options(joinedload(models.PostReport.post, innerjoin=True)
                 .options(*shared.stores.utils.eager_load_post_options()),
                 joinedload(models.PostReport.reported_by, innerjoin=True)
                 .options(*shared.stores.utils.eager_load_user_options())) \
        .order_by(models.PostReport.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    reports = (await db.execute(query)).scalars().all()
    return schemas.admin.Page(total=total, data=reports)


@router.get("/feedback", response_model=schemas.admin.Page[schemas.admin.Feedback])
async def get_feedback(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all submitted feedback."""
    total_query = await db.execute(select(func.count()).select_from(models.Feedback))
    total = total_query.scalar()
    query = select(models.Feedback) \
        .options(joinedload(models.Feedback.user, innerjoin=True)
                 .options(*shared.stores.utils.eager_load_user_options())) \
        .order_by(models.Feedback.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit)
    feedback = (await db.execute(query)).scalars().all()
    return schemas.admin.Page(total=total, data=feedback)
