"""Basic admin endpoints."""
import uuid
from collections import namedtuple
from typing import Optional

from app.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import true, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()

Page = namedtuple("Page", ["offset", "limit"])


def get_admin_or_raise(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
) -> schemas.internal.InternalUser:
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, uid=firebase_user.uid)
    if not user.is_admin:
        raise HTTPException(403)
    return user


def get_page(page: int = Query(1, gt=0), limit: int = Query(100, gt=0, le=1000)) -> Page:
    return Page(offset=(page - 1) * limit, limit=limit)


# User endpoints
@router.get("/users", response_model=schemas.admin.Page[schemas.admin.User])
def get_users(
    page: Page = Depends(get_page), db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all users."""
    total = db.query(models.User).count()
    data = db.query(models.User) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=data)


@router.post("/users", response_model=schemas.admin.User)
def create_user(
    request: schemas.admin.CreateUserRequest,
    user_store: UserStore = Depends(UserStore),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise),
):
    """Create a user."""
    created_user, error = user_store.create_user(request.uid, request.username, request.first_name, request.last_name)
    if created_user:
        return created_user
    elif error:
        raise HTTPException(400, error.json())
    else:
        raise HTTPException(500)


@router.get("/users/{username}", response_model=schemas.admin.User)
def get_user(
    username: str,
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get the given user."""
    user = db.query(models.User).filter(models.User.username_lower == username.lower()).first()
    if user is None:
        raise HTTPException(404)
    return user


@router.post("/users/{username}", response_model=schemas.admin.User)
def update_user(
    username: str,
    request: schemas.admin.UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Update the given user."""
    to_update: Optional[models.User] = db.query(models.User) \
        .filter(models.User.username_lower == username.lower()) \
        .first()
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
        db.commit()
    except IntegrityError:
        raise HTTPException(400)
    return to_update


@router.get("/admins", response_model=schemas.admin.Page[schemas.admin.User])
def get_admins(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all admin users."""
    total = db.query(models.User).filter(models.User.is_admin == true()).count()
    admins = db.query(models.User) \
        .filter(models.User.is_admin == true()) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=admins)


# Featured users
@router.get("/featuredUsers", response_model=schemas.admin.Page[schemas.admin.User])
def get_featured_users(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get featured users."""
    total = db.query(models.User).filter(models.User.is_featured == true()).count()
    featured_users = db.query(models.User) \
        .filter(models.User.is_featured == true()) \
        .order_by(models.User.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=featured_users)


# Posts
@router.get("/posts", response_model=schemas.admin.Page[schemas.admin.Post])
def get_all_posts(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all posts."""
    total = db.query(models.Post).count()
    posts = db.query(models.Post) \
        .order_by(models.Post.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=posts)


@router.get("/posts/{post_id}", response_model=schemas.admin.Post)
def get_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    post = db.query(models.Post) \
        .filter(models.Post.id == post_id) \
        .first()
    if post is None:
        raise HTTPException(404)
    return post


@router.post("/posts/{post_id}", response_model=schemas.admin.Post)
def update_post(
    post_id: uuid.UUID,
    request: schemas.admin.UpdatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    post: Optional[models.Post] = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post is None:
        raise HTTPException(404)
    if request.content:
        post.content = request.content
    if request.deleted is not None:
        post.deleted = request.deleted
    db.commit()
    if post.image is not None:
        if post.deleted:
            firebase_user.shared_firebase.make_image_private(post.image.firebase_blob_name)
        else:
            firebase_user.shared_firebase.make_image_public(post.image.firebase_blob_name)
    return post


# Waitlist
@router.get("/waitlist", response_model=schemas.admin.Page[schemas.admin.Waitlist])
def get_waitlist(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all users on the waitlist that haven't been invited yet."""
    total = db.query(models.Waitlist) \
        .filter(~exists().where(models.Waitlist.phone_number == models.Invite.phone_number)) \
        .count()
    waitlist = db.query(models.Waitlist) \
        .filter(~exists().where(models.Waitlist.phone_number == models.Invite.phone_number)) \
        .order_by(models.Waitlist.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=waitlist)


# Invites
@router.get("/invites", response_model=schemas.admin.Page[schemas.admin.Invite])
def get_all_invites(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get invited phone numbers that haven't signed up yet."""
    total = db.query(models.Invite) \
        .filter(~exists().where(models.Invite.phone_number == models.User.phone_number)) \
        .count()
    invites = db.query(models.Invite) \
        .filter(~exists().where(models.Invite.phone_number == models.User.phone_number)) \
        .order_by(models.Invite.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=invites)


@router.post("/invites", response_model=schemas.admin.Invite)
def create_invite(
    request: schemas.admin.CreateInviteRequest,
    db: Session = Depends(get_db),
    admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Create invite."""
    invite = models.Invite(phone_number=request.phone_number, invited_by=admin.id)
    try:
        db.add(invite)
        db.commit()
        return invite
    except IntegrityError:
        raise HTTPException(400, "Phone number exists")


@router.delete("/invites", response_model=list[schemas.admin.Invite])
def remove_invites(
    request: schemas.user.PhoneNumberList,
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Remove invites."""
    to_delete = db.query(models.Invite).filter(models.Invite.phone_number.in_(request.phone_numbers)).all()
    for invite in to_delete:
        db.delete(invite)
    db.commit()
    return to_delete


# Reports + Feedback
@router.get("/reports", response_model=schemas.admin.Page[schemas.admin.Report])
def get_post_reports(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all post reports."""
    total = db.query(models.PostReport).count()
    reports = db.query(models.PostReport) \
        .order_by(models.PostReport.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=reports)


@router.get("/feedback", response_model=schemas.admin.Page[schemas.admin.Feedback])
def get_feedback(
    page: Page = Depends(get_page),
    db: Session = Depends(get_db),
    _admin: schemas.internal.InternalUser = Depends(get_admin_or_raise)
):
    """Get all submitted feedback."""
    total = db.query(models.Feedback).count()
    feedback = db.query(models.Feedback) \
        .order_by(models.Feedback.id.desc()) \
        .offset(page.offset) \
        .limit(page.limit) \
        .all()
    return schemas.admin.Page(total=total, data=feedback)
