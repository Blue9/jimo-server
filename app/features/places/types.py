from app.core.types import Base
from app.features.places.entities import Place
from app.features.posts.entities import Post


class GetPlaceResponse(Base):
    place: Place
    community_posts: list[Post]
    following_posts: list[Post]
