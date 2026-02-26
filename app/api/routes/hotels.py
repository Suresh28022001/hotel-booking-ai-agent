from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.schemas import HotelOut, HotelSearch
from app.services.hotel_service import list_hotels, get_hotel
from app.core.security import get_current_user_id

router = APIRouter(prefix="/hotels", tags=["Hotels"])


@router.get("/", response_model=list[HotelOut])
async def search_hotels(
    city: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_stars: Optional[int] = Query(None, ge=1, le=5),
    guests: Optional[int] = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    search = HotelSearch(city=city, min_price=min_price, max_price=max_price, min_stars=min_stars, guests=guests)
    return await list_hotels(search, db)


@router.get("/{hotel_id}", response_model=HotelOut)
async def get_hotel_detail(
    hotel_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    return await get_hotel(hotel_id, db)
