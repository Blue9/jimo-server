from uuid import UUID
from app.core.types import Base, CursorId
from app.features.places.entities import Place
from app.features.posts.entities import Post


class FindPlaceResponse(Base):
    place: Place | None


class GetPlaceDetailsResponse(Base):
    place: Place
    community_posts: list[Post]
    featured_posts: list[Post]
    following_posts: list[Post]


class SavedPlace(Base):
    id: UUID
    place: Place
    category: str
    note: str


class SavedPlacesResponse(Base):
    saves: list[SavedPlace]
    cursor: CursorId | None = None


class SavePlaceRequest(Base):
    category: str
    note: str
