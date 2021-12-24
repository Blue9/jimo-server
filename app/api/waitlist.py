from app.api.utils import get_user_store, get_invite_store
from shared.stores.invite_store import InviteStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException

from app import config
from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user

router = APIRouter()


async def get_phone_number(firebase_user: FirebaseUser = Depends(get_firebase_user)) -> str:
    phone_number = await firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        raise HTTPException(403)
    return phone_number


@router.get("/status", response_model=schemas.invite.UserWaitlistStatus)
async def get_waitlist_status(
    phone_number: str = Depends(get_phone_number),
    invite_store: InviteStore = Depends(get_invite_store)
):
    return schemas.invite.UserWaitlistStatus(
        invited=await invite_store.is_invited(phone_number),
        waitlisted=await invite_store.is_on_waitlist(phone_number)
    )


@router.post("", response_model=schemas.invite.UserWaitlistStatus)
async def join_waitlist(
    phone_number: str = Depends(get_phone_number),
    invite_store: InviteStore = Depends(get_invite_store)
):
    await invite_store.join_waitlist(phone_number)
    return schemas.invite.UserWaitlistStatus(invited=False, waitlisted=True)


@router.post("/invites", response_model=schemas.invite.UserInviteStatus)
async def invite_user(
    request: schemas.invite.InviteUserRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    invite_store: InviteStore = Depends(get_invite_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    num_used_invites = await invite_store.num_used_invites(user.id)
    if num_used_invites >= config.INVITES_PER_USER:
        return schemas.invite.UserInviteStatus(invited=False, message="Reached invite limit.")
    return await invite_store.invite_user(invited_by=user.id, phone_number=request.phone_number)
