"""Basic admin endpoints."""
import uuid
from collections import namedtuple
from typing import Optional

import shared.stores.utils
from fastapi import APIRouter, Depends, HTTPException, Query
from shared.api.admin import (
    AdminResponsePage,
    AdminAPIUser,
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    AdminAPIPost,
    AdminUpdatePostRequest,
    AdminAPIWaitlist,
    AdminAPIInvite,
    AdminCreateInviteRequest,
    AdminAPIReport,
    AdminAPIFeedback,
)
from shared.api.base import SimpleResponse
from shared.api.internal import InternalUser
from shared.api.user import PhoneNumberList
from shared.models.models import (
    UserRow,
    InviteRow,
    PostReportRow,
    PostRow,
    FeedbackRow,
    WaitlistRow,
)
from shared.stores.user_store import UserStore
from sqlalchemy import exists, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api import utils
from app.api.utils import get_user_store
from app.controllers.dependencies import get_redis
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()

Page = namedtuple("Page", ["offset", "limit"])


async def get_admin_or_raise(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
) -> InternalUser:
    user: InternalUser = await utils.get_user_from_uid_or_raise(user_store, uid=firebase_user.uid)
    if not user.is_admin:
        raise HTTPException(403)
    return user


def get_page(page: int = Query(1, gt=0), limit: int = Query(100, gt=0, le=1000)) -> Page:
    return Page(offset=(page - 1) * limit, limit=limit)


