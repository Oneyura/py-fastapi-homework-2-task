from pydantic import BaseModel, Field, conlist, condecimal, constr, ConfigDict
from typing import List, Optional
from datetime import date

from src.database.models import MovieStatusEnum


class CountrySchema(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class GenreSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class ActorSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class LanguageSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(BaseModel):
    name: str
    date: date
    score: float = Field(..., ge=0.0, le=100.0)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0.0)
    revenue: float = Field(..., ge=0.0)
    country: constr(min_length=2, max_length=2)
    genres: List[str]
    actors: List[str]
    languages: List[str]


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0.0)
    revenue: Optional[float] = Field(None, ge=0.0)
    country: Optional[constr(min_length=2, max_length=2)] = None
    genres: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    languages: Optional[List[str]] = None


class MovieCreateResponseSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieUpdateResponseSchema(BaseModel):
    detail: str
