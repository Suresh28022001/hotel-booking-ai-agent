"""
Agent Tools — callable functions the agent can invoke.

Search strategy:
  1. Try DB first (fast, free)
  2. If DB returns 0 results → fetch from internet (free APIs)
  3. Save internet results into DB so future searches are instant
"""
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Hotel, Booking, BookingStatus
from app.schemas.schemas import HotelOut, BookingOut, BookingIntent
from app.core.logging import logger


# ─────────────────────────────────────────────────────────────────────────────
# CURATED FALLBACK DATA — used when internet APIs are unreachable
# ─────────────────────────────────────────────────────────────────────────────

FALLBACK_HOTELS: dict[str, list[dict]] = {
    "paris": [
        {"name": "Hotel de Crillon", "location": "10 Place de la Concorde", "country": "France", "star_rating": 5, "price_per_night": 950.0, "max_guests": 2, "description": "Legendary palace hotel on Place de la Concorde", "amenities": {"wifi": True, "spa": True, "restaurant": True}},
        {"name": "Hotel Le Marais", "location": "3 Rue de Bretagne", "country": "France", "star_rating": 4, "price_per_night": 220.0, "max_guests": 3, "description": "Boutique hotel in the heart of Le Marais", "amenities": {"wifi": True, "breakfast": True}},
        {"name": "Ibis Paris Centre", "location": "15 Rue Serpente", "country": "France", "star_rating": 3, "price_per_night": 110.0, "max_guests": 4, "description": "Comfortable budget hotel near Notre Dame", "amenities": {"wifi": True, "bar": True}},
    ],
    "london": [
        {"name": "The Savoy London", "location": "Strand, London", "country": "UK", "star_rating": 5, "price_per_night": 800.0, "max_guests": 2, "description": "Iconic luxury hotel on the Thames", "amenities": {"wifi": True, "spa": True, "pool": True}},
        {"name": "Citizen M Tower of London", "location": "40 Trinity Square", "country": "UK", "star_rating": 4, "price_per_night": 180.0, "max_guests": 2, "description": "Modern hotel near Tower of London", "amenities": {"wifi": True, "gym": True}},
        {"name": "Premier Inn London Bridge", "location": "Southwark Bridge Road", "country": "UK", "star_rating": 3, "price_per_night": 95.0, "max_guests": 4, "description": "Reliable budget hotel near Borough Market", "amenities": {"wifi": True, "breakfast": True}},
    ],
    "new york": [
        {"name": "The Plaza Hotel NYC", "location": "768 Fifth Avenue", "country": "USA", "star_rating": 5, "price_per_night": 1100.0, "max_guests": 2, "description": "Iconic hotel overlooking Central Park", "amenities": {"wifi": True, "spa": True, "restaurant": True}},
        {"name": "The Standard High Line", "location": "848 Washington St", "country": "USA", "star_rating": 4, "price_per_night": 320.0, "max_guests": 2, "description": "Trendy hotel straddling the High Line", "amenities": {"wifi": True, "pool": True, "bar": True}},
        {"name": "Pod 51 Hotel", "location": "230 E 51st St", "country": "USA", "star_rating": 3, "price_per_night": 150.0, "max_guests": 2, "description": "Compact smart hotel in Midtown Manhattan", "amenities": {"wifi": True, "rooftop": True}},
    ],
    "tokyo": [
        {"name": "The Peninsula Tokyo", "location": "1-8-1 Yurakucho", "country": "Japan", "star_rating": 5, "price_per_night": 750.0, "max_guests": 2, "description": "Luxury hotel with views of the Imperial Palace", "amenities": {"wifi": True, "spa": True, "pool": True}},
        {"name": "Andaz Tokyo Toranomon Hills", "location": "1-23-4 Toranomon", "country": "Japan", "star_rating": 5, "price_per_night": 480.0, "max_guests": 2, "description": "Modern hotel with rooftop bar panoramic views", "amenities": {"wifi": True, "bar": True, "gym": True}},
        {"name": "Dormy Inn Akihabara", "location": "3-2-3 Kandasakumacho", "country": "Japan", "star_rating": 3, "price_per_night": 90.0, "max_guests": 2, "description": "Japanese business hotel with onsen bath", "amenities": {"wifi": True, "onsen": True}},
    ],
    "dubai": [
        {"name": "Burj Al Arab Jumeirah", "location": "Jumeirah Beach Road", "country": "UAE", "star_rating": 5, "price_per_night": 2500.0, "max_guests": 2, "description": "The world's most luxurious hotel shaped like a sail", "amenities": {"wifi": True, "pool": True, "spa": True, "butler": True}},
        {"name": "JW Marriott Marquis Dubai", "location": "Sheikh Zayed Road", "country": "UAE", "star_rating": 5, "price_per_night": 350.0, "max_guests": 4, "description": "Twin tower business hotel in downtown Dubai", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "Rove Downtown Dubai", "location": "Al Asayel Street", "country": "UAE", "star_rating": 3, "price_per_night": 120.0, "max_guests": 4, "description": "Modern budget hotel near Dubai Mall", "amenities": {"wifi": True, "pool": True}},
    ],
    "bali": [
        {"name": "Four Seasons Resort Bali Sayan", "location": "Sayan, Ubud", "country": "Indonesia", "star_rating": 5, "price_per_night": 900.0, "max_guests": 2, "description": "Stunning resort above the Ayung River valley", "amenities": {"wifi": True, "pool": True, "spa": True, "yoga": True}},
        {"name": "Alaya Resort Ubud", "location": "Jalan Hanoman, Ubud", "country": "Indonesia", "star_rating": 4, "price_per_night": 200.0, "max_guests": 3, "description": "Boutique resort in the cultural heart of Ubud", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "The Layar Seminyak", "location": "Seminyak", "country": "Indonesia", "star_rating": 4, "price_per_night": 280.0, "max_guests": 4, "description": "Private villa resort steps from the beach", "amenities": {"wifi": True, "pool": True, "beach": True}},
    ],
    "singapore": [
        {"name": "Marina Bay Sands", "location": "10 Bayfront Avenue", "country": "Singapore", "star_rating": 5, "price_per_night": 500.0, "max_guests": 2, "description": "Iconic hotel with infinity pool on the roof", "amenities": {"wifi": True, "pool": True, "casino": True, "spa": True}},
        {"name": "Raffles Hotel Singapore", "location": "1 Beach Road", "country": "Singapore", "star_rating": 5, "price_per_night": 700.0, "max_guests": 2, "description": "Colonial landmark, home of the Singapore Sling", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "Ibis Singapore Bencoolen", "location": "170 Bencoolen Street", "country": "Singapore", "star_rating": 3, "price_per_night": 120.0, "max_guests": 4, "description": "Budget hotel in the city centre", "amenities": {"wifi": True, "gym": True}},
    ],
    "mumbai": [
        {"name": "The Taj Mahal Palace Mumbai", "location": "Apollo Bunder, Colaba", "country": "India", "star_rating": 5, "price_per_night": 400.0, "max_guests": 2, "description": "Iconic heritage hotel overlooking Gateway of India", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "ITC Grand Central Mumbai", "location": "287 Dr Ambedkar Road", "country": "India", "star_rating": 5, "price_per_night": 250.0, "max_guests": 4, "description": "Luxury business hotel in Parel", "amenities": {"wifi": True, "pool": True, "gym": True}},
        {"name": "Residency Hotel Fort", "location": "26 Rustom Sidhwa Marg", "country": "India", "star_rating": 3, "price_per_night": 65.0, "max_guests": 4, "description": "Heritage budget hotel in the Fort district", "amenities": {"wifi": True, "restaurant": True}},
    ],
    "bangkok": [
        {"name": "Mandarin Oriental Bangkok", "location": "48 Oriental Avenue", "country": "Thailand", "star_rating": 5, "price_per_night": 500.0, "max_guests": 2, "description": "Legendary riverside hotel since 1876", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "The Okura Prestige Bangkok", "location": "Park Ventures Ecoplex", "country": "Thailand", "star_rating": 5, "price_per_night": 280.0, "max_guests": 2, "description": "Japanese luxury hotel with sky pool", "amenities": {"wifi": True, "pool": True, "gym": True}},
        {"name": "Ibis Bangkok Riverside", "location": "27 Charoen Nakhon Road", "country": "Thailand", "star_rating": 3, "price_per_night": 65.0, "max_guests": 4, "description": "Budget hotel along the Chao Phraya River", "amenities": {"wifi": True, "pool": True}},
    ],
    "rome": [
        {"name": "Hotel de Russie Rome", "location": "Via del Babuino 9", "country": "Italy", "star_rating": 5, "price_per_night": 700.0, "max_guests": 2, "description": "Luxury hotel steps from the Spanish Steps", "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": "Hotel Artemide Rome", "location": "Via Nazionale 22", "country": "Italy", "star_rating": 4, "price_per_night": 180.0, "max_guests": 3, "description": "Classic hotel near Termini Station", "amenities": {"wifi": True, "spa": True, "gym": True}},
        {"name": "Hotel Quirinale", "location": "Via Nazionale 7", "country": "Italy", "star_rating": 4, "price_per_night": 140.0, "max_guests": 4, "description": "Historic hotel in the city centre", "amenities": {"wifi": True, "restaurant": True}},
    ],
}

