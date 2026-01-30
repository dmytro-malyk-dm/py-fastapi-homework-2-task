from datetime import date
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class MovieStatusEnum(str, Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


class GenreSchema(BaseModel):
    """Schema for Genre entity"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ActorSchema(BaseModel):
    """Schema for Actor entity"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CountrySchema(BaseModel):
    """Schema for Country entity"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: Optional[str] = None


class LanguageSchema(BaseModel):
    """Schema for Language entity"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MovieListItemSchema(BaseModel):
    """Schema for movie in list (without relationships)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float


class MovieDetailSchema(BaseModel):
    """Schema for detailed movie view (with all relationships)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountrySchema
    genres: list[GenreSchema]
    actors: list[ActorSchema]
    languages: list[LanguageSchema]


class MovieCreateSchema(BaseModel):
    """Schema for creating a new movie"""

    name: str = Field(min_length=1, max_length=255)
    date: date
    score: float = Field(ge=0, le=100)
    overview: str = Field(min_length=1)
    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country_id: int = Field(gt=0)
    genre_ids: list[int] = Field(min_length=1)
    actor_ids: list[int] = Field(min_length=1)
    language_ids: list[int] = Field(min_length=1)


class MovieUpdateSchema(BaseModel):
    """Schema for updating a movie (all fields optional)"""

    name: Optional[str] = Field(min_length=1, max_length=255)
    date: Optional[date]
    score: Optional[float] = Field(ge=0, le=100)
    overview: Optional[str] = Field(min_length=1)
    status: Optional[MovieStatusEnum]
    budget: Optional[float] = Field(ge=0)
    revenue: Optional[float] = Field(ge=0)


class MovieListResponseSchema(BaseModel):
    """Schema for paginated list of movies"""

    movies: list[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int = Field(ge=0)
    total_items: int = Field(ge=0)


class MessageResponseSchema(BaseModel):
    """Generic message response"""
    detail: str
