"""
Seed script — populates the database with sample hotels.
Run: python scripts/seed_hotels.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import AsyncSessionLocal, create_tables
from app.models.models import Hotel

SAMPLE_HOTELS = [
    {
        "name": "The Grand Palace",
        "location": "123 Fifth Avenue, Manhattan",
        "city": "New York",
        "country": "USA",
        "description": "A luxurious 5-star hotel in the heart of Manhattan with stunning skyline views.",
        "star_rating": 5,
        "price_per_night": 450.00,
        "max_guests": 4,
        "amenities": {"wifi": True, "pool": True, "gym": True, "spa": True, "parking": True, "restaurant": True},
        "image_url": "https://example.com/grand-palace.jpg",
    },
    {
        "name": "Brooklyn Boutique Inn",
        "location": "456 Bedford Avenue, Williamsburg",
        "city": "New York",
        "country": "USA",
        "description": "Charming boutique hotel in trendy Williamsburg with artisan coffee shop.",
        "star_rating": 3,
        "price_per_night": 150.00,
        "max_guests": 2,
        "amenities": {"wifi": True, "gym": False, "parking": False, "restaurant": True},
        "image_url": "https://example.com/brooklyn-inn.jpg",
    },
    {
        "name": "Sunset Beach Resort",
        "location": "1 Ocean Drive",
        "city": "Miami",
        "country": "USA",
        "description": "Beachfront resort with private beach access, two pools, and world-class dining.",
        "star_rating": 5,
        "price_per_night": 380.00,
        "max_guests": 6,
        "amenities": {"wifi": True, "pool": True, "gym": True, "spa": True, "parking": True, "beach": True},
        "image_url": "https://example.com/sunset-resort.jpg",
    },
    {
        "name": "Miami Budget Stay",
        "location": "200 Collins Avenue",
        "city": "Miami",
        "country": "USA",
        "description": "Comfortable and affordable hotel just 2 blocks from the beach.",
        "star_rating": 2,
        "price_per_night": 75.00,
        "max_guests": 2,
        "amenities": {"wifi": True, "pool": True, "parking": True},
        "image_url": "https://example.com/miami-budget.jpg",
    },
    {
        "name": "Hollywood Hills Hotel",
        "location": "9876 Sunset Blvd",
        "city": "Los Angeles",
        "country": "USA",
        "description": "Celebrity favorite with panoramic views of the Hollywood Hills and city lights.",
        "star_rating": 4,
        "price_per_night": 320.00,
        "max_guests": 3,
        "amenities": {"wifi": True, "pool": True, "gym": True, "spa": True, "valet": True},
        "image_url": "https://example.com/hollywood-hills.jpg",
    },
    {
        "name": "Santa Monica Surfer's Lodge",
        "location": "5 Palisades Beach Road",
        "city": "Los Angeles",
        "country": "USA",
        "description": "Laid-back lodging steps from the beach and Santa Monica Pier.",
        "star_rating": 3,
        "price_per_night": 180.00,
        "max_guests": 4,
        "amenities": {"wifi": True, "pool": False, "gym": True, "surfboard_rental": True},
        "image_url": "https://example.com/surfers-lodge.jpg",
    },
    {
        "name": "The Windy City Suites",
        "location": "100 N Michigan Avenue",
        "city": "Chicago",
        "country": "USA",
        "description": "Executive suites in the Magnificent Mile with stunning lake views.",
        "star_rating": 4,
        "price_per_night": 260.00,
        "max_guests": 2,
        "amenities": {"wifi": True, "gym": True, "business_center": True, "restaurant": True},
        "image_url": "https://example.com/windy-city.jpg",
    },
    {
        "name": "Vegas Dream Casino Resort",
        "location": "3000 Las Vegas Boulevard",
        "city": "Las Vegas",
        "country": "USA",
        "description": "Vegas entertainment at its finest with casino, shows, and 5 restaurants.",
        "star_rating": 5,
        "price_per_night": 299.00,
        "max_guests": 4,
        "amenities": {"wifi": True, "pool": True, "gym": True, "casino": True, "spa": True, "shows": True},
        "image_url": "https://example.com/vegas-dream.jpg",
    },
    {
        "name": "Desert Sands Motel",
        "location": "1200 Fremont Street",
        "city": "Las Vegas",
        "country": "USA",
        "description": "Clean, affordable rooms in downtown Las Vegas — perfect for budget travelers.",
        "star_rating": 2,
        "price_per_night": 55.00,
        "max_guests": 2,
        "amenities": {"wifi": True, "pool": True, "parking": True},
        "image_url": "https://example.com/desert-sands.jpg",
    },
    {
        "name": "Seattle Space View Hotel",
        "location": "400 Broad Street",
        "city": "Seattle",
        "country": "USA",
        "description": "Modern hotel near Space Needle with Pacific Northwest-inspired decor.",
        "star_rating": 4,
        "price_per_night": 210.00,
        "max_guests": 3,
        "amenities": {"wifi": True, "gym": True, "restaurant": True, "rooftop_bar": True},
        "image_url": "https://example.com/seattle-space.jpg",
    },
]


async def seed():
    await create_tables()
    async with AsyncSessionLocal() as session:
        for data in SAMPLE_HOTELS:
            hotel = Hotel(**data)
            session.add(hotel)
        await session.commit()
        print(f"✅ Seeded {len(SAMPLE_HOTELS)} hotels successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
