from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    MessageResponseSchema
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies_list(
        page: int = Query(default=1, ge=1, description="Page number (must be >= 1)"),
        per_page: int = Query(default=10, ge=1, le=20, description="Items per page (1-20)"),
        db: AsyncSession = Depends(get_db)
):
    """
    Get a paginated list of movies.

    - **page**: Page number to fetch (default: 1, min: 1)
    - **per_page**: Number of movies per page (default: 10, min: 1, max: 20)

    Returns:
    - List of movies with pagination metadata

    Raises:
    - 404: If no movies found
    - 422: If validation fails (invalid page or per_page)
    """

    count_query = select(func.count(MovieModel.id))
    result = await db.execute(count_query)
    total_items = result.scalar_one()

    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = ceil(total_items / per_page)

    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")

    offset = (page - 1) * per_page

    movies_query = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(movies_query)
    movies = result.scalars().all()

    base_url = "/theater/movies/"
    prev_page = None
    next_page = None

    if page > 1:
        prev_page = f"{base_url}?page={page - 1}&per_page={per_page}"

    if page < total_pages:
        next_page = f"{base_url}?page={page + 1}&per_page={per_page}"

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_by_id(
        movie_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific movie by ID.

    Returns:
    - Detailed movie information with all relationships

    Raises:
    - 404: If movie with the given ID was not found
    """

    query = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )

    result = await db.execute(query)
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return movie


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific movie by ID.

    - **movie_id**: The ID of the movie to delete

    Returns:
    - 204 No Content (success, no response body)

    Raises:
    - 404: If movie with the given ID was not found

    Notes:
    - CASCADE delete will automatically remove relationships in:
      - movies_genres
      - actors_movies
      - movies_languages
    - Genres, actors, and languages themselves are NOT deleted
    """
    query = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(query)
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return None


@router.patch("/movies/{movie_id}/", response_model=MessageResponseSchema)
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db)
):
    """
    Update a specific movie by ID (partial update).

    Only the fields provided in the request body will be updated.
    All fields are optional.

    - **movie_id**: The ID of the movie to update
    - **movie_data**: Fields to update (all optional)

    Returns:
    - 200 OK: {"detail": "Movie updated successfully."}

    Raises:
    - 404: If movie with the given ID was not found
    - 400: If invalid input data (violates constraints)

    Validation:
    - score: 0-100
    - budget, revenue: >= 0
    - name+date: must be unique (UniqueConstraint)
    """

    query = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(query)
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    update_data = movie_data.model_dump(exclude_unset=True)

    if not update_data:
        return MessageResponseSchema(detail="Movie updated successfully.")

    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid input data."
        )

    return MessageResponseSchema(detail="Movie updated successfully.")


@router.post("/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    """
    Create a new movie with relationships.

    Accepts names/codes for related entities and finds or creates them:
    - country: Country code (e.g., "US")
    - genres: List of genre names
    - actors: List of actor names
    - languages: List of language names

    - **movie_data**: Movie data including names/codes for relationships

    Returns:
    - 201 Created: Detailed movie information with all relationships

    Raises:
    - 404: If country code does not exist
    - 409: If movie with same name and date already exists
    - 400: If invalid input data

    Validation:
    - score: 0-100
    - budget, revenue: >= 0
    - date: not more than 1 year in future
    - name+date: must be unique
    """

    country_query = select(CountryModel).where(CountryModel.code == movie_data.country)
    country_result = await db.execute(country_query)
    country = country_result.scalar_one_or_none()

    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with code '{movie_data.country}' not found."
        )

    genres = []
    for genre_name in movie_data.genres:
        genre_query = select(GenreModel).where(GenreModel.name == genre_name)
        genre_result = await db.execute(genre_query)
        genre = genre_result.scalar_one_or_none()

        if genre is None:
            genre = GenreModel(name=genre_name)
            db.add(genre)
            await db.flush()

        genres.append(genre)

    actors = []
    for actor_name in movie_data.actors:
        actor_query = select(ActorModel).where(ActorModel.name == actor_name)
        actor_result = await db.execute(actor_query)
        actor = actor_result.scalar_one_or_none()

        if actor is None:
            actor = ActorModel(name=actor_name)
            db.add(actor)
            await db.flush()

        actors.append(actor)

    languages = []
    for language_name in movie_data.languages:
        language_query = select(LanguageModel).where(LanguageModel.name == language_name)
        language_result = await db.execute(language_query)
        language = language_result.scalar_one_or_none()

        if language is None:
            language = LanguageModel(name=language_name)
            db.add(language)
            await db.flush()

        languages.append(language)

    movie = MovieModel(
        name=movie_data.name,
        date=movie_data.date,
        score=movie_data.score,
        overview=movie_data.overview,
        status=movie_data.status,
        budget=movie_data.budget,
        revenue=movie_data.revenue,
        country_id=country.id
    )

    movie.genres = genres
    movie.actors = actors
    movie.languages = languages

    db.add(movie)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError as e:
        await db.rollback()
        error_message = str(e.orig) if hasattr(e, "orig") else str(e)
        if "unique_movie_constraint" in error_message or "duplicate key" in error_message.lower():
            raise HTTPException(
                status_code=409,
                detail=f"A movie with the name '{movie_data.name}' and "
                f"release date '{movie_data.date}' already exists."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid input data."
            )

    query = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie.id)
    )

    result = await db.execute(query)
    created_movie = result.scalar_one()

    return created_movie
