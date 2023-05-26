from pydantic import root_validator
from app.core.types import Base, CursorId, PlaceId, PostId
from app.features.places.entities import Place, SavedPlace
from app.features.posts.entities import Post
from app.features.posts.types import MaybeCreatePlaceWithMetadataRequest


class FindPlaceResponse(Base):
    place: Place | None


class GetPlaceDetailsResponse(Base):
    # TODO(gautam): paginate/ remove posts when this gets too big
    place: Place
    my_post: Post | None
    my_save: SavedPlace | None
    following_posts: list[Post]
    featured_posts: list[Post]
    community_posts: list[Post]


class SavedPlacesResponse(Base):
    saves: list[SavedPlace]
    cursor: CursorId | None = None


class SavePlaceRequest(Base):
    place: MaybeCreatePlaceWithMetadataRequest | None = None
    place_id: PlaceId | None = None
    post_id: PostId | None = None  # Set if user saves place from a post view
    note: str

    @root_validator
    def validate_place(cls, values):
        assert values.get("place_id") is not None or values.get("place") is not None, "place must be included"
        return values


class SavePlaceResponse(Base):
    save: SavedPlace
    # If the client sent a place creation request we send it back so that the client
    # can update its local state
    create_place_request: MaybeCreatePlaceWithMetadataRequest | None
