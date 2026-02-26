from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.schemas import BookingCreate, BookingOut
from app.services.booking_service import create_booking, get_user_bookings, cancel_booking
from app.core.security import get_current_user_id

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingOut, status_code=201)
async def book_hotel(
    data: BookingCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await create_booking(user_id, data, db)


@router.get("/", response_model=list[BookingOut])
async def my_bookings(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_bookings(user_id, db)


@router.delete("/{booking_id}", response_model=BookingOut)
async def cancel(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await cancel_booking(booking_id, user_id, db)
