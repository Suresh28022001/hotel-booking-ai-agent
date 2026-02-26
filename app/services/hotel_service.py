from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.models import Hotel
from app.schemas.schemas import HotelSearch, HotelOut


async def list_hotels(search: HotelSearch, db: AsyncSession) -> list[HotelOut]:
    query = select(Hotel).where(Hotel.is_available == True)

    if search.city:
        query = query.where(Hotel.city.ilike(f"%{search.city}%"))
    if search.min_price is not None:
        query = query.where(Hotel.price_per_night >= search.min_price)
    if search.max_price is not None:
        query = query.where(Hotel.price_per_night <= search.max_price)
    if search.min_stars:
        query = query.where(Hotel.star_rating >= search.min_stars)
    if search.guests:
        query = query.where(Hotel.max_guests >= search.guests)

    result = await db.execute(query.limit(20))
    return [HotelOut.model_validate(h) for h in result.scalars().all()]


async def get_hotel(hotel_id: int, db: AsyncSession) -> HotelOut:
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return HotelOut.model_validate(hotel)