@router.post("/cache/flush", response_model=SimpleResponse)
async def flush_cache(
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Flush the cache."""
    await get_redis().flushdb()
    return SimpleResponse(success=True)


# User endpoints
@router.get("/users", response_model=AdminResponsePage[AdminAPIUser])
async def get_users(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all users."""
    total_query = await db.execute(select(func.count(UserRow.id)))
    total = total_query.scalar()
    query = (
        select(UserRow)
        .options(*shared.stores.utils.eager_load_user_options())
        .order_by(UserRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    data = (await db.execute(query)).scalars().all()
    return AdminResponsePage(total=total, data=data)


@router.post("/users", response_model=AdminAPIUser)
async def create_user(
    request: AdminCreateUserRequest,
    user_store: UserStore = Depends(get_user_store),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Create a user."""
    created, error = await user_store.create_user(request.uid, request.username, request.first_name, request.last_name)
    if created:
        return created
    elif error:
        raise HTTPException(400, error.json())
    else:
        raise HTTPException(500)


@router.get("/users/{username}", response_model=AdminAPIUser)
async def get_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get the given user."""
    query = (
        select(UserRow)
        .options(*shared.stores.utils.eager_load_user_options())
        .where(UserRow.username_lower == username.lower())
    )
    user = (await db.execute(query)).scalars().first()
    if user is None:
        raise HTTPException(404)
    return user


@router.post("/users/{username}", response_model=AdminAPIUser)
async def update_user(
    username: str,
    request: AdminUpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: InternalUser = Depends(get_admin_or_raise),
):
    """Update the given user."""
    query = (
        select(UserRow)
        .options(*shared.stores.utils.eager_load_user_options())
        .where(UserRow.username_lower == username.lower())
    )
    executed = await db.execute(query)
    to_update: Optional[UserRow] = executed.scalars().first()
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


@router.get("/admins", response_model=AdminResponsePage[AdminAPIUser])
async def get_admins(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all admin users."""
    total_query = await db.execute(select(func.count()).where(UserRow.is_admin))
    total = total_query.scalar()
    query = (
        select(UserRow)
        .options(*shared.stores.utils.eager_load_user_options())
        .where(UserRow.is_admin)
        .order_by(UserRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    admins_query = await db.execute(query)
    admins = admins_query.scalars().all()
    return AdminResponsePage(total=total, data=admins)


# Featured users
@router.get("/featuredUsers", response_model=AdminResponsePage[AdminAPIUser])
async def get_featured_users(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get featured users."""
    total_query = await db.execute(select(func.count()).where(UserRow.is_featured))
    total = total_query.scalar()
    query = (
        select(UserRow)
        .options(*shared.stores.utils.eager_load_user_options())
        .where(UserRow.is_featured)
        .order_by(UserRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    rows = await db.execute(query)
    featured_users = rows.scalars().all()
    return AdminResponsePage(total=total, data=featured_users)


# Posts
@router.get("/posts", response_model=AdminResponsePage[AdminAPIPost])
async def get_all_posts(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all posts."""
    total_query = await db.execute(select(func.count()).select_from(PostRow))
    total = total_query.scalar()
    query = (
        select(PostRow)
        .options(*shared.stores.utils.eager_load_post_options())
        .order_by(PostRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    rows = await db.execute(query)
    posts = rows.scalars().all()
    return AdminResponsePage(total=total, data=posts)


@router.get("/posts/{post_id}", response_model=AdminAPIPost)
async def get_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    query = select(PostRow).options(*shared.stores.utils.eager_load_post_options()).where(PostRow.id == post_id)
    rows = await db.execute(query)
    post = rows.scalars().first()
    if post is None:
        raise HTTPException(404)
    return post


@router.post("/posts/{post_id}", response_model=AdminAPIPost)
async def update_post(
    post_id: uuid.UUID,
    request: AdminUpdatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    query = select(PostRow).options(*shared.stores.utils.eager_load_post_options()).where(PostRow.id == post_id)
    rows = await db.execute(query)
    post: Optional[PostRow] = rows.scalars().first()
    if post is None:
        raise HTTPException(404)
    if request.content:
        post.content = request.content
    if request.deleted is not None:
        post.deleted = request.deleted
    await db.commit()
    updated_post_result = await db.execute(query)
    updated_post: PostRow = updated_post_result.scalars().first()  # type: ignore
    if updated_post.image is not None:
        if updated_post.deleted:
            await firebase_user.shared_firebase.make_image_private(updated_post.image_blob_name)
        else:
            await firebase_user.shared_firebase.make_image_public(updated_post.image_blob_name)
    return updated_post


# Waitlist
@router.get("/waitlist", response_model=AdminResponsePage[AdminAPIWaitlist])
async def get_waitlist(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all users on the waitlist that haven't been invited yet."""
    total_query = (
        select(func.count())
        .select_from(WaitlistRow)
        .where(~exists().where(WaitlistRow.phone_number == InviteRow.phone_number))
    )
    total = (await db.execute(total_query)).scalar()
    query = (
        select(WaitlistRow)
        .where(~exists().where(WaitlistRow.phone_number == InviteRow.phone_number))
        .order_by(WaitlistRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    rows = await db.execute(query)
    waitlist = rows.scalars().all()
    return AdminResponsePage(total=total, data=waitlist)


# Invites
@router.get("/invites", response_model=AdminResponsePage[AdminAPIInvite])
async def get_all_invites(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get invited phone numbers that haven't signed up yet."""
    total_query = (
        select(func.count())
        .select_from(InviteRow)
        .where(~exists().where(InviteRow.phone_number == UserRow.phone_number))
    )
    total = (await db.execute(total_query)).scalar()
    query = (
        select(InviteRow)
        .where(~exists().where(InviteRow.phone_number == UserRow.phone_number))
        .order_by(InviteRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    rows = await db.execute(query)
    invites = rows.scalars().all()
    return AdminResponsePage(total=total, data=invites)


@router.post("/invites", response_model=AdminAPIInvite)
async def create_invite(
    request: AdminCreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    admin: InternalUser = Depends(get_admin_or_raise),
):
    """Create invite."""
    invite = InviteRow(phone_number=request.phone_number, invited_by=admin.id)
    try:
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite
    except IntegrityError:
        raise HTTPException(400, "Phone number exists")


@router.delete("/invites", response_model=list[AdminAPIInvite])
async def remove_invites(
    request: PhoneNumberList,
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Remove invites."""
    query = select(InviteRow).where(InviteRow.phone_number.in_(request.phone_numbers))
    to_delete = (await db.execute(query)).scalars().all()
    for invite in to_delete:
        await db.delete(invite)
    await db.commit()
    return to_delete


# Reports + Feedback
@router.get("/reports", response_model=AdminResponsePage[AdminAPIReport])
async def get_post_reports(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all post reports."""
    total_query = await db.execute(select(func.count()).select_from(PostReportRow))
    total = total_query.scalar()
    query = (
        select(PostReportRow)
        .options(
            joinedload(PostReportRow.post, innerjoin=True).options(*shared.stores.utils.eager_load_post_options()),
            joinedload(PostReportRow.reported_by, innerjoin=True).options(
                *shared.stores.utils.eager_load_user_options()
            ),
        )
        .order_by(PostReportRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    reports = (await db.execute(query)).scalars().all()
    return AdminResponsePage(total=total, data=reports)


@router.get("/feedback", response_model=AdminResponsePage[AdminAPIFeedback])
async def get_feedback(
    page: Page = Depends(get_page),
    db: AsyncSession = Depends(get_db),
    _admin: InternalUser = Depends(get_admin_or_raise),
):
    """Get all submitted feedback."""
    total_query = await db.execute(select(func.count()).select_from(FeedbackRow))
    total = total_query.scalar()
    query = (
        select(FeedbackRow)
        .options(joinedload(FeedbackRow.user, innerjoin=True).options(*shared.stores.utils.eager_load_user_options()))
        .order_by(FeedbackRow.id.desc())
        .offset(page.offset)
        .limit(page.limit)
    )
    feedback = (await db.execute(query)).scalars().all()
    return AdminResponsePage(total=total, data=feedback)
