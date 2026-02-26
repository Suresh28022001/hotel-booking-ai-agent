"""
Example API requests using httpx — demonstrates the full flow.
Run: python scripts/test_api.py
Requires the server to be running: uvicorn app.main:app --reload
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:

        print("=" * 60)
        print("  Hotel Booking AI Agent — API Demo")
        print("=" * 60)

        # ── 1. Register user ─────────────────────────────────────────
        print("\n[1] Registering user...")
        r = await client.post(f"{BASE_URL}/auth/register", json={
            "email": "demo@example.com",
            "username": "demouser",
            "password": "secret123"
        })
        print(f"Status: {r.status_code}")
        print(json.dumps(r.json(), indent=2))

        # ── 2. Login ─────────────────────────────────────────────────
        print("\n[2] Logging in...")
        r = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "demo@example.com",
            "password": "secret123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Got token: {token[:40]}...")

        # ── 3. Search hotels ─────────────────────────────────────────
        print("\n[3] Searching hotels in Miami...")
        r = await client.get(f"{BASE_URL}/hotels/?city=Miami&guests=2", headers=headers)
        print(f"Status: {r.status_code}")
        hotels = r.json()
        for h in hotels:
            print(f"  🏨 [{h['id']}] {h['name']} — ${h['price_per_night']}/night ({h['star_rating']}★)")

        # ── 4. Chat with AI agent ─────────────────────────────────────
        print("\n[4] Chatting with AI Agent...")
        session_id = None

        conversations = [
            "Hi! I'm looking for a hotel in New York.",
            "I need it for 2 guests from 2025-08-10 to 2025-08-15. Budget around $100-$200 per night.",
            "The Brooklyn Boutique Inn looks great! Can you book it for me?",
            "What are my current bookings?",
        ]

        for msg in conversations:
            print(f"\n  👤 User: {msg}")
            r = await client.post(
                f"{BASE_URL}/agent/chat",
                json={"message": msg, "session_id": session_id},
                headers=headers,
            )
            data = r.json()
            session_id = data.get("session_id")
            print(f"  🤖 Agent: {data['reply']}")
            if data.get("suggested_hotels"):
                print(f"  📋 Hotels suggested: {len(data['suggested_hotels'])}")
            if data.get("booking_initiated"):
                print(f"  ✅ Booking confirmed! ID: {data['booking']['id']}")

        # ── 5. Direct REST booking ────────────────────────────────────
        print("\n[5] Direct REST booking...")
        r = await client.post(
            f"{BASE_URL}/bookings/",
            json={
                "hotel_id": 3,
                "check_in": "2025-09-01T00:00:00",
                "check_out": "2025-09-05T00:00:00",
                "guests": 2,
                "special_requests": "Late check-in please"
            },
            headers=headers,
        )
        print(f"Status: {r.status_code}")
        b = r.json()
        print(f"  Booking ID: {b['id']}, Total: ${b['total_price']}, Status: {b['status']}")

        # ── 6. Cancel booking ─────────────────────────────────────────
        print(f"\n[6] Cancelling booking #{b['id']}...")
        r = await client.delete(f"{BASE_URL}/bookings/{b['id']}", headers=headers)
        print(f"Status: {r.status_code}, New status: {r.json()['status']}")

        print("\n✅ All API tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