OPENTRIPMAP_API_KEY = "5ae2e3f221c38a28845f05b676e56c9c12f3f7f4bdde04861ecf1b9e"


async def _fetch_hotels_from_internet(city: str) -> list[dict]:
    """
    Fetch real hotel data from the internet.
    Strategy: OpenTripMap (free) → curated fallback → generic fallback
    """
    city_lower = city.lower().strip()

    # Try OpenTripMap
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            geo_resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "format": "json", "limit": 1},
                headers={"User-Agent": "HotelBookingAgent/1.0"},
            )
            geo_data = geo_resp.json()
            if not geo_data:
                raise ValueError(f"City geocode failed: {city}")

            lat = float(geo_data[0]["lat"])
            lon = float(geo_data[0]["lon"])
            display_name = geo_data[0].get("display_name", city)
            # Extract country from display_name (last part)
            country = display_name.split(",")[-1].strip() if "," in display_name else city.title()

            hotels_resp = await client.get(
                "https://api.opentripmap.com/0.1/en/places/radius",
                params={
                    "radius": 5000,
                    "lon": lon,
                    "lat": lat,
                    "kinds": "accomodations",
                    "limit": 10,
                    "format": "json",
                    "apikey": OPENTRIPMAP_API_KEY,
                },
            )
            places = hotels_resp.json()

            if not isinstance(places, list) or len(places) == 0:
                raise ValueError("No hotels from OpenTripMap")

            hotels = []
            for i, place in enumerate(places[:6]):
                name = place.get("name", "").strip()
                if not name or len(name) < 3:
                    continue
                star = max(2, min(5, 5 - (i // 2)))
                price_map = {5: 450.0, 4: 220.0, 3: 120.0, 2: 70.0}
                price = round(price_map[star] + (i * 12), 2)
                addr = place.get("address", {})
                location = addr.get("road", addr.get("suburb", f"City Centre, {city}"))

                hotels.append({
                    "name": name, "location": location, "country": country,
                    "star_rating": star, "price_per_night": price, "max_guests": 4,
                    "description": f"Hotel in {city.title()}, conveniently located near city attractions.",
                    "amenities": {"wifi": True, **({"pool": True, "spa": True} if star == 5 else {"gym": True} if star == 4 else {})},
                })

            if hotels:
                logger.info("OpenTripMap fetch OK", city=city, count=len(hotels))
                return hotels

    except Exception as e:
        logger.warning("OpenTripMap failed", city=city, error=str(e))

    # Curated fallback
    for key, hotel_list in FALLBACK_HOTELS.items():
        if key in city_lower or city_lower in key:
            logger.info("Using curated fallback", city=city, key=key)
            return hotel_list

    # Generic fallback for unknown city
    logger.warning("Generating generic hotels for unknown city", city=city)
    return [
        {"name": f"{city.title()} Grand Hotel", "location": f"City Centre, {city.title()}", "country": city.title(),
         "star_rating": 5, "price_per_night": 350.0, "max_guests": 2,
         "description": f"Premium 5-star hotel in the heart of {city.title()}",
         "amenities": {"wifi": True, "pool": True, "spa": True}},
        {"name": f"{city.title()} Plaza Hotel", "location": f"Business District, {city.title()}", "country": city.title(),
         "star_rating": 4, "price_per_night": 180.0, "max_guests": 4,
         "description": f"Modern 4-star hotel in {city.title()}",
         "amenities": {"wifi": True, "gym": True, "restaurant": True}},
        {"name": f"{city.title()} Budget Inn", "location": f"Old Town, {city.title()}", "country": city.title(),
         "star_rating": 3, "price_per_night": 80.0, "max_guests": 4,
         "description": f"Affordable 3-star stay in {city.title()}",
         "amenities": {"wifi": True, "breakfast": True}},
    ]


async def _seed_hotels_to_db(city: str, hotels_data: list[dict], db: AsyncSession) -> list[Hotel]:
    """Insert fetched hotels into DB, skipping duplicates."""
    inserted = []
    for h in hotels_data:
        existing = await db.execute(
            select(Hotel).where(Hotel.name == h["name"], Hotel.city.ilike(city))
        )
        if existing.scalar_one_or_none():
            continue
        hotel = Hotel(
            name=h["name"],
            location=h.get("location", city),
            city=city.title(),
            country=h.get("country", city.title()),
            description=h.get("description", ""),
            star_rating=h.get("star_rating", 3),
            price_per_night=h.get("price_per_night", 100.0),
            max_guests=h.get("max_guests", 4),
            amenities=h.get("amenities", {}),
            image_url=h.get("image_url"),
            is_available=True,
        )
        db.add(hotel)
        inserted.append(hotel)

    if inserted:
        await db.flush()
        for hotel in inserted:
            await db.refresh(hotel)
        logger.info("Seeded hotels into DB", city=city, count=len(inserted))

    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: SEARCH HOTELS  (DB-first → internet fallback)
# ─────────────────────────────────────────────────────────────────────────────

async def tool_search_hotels(intent: BookingIntent, db: AsyncSession) -> list[HotelOut]:
    """
    1. Query DB with all filters
    2. If 0 results + city provided → fetch internet → seed DB → re-query
    3. If re-query still 0 (filters too strict) → return all seeded for city
    """
    def build_query(apply_filters: bool):
        q = select(Hotel).where(Hotel.is_available == True)
        if intent.city:
            q = q.where(Hotel.city.ilike(f"%{intent.city}%"))
        if apply_filters:
            if intent.budget_min is not None:
                q = q.where(Hotel.price_per_night >= intent.budget_min)
            if intent.budget_max is not None:
                q = q.where(Hotel.price_per_night <= intent.budget_max)
            if intent.star_rating:
                q = q.where(Hotel.star_rating >= intent.star_rating)
            if intent.guests:
                q = q.where(Hotel.max_guests >= intent.guests)
        return q.limit(6)

    result = await db.execute(build_query(apply_filters=True))
    hotels = result.scalars().all()
    logger.info("Hotel DB search", city=intent.city, count=len(hotels))

    if len(hotels) == 0 and intent.city:
        logger.info("DB empty for city — fetching from internet", city=intent.city)
        internet_data = await _fetch_hotels_from_internet(intent.city)
        await _seed_hotels_to_db(intent.city, internet_data, db)
        await db.commit()

        # Re-query with filters
        result2 = await db.execute(build_query(apply_filters=True))
        hotels = result2.scalars().all()

        # If still empty (filters too tight), return all for city
        if not hotels:
            result3 = await db.execute(build_query(apply_filters=False))
            hotels = result3.scalars().all()

    return [HotelOut.model_validate(h) for h in hotels]


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: BOOK HOTEL
# ─────────────────────────────────────────────────────────────────────────────

async def tool_book_hotel(
    user_id: int, hotel_id: int, intent: BookingIntent, db: AsyncSession
) -> Optional[BookingOut]:
    result = await db.execute(
        select(Hotel).where(Hotel.id == hotel_id, Hotel.is_available == True)
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        logger.warning("Hotel not found or unavailable", hotel_id=hotel_id)
        return None

    try:
        check_in = datetime.strptime(intent.check_in, "%Y-%m-%d")
        check_out = datetime.strptime(intent.check_out, "%Y-%m-%d")
    except (TypeError, ValueError) as e:
        logger.error("Invalid booking dates", error=str(e))
        return None

    nights = (check_out - check_in).days
    if nights <= 0:
        return None

    booking = Booking(
        user_id=user_id, hotel_id=hotel_id,
        check_in=check_in, check_out=check_out,
        guests=intent.guests or 1,
        total_price=round(hotel.price_per_night * nights, 2),
        status=BookingStatus.CONFIRMED,
        special_requests=intent.special_requests,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    logger.info("Booking created", booking_id=booking.id, hotel=hotel.name)
    booking.hotel = hotel
    return BookingOut.model_validate(booking)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: GET BOOKINGS
# ─────────────────────────────────────────────────────────────────────────────

async def tool_get_bookings(user_id: int, db: AsyncSession) -> list[BookingOut]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.hotel))
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return [BookingOut.model_validate(b) for b in result.scalars().all()]


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: CANCEL BOOKING
# ─────────────────────────────────────────────────────────────────────────────

async def tool_cancel_booking(booking_id: int, user_id: int, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == user_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        return False
    booking.status = BookingStatus.CANCELLED
    return True