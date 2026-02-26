from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.models.models import Booking, Hotel, BookingStatus
from app.schemas.schemas import BookingCreate, BookingOut


async def create_booking(user_id: int, data: BookingCreate, db: AsyncSession) -> BookingOut:
    result = await db.execute(select(Hotel).where(Hotel.id == data.hotel_id, Hotel.is_available == True))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found or unavailable")

    nights = (data.check_out - data.check_in).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="Check-out must be after check-in")

    booking = Booking(
        user_id=user_id,
        hotel_id=hotel.id,
        check_in=data.check_in,
        check_out=data.check_out,
        guests=data.guests,
        total_price=hotel.price_per_night * nights,
        status=BookingStatus.CONFIRMED,
        special_requests=data.special_requests,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    booking.hotel = hotel
    return BookingOut.model_validate(booking)


async def get_user_bookings(user_id: int, db: AsyncSession) -> list[BookingOut]:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.hotel))
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return [BookingOut.model_validate(b) for b in result.scalars().all()]


async def cancel_booking(booking_id: int, user_id: int, db: AsyncSession) -> BookingOut:
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.hotel))
        .where(Booking.id == booking_id, Booking.user_id == user_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking already cancelled")
    booking.status = BookingStatus.CANCELLED
    return BookingOut.model_validate(booking)
