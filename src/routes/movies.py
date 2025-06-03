from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieCreateSchema,
    MovieCreateResponseSchema,
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieUpdateSchema,
    MovieUpdateResponseSchema,
)

router = APIRouter(prefix="/movies")


async def get_or_create_by_field(
    db: AsyncSession, model, field_name: str, value: str
):
    stmt = select(model).where(getattr(model, field_name) == value)
    instance = await db.scalar(stmt)
    if not instance:
        instance = model(**{field_name: value})
        db.add(instance)
        await db.flush()
    return instance


async def process_many_to_many(
    db: AsyncSession, model, field_name: str, values: list[str]
):
    result = []
    for value in values:
        item = await get_or_create_by_field(db, model, field_name, value)
        result.append(item)
    return result


@router.get("/{movie_id}/", response_model=MovieCreateResponseSchema)
async def get_movie_by_id(
    movie_id: int, db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
    movie = await db.scalar(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    return MovieCreateResponseSchema.model_validate(movie)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=MovieCreateResponseSchema,
)
async def create_movie(
    movie_data: MovieCreateSchema, db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
    existing_movie = await db.scalar(
        select(MovieModel)
        .where(MovieModel.name == movie_data.name)
        .where(MovieModel.date == movie_data.date)
    )
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie_data.name}' and release date '{movie_data.date}' already exists.",
        )
    try:
        country = await get_or_create_by_field(
            db, CountryModel, "code", movie_data.country
        )
        genres = await process_many_to_many(
            db, GenreModel, "name", movie_data.genres
        )
        actors = await process_many_to_many(
            db, ActorModel, "name", movie_data.actors
        )
        languages = await process_many_to_many(
            db, LanguageModel, "name", movie_data.languages
        )

        movie = MovieModel(
            name=movie_data.name,
            date=movie_data.date,
            score=movie_data.score,
            overview=movie_data.overview,
            status=movie_data.status,
            budget=movie_data.budget,
            revenue=movie_data.revenue,
            country=country,
            genres=genres,
            actors=actors,
            languages=languages,
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        movie = await db.scalar(
            select(MovieModel)
            .options(
                selectinload(MovieModel.country),
                selectinload(MovieModel.genres),
                selectinload(MovieModel.actors),
                selectinload(MovieModel.languages),
            )
            .where(MovieModel.id == movie.id)
        )
        return MovieCreateResponseSchema.model_validate(movie)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The input data is invalid (e.g., missing required fields, invalid values)",
        )


@router.get("/", response_model=MovieListResponseSchema)
async def list_movies(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=20, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    offset = (page - 1) * per_page
    total_count = await db.scalar(select(func.count()).select_from(MovieModel))
    if total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies found."
        )

    total_pages = (total_count + per_page - 1) // per_page
    if page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No movies found."
        )

    query = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    movies = result.scalars().all()

    base_url = "/theater/movies/"
    prev_page = (
        f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    )
    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return MovieListResponseSchema(
        movies=[MovieListItemSchema.model_validate(movie) for movie in movies],
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_count,
    )


@router.delete("/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.scalar(
        select(MovieModel).where(MovieModel.id == movie_id)
    )
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    await db.delete(movie)
    await db.commit()


@router.patch("/{movie_id}/", response_model=MovieUpdateResponseSchema)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    movie = await db.scalar(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found.",
        )
    try:
        if movie_data.country:
            movie.country = await get_or_create_by_field(
                db, CountryModel, "code", movie_data.country
            )
        if movie_data.genres:
            movie.genres = await process_many_to_many(
                db, GenreModel, "name", movie_data.genres
            )
        if movie_data.actors:
            movie.actors = await process_many_to_many(
                db, ActorModel, "name", movie_data.actors
            )
        if movie_data.languages:
            movie.languages = await process_many_to_many(
                db, LanguageModel, "name", movie_data.languages
            )

        for field in [
            "name",
            "date",
            "score",
            "overview",
            "status",
            "budget",
            "revenue",
        ]:
            value = getattr(movie_data, field)
            if value is not None:
                setattr(movie, field, value)

        await db.commit()
        await db.refresh(movie)
        return MovieUpdateResponseSchema(detail="Movie updated successfully.")

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The input data is invalid (e.g., missing required fields, invalid values)",
        )
