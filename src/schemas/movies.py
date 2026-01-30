from datetime import date, datetime, timedelta
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


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
    country: str = Field(min_length=1, max_length=3)  # Country code (e.g., "US")
    genres: list[str] = Field(min_length=1)  # Genre names
    actors: list[str] = Field(min_length=1)  # Actor names
    languages: list[str] = Field(min_length=1)  # Language names

    @field_validator("date")
    @classmethod
    def validate_date_not_too_far_future(cls, chek_data: date) -> date:
        """Validate that date is not more than 1 year in the future"""

        max_future_date = datetime.now().date() + timedelta(days=365)
        if chek_data > max_future_date:
            raise ValueError("Date cannot be more than one year in the future")
        return chek_data


class MovieUpdateSchema(BaseModel):
    """Schema for updating a movie (all fields optional)"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = Field(None, min_length=1)
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)


class MovieListResponseSchema(BaseModel):
    """Schema for paginated list of movies"""

    movies: list[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int = Field(ge=0)
    total_items: int = Field(ge=0)


class MessageResponseSchema(BaseModel):
    """Generic message response"""
    detail: str
