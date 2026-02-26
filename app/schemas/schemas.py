from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from app.models.models import BookingStatus


# ─── Auth ────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Hotel ───────────────────────────────────────────────────────────────────
class HotelOut(BaseModel):
    id: int
    name: str
    location: str
    city: str
    country: str
    description: str
    star_rating: int
    price_per_night: float
    max_guests: int
    amenities: Optional[dict] = None
    image_url: Optional[str] = None
    is_available: bool

    model_config = {"from_attributes": True}


class HotelSearch(BaseModel):
    city: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    guests: Optional[int] = 1
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_stars: Optional[int] = None
    amenities: Optional[List[str]] = None


# ─── Booking ─────────────────────────────────────────────────────────────────
class BookingCreate(BaseModel):
    hotel_id: int
    check_in: datetime
    check_out: datetime
    guests: int = Field(..., ge=1)
    special_requests: Optional[str] = None

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v, info):
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out must be after check_in")
        return v


class BookingOut(BaseModel):
    id: int
    user_id: int
    hotel_id: int
    check_in: datetime
    check_out: datetime
    guests: int
    total_price: float
    status: BookingStatus
    special_requests: Optional[str] = None
    created_at: datetime
    hotel: Optional[HotelOut] = None

    model_config = {"from_attributes": True}


# ─── Agent / Chat ─────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    suggested_hotels: Optional[List[HotelOut]] = None
    booking_initiated: bool = False
    booking: Optional[BookingOut] = None


# ─── Agent Internal Schemas ───────────────────────────────────────────────────
class BookingIntent(BaseModel):
    city: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    guests: Optional[int] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    star_rating: Optional[int] = None
    amenities: Optional[List[str]] = None
    special_requests: Optional[str] = None
    confirm_hotel_id: Optional[int] = None
    action: Optional[str] = None  # search | book | cancel | status | clarify
