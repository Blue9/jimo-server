from app.models import models


def user_can_view_post(user: models.User, post: models.Post) -> bool:
    """Return whether the user is authorized to view the given post or not."""
    return not post.user.private_account or post.user in user.following
