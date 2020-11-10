from app.models.models import User, Post


def user_can_view_post(user: User, post: Post) -> bool:
    """Return whether the user is authorized to view the given post or not."""
    return not post.user.private_account or post.user in user.following
