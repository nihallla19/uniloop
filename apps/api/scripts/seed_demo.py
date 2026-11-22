"""Fictional demo data for showing Uniloop. NOT real users or activity.

    uv run python -m scripts.seed_demo          # (re)create demo data
    uv run python -m scripts.seed_demo --remove # delete it

All demo accounts use `demo.*@example.edu`. Refuses to run in production.
"""

import json
import random
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, text

from app.config import get_settings
from app.db import get_engine
from scripts.seed import seed

DEMO_EMAIL_LIKE = "demo.%@example.edu"

STUDENTS = [
    "Aarav Mehta",
    "Diya Sharma",
    "Kabir Rao",
    "Ananya Iyer",
    "Vihaan Nair",
    "Ishita Das",
    "Rohan Kulkarni",
    "Meera Pillai",
    "Arjun Reddy",
    "Saanvi Joshi",
    "Dev Malhotra",
    "Kavya Menon",
    "Nikhil Bose",
    "Tara Fernandes",
    "Aditya Singh",
    "Riya Kapoor",
    "Yash Patil",
    "Neha Agarwal",
    "Siddharth Jain",
    "Pooja Hegde",
    "Farhan Qureshi",
    "Lakshmi Krishnan",
    "Omkar Deshpande",
    "Zoya Khan",
]
TAGLINES = [
    "Final year, clearing out my room",
    "CSE '27. Books mostly.",
    "Mech student, ask me about cycles",
    "Hostel B. Quick replies.",
    "Moving out in May",
    "Selling what I don't need anymore",
    "",
]
PICKUPS = ["Library entrance", "Central canteen", "Main gate", "Hostel block A", "Sports complex"]

# category slug -> [(title, rupees, mode, condition, description, attributes)]
LISTINGS: dict[str, list[tuple[str, int, str, str, str, dict[str, object]]]] = {
    "books-notes": [
        (
            "Engineering Mathematics II, B.S. Grewal",
            350,
            "negotiable",
            "good",
            "Some highlighting in the first four chapters. No torn pages.",
            {"subject": "Engineering Mathematics", "edition": "44th", "semester": 2},
        ),
        (
            "Data Structures using C, Reema Thareja",
            280,
            "fixed",
            "like_new",
            "Bought last semester, barely opened. Clean copy.",
            {"subject": "Data Structures", "edition": "3rd", "semester": 3},
        ),
        (
            "Handwritten Thermodynamics notes, full semester",
            150,
            "fixed",
            "good",
            "Neat notes with solved PYQs at the end. Got an A with these.",
            {"subject": "Thermodynamics", "semester": 4},
        ),
        (
            "Concepts of Physics Vol 1 & 2, H.C. Verma",
            400,
            "negotiable",
            "fair",
            "Covers are worn but all pages are intact. Great for first years.",
            {"subject": "Physics", "semester": 1},
        ),
        (
            "Operating System Concepts (Galvin)",
            550,
            "negotiable",
            "like_new",
            "International edition. No markings.",
            {"subject": "Operating Systems", "edition": "10th", "semester": 5},
        ),
        (
            "Microeconomics, Pindyck & Rubinfeld",
            0,
            "free",
            "fair",
            "Free to anyone taking ECON 101. Some notes in pencil.",
            {"subject": "Economics", "semester": 1},
        ),
        (
            "GATE CSE previous year papers (2010–2025)",
            200,
            "fixed",
            "good",
            "Topic-wise solved. A few pages folded.",
            {"subject": "GATE prep"},
        ),
    ],
    "electronics": [
        (
            "Lenovo IdeaPad Slim 3, Ryzen 5, 16GB",
            32000,
            "negotiable",
            "good",
            "2 years old, battery holds about 5 hours. Charger and sleeve included.",
            {"brand": "Lenovo", "model": "IdeaPad Slim 3", "warranty_left": False},
        ),
        (
            "boAt Rockerz 450 headphones",
            700,
            "fixed",
            "good",
            "Works perfectly, ear cushions slightly worn.",
            {"brand": "boAt", "model": "Rockerz 450", "warranty_left": False},
        ),
        (
            "Logitech wireless mouse + keyboard combo",
            900,
            "fixed",
            "like_new",
            "Used for 3 months. Selling because I moved to a laptop stand setup.",
            {"brand": "Logitech", "model": "MK270", "warranty_left": True},
        ),
        (
            "Arduino Uno starter kit with sensors",
            1200,
            "negotiable",
            "good",
            "Breadboard, jumper wires, ultrasonic and IR sensors, servo. Great for projects.",
            {"brand": "Arduino", "model": "Uno R3"},
        ),
        (
            "Mi 20000mAh power bank",
            800,
            "fixed",
            "good",
            "Charges a phone 4–5 times.",
            {"brand": "Xiaomi"},
        ),
        (
            'Dell 24" monitor, 1080p IPS',
            6500,
            "negotiable",
            "like_new",
            "No dead pixels. HDMI cable included.",
            {"brand": "Dell", "model": "P2422H", "warranty_left": True},
        ),
    ],
    "calculators-instruments": [
        (
            "Casio FX-991ES Plus scientific calculator",
            650,
            "negotiable",
            "good",
            "Used for one semester. Allowed in all university exams.",
            {"brand": "Casio", "model": "FX-991ES Plus"},
        ),
        (
            "Engineering drawing kit with mini drafter",
            450,
            "fixed",
            "good",
            "Mini drafter, set squares, compass, and sheet holder.",
            {"brand": "Omega"},
        ),
        (
            "Casio FX-82MS",
            300,
            "fixed",
            "fair",
            "Display slightly scratched, works fine.",
            {"brand": "Casio", "model": "FX-82MS"},
        ),
        (
            "Digital multimeter",
            500,
            "negotiable",
            "like_new",
            "Barely used, comes with probes.",
            {"brand": "Mastech"},
        ),
    ],
    "lab-gear-uniforms": [
        (
            "White lab coat, size M",
            0,
            "free",
            "good",
            "Washed and ironed. Free to a first year.",
            {"size": "M", "department": "Chemistry"},
        ),
        (
            "Safety goggles + nitrile gloves pack",
            150,
            "fixed",
            "new",
            "Goggles unused, 40 gloves left.",
            {"department": "Biotech"},
        ),
        (
            "Workshop apron and safety shoes (UK 9)",
            600,
            "negotiable",
            "good",
            "Needed for Mech workshop. Shoes have steel toe caps.",
            {"size": "UK 9", "department": "Mechanical"},
        ),
        (
            "Lab coat, size L",
            200,
            "fixed",
            "like_new",
            "Worn twice.",
            {"size": "L", "department": "Physics"},
        ),
    ],
    "hostel-room": [
        (
            "Study table lamp, LED with USB port",
            450,
            "fixed",
            "like_new",
            "Three brightness levels.",
            {},
        ),
        (
            "Foldable study table",
            900,
            "negotiable",
            "good",
            "Fits on a hostel bed. Sturdy.",
            {"dimensions": "60 x 40 cm"},
        ),
        (
            "Mattress protector + pillow set",
            400,
            "fixed",
            "good",
            "Washed. Single bed size.",
            {"dimensions": "Single"},
        ),
        ("Electric kettle 1.5L", 500, "fixed", "good", "Check hostel rules before buying!", {}),
        (
            "Extension board, 6 sockets with surge protection",
            0,
            "swap",
            "good",
            "Will swap for a desk organiser or a small mirror.",
            {},
        ),
        (
            "Mini fridge, 50L",
            5500,
            "negotiable",
            "good",
            "Perfect for a shared room. Moving out, must go by May.",
            {"dimensions": "50L"},
        ),
    ],
    "cycles-transport": [
        (
            "Hero Sprint 21-gear cycle",
            4500,
            "negotiable",
            "fair",
            "Gears shift fine, new brake pads last month. Lock included.",
            {"brand": "Hero", "gear_count": 21},
        ),
        (
            "Btwin Rockrider ST100",
            9000,
            "negotiable",
            "good",
            "Front suspension, serviced in January.",
            {"brand": "Btwin", "gear_count": 21},
        ),
        ("Cycle lock + helmet", 600, "fixed", "like_new", "Helmet size M.", {}),
        (
            "Ladies cycle with basket",
            3200,
            "negotiable",
            "good",
            "Single speed, very comfortable.",
            {"brand": "Atlas", "gear_count": 1},
        ),
    ],
    "clothing-accessories": [
        (
            "College fest hoodie (2025), size L",
            500,
            "fixed",
            "like_new",
            "Limited edition, washed once.",
            {"size": "L"},
        ),
        (
            "Formal blazer, navy, size 40",
            1500,
            "negotiable",
            "good",
            "Worn for two interviews. Dry cleaned.",
            {"size": "40"},
        ),
        ("Backpack, 30L with laptop sleeve", 800, "fixed", "good", 'Fits a 15.6" laptop.', {}),
    ],
    "sports-hobbies": [
        (
            "Yonex badminton racket + shuttles",
            900,
            "negotiable",
            "good",
            "Racket restrung recently.",
            {"item_type": "Badminton racket"},
        ),
        (
            "Acoustic guitar, Yamaha F280",
            5500,
            "negotiable",
            "good",
            "Comes with bag, capo and spare strings.",
            {"item_type": "Guitar"},
        ),
        (
            "Cricket kit bag with bat and pads",
            2200,
            "negotiable",
            "fair",
            "Bat is English willow.",
            {"item_type": "Cricket kit"},
        ),
        (
            "Chess board, tournament size",
            0,
            "free",
            "good",
            "All pieces present.",
            {"item_type": "Chess"},
        ),
        ("Yoga mat, 6mm", 350, "fixed", "like_new", "Non-slip.", {"item_type": "Yoga mat"}),
    ],
    "tickets-passes": [
        (
            "Fest pro-show pass, day 2",
            800,
            "fixed",
            "new",
            "Can't make it anymore. Transferable.",
            {"event_date": "21 Nov 2026"},
        ),
        (
            "Gym membership, 3 months remaining",
            1800,
            "negotiable",
            "new",
            "Campus gym, transferable with ID change.",
            {"event_date": "Valid till Feb 2027"},
        ),
    ],
    "other": [
        (
            "Plants: money plant and snake plant with pots",
            250,
            "fixed",
            "good",
            "Healthy and easy to look after.",
            {},
        ),
        (
            "Board games bundle: Uno, Monopoly Deal, Codenames",
            600,
            "negotiable",
            "good",
            "All cards present.",
            {},
        ),
        (
            "Whiteboard 2x3 ft with markers",
            700,
            "fixed",
            "good",
            "Great for planning and study groups.",
            {},
        ),
    ],
}

CONVERSATIONS = [
    [
        "Hi! Is this still available?",
        "Yes it is 🙂",
        "Can we meet at the library tomorrow at 4?",
        "Sure, see you there.",
    ],
    ["Would you take a bit less?", "I can do a small discount if you pick it up today."],
    ["Does it come with the charger?", "Yes, charger and the sleeve both."],
    ["Hey, interested! Which hostel are you in?", "Block A. Canteen works too."],
]


def remove(conn: Connection) -> None:
    demo = "SELECT id FROM identity.users WHERE email LIKE :like"
    p = {"like": DEMO_EMAIL_LIKE}
    conn.execute(text(f"DELETE FROM trust.reports WHERE reporter_id IN ({demo})"), p)  # noqa: S608
    conn.execute(
        text(
            f"DELETE FROM messaging.conversations WHERE buyer_id IN ({demo}) OR listing_id IN "  # noqa: S608
            f"(SELECT id FROM catalog.listings WHERE seller_id IN ({demo}))"
        ),
        p,
    )
    conn.execute(text(f"DELETE FROM catalog.listings WHERE seller_id IN ({demo})"), p)  # noqa: S608
    conn.execute(text("DELETE FROM identity.users WHERE email LIKE :like"), p)


def create(conn: Connection) -> None:
    rng = random.Random(42)  # noqa: S311 - deterministic demo data, not security
    now = datetime.now(UTC)
    seed(conn)

    for pos, name in enumerate(PICKUPS, start=10):
        conn.execute(
            text(
                "INSERT INTO catalog.pickup_points (name, position) VALUES (:n, :p) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"n": name, "p": pos},
        )
    pickup_ids = [
        conn.execute(
            text("SELECT id FROM catalog.pickup_points WHERE name = :n"), {"n": n}
        ).scalar_one()
        for n in PICKUPS
    ]

    users = []
    for i, name in enumerate(STUDENTS):
        first, last = name.lower().split(" ", 1)
        joined = now - timedelta(days=rng.randint(20, 300))
        uid = conn.execute(
            text(
                "INSERT INTO identity.users (email, terms_version, terms_accepted_at, created_at) "
                "VALUES (:e, 'demo', :j, :j) RETURNING id"
            ),
            {"e": f"demo.{first}.{i}@example.edu", "j": joined},
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO identity.profiles (user_id, handle, display_name, tagline) "
                "VALUES (:u, :h, :d, :t)"
            ),
            {"u": uid, "h": f"{first}_{last[:1]}{i}", "d": name, "t": rng.choice(TAGLINES)},
        )
        users.append(uid)

    listing_ids = []
    for slug, items in LISTINGS.items():
        cat_id = conn.execute(
            text("SELECT id FROM catalog.categories WHERE slug = :s"), {"s": slug}
        ).scalar_one()
        for title, rupees, mode, condition, desc, attrs in items:
            seller = rng.choice(users)
            published = now - timedelta(hours=rng.randint(1, 24 * 25))
            status = rng.choices(["active", "reserved", "sold"], weights=[85, 8, 7])[0]
            lid = conn.execute(
                text(
                    """
                    INSERT INTO catalog.listings (seller_id, category_id, pickup_point_id, title,
                        description, status, price_mode, price_paise, condition, attributes,
                        availability_note, published_at, expires_at, sold_at, created_at,
                        updated_at)
                    VALUES (:s, :c, :p, :t, :d, :st, :m, :price, :cond, CAST(:a AS jsonb), :avail,
                        :pub, :pub + interval '60 days', :sold, :pub, :pub)
                    RETURNING id
                    """
                ),
                {
                    "s": seller,
                    "c": cat_id,
                    "p": rng.choice(pickup_ids),
                    "t": title,
                    "d": desc,
                    "st": status,
                    "m": mode,
                    "price": rupees * 100,
                    "cond": condition,
                    "a": json.dumps(attrs),
                    "avail": rng.choice(
                        ["Weekdays after 4 pm", "Evenings", "Anytime on weekends", ""]
                    ),
                    "pub": published,
                    "sold": published + timedelta(days=2) if status == "sold" else None,
                },
            ).scalar_one()
            listing_ids.append((lid, seller, status))

    for uid in users:
        for lid, seller, status in rng.sample(listing_ids, 4):
            if seller != uid and status == "active":
                conn.execute(
                    text(
                        "INSERT INTO catalog.favorites (user_id, listing_id) VALUES (:u, :l) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"u": uid, "l": lid},
                )

    active = [x for x in listing_ids if x[2] == "active"]
    for lid, seller, _ in rng.sample(active, 12):
        buyer = rng.choice([u for u in users if u != seller])
        script = rng.choice(CONVERSATIONS)
        start = now - timedelta(hours=rng.randint(2, 72))
        cid = conn.execute(
            text(
                "INSERT INTO messaging.conversations (listing_id, buyer_id, created_at) "
                "VALUES (:l, :b, :t) RETURNING id"
            ),
            {"l": lid, "b": buyer, "t": start},
        ).scalar_one()
        for n, body in enumerate(script):
            conn.execute(
                text(
                    "INSERT INTO messaging.messages "
                    "(conversation_id, sender_id, client_nonce, body, created_at)"
                    " VALUES (:c, :s, gen_random_uuid(), :b, :t)"
                ),
                {
                    "c": cid,
                    "s": buyer if n % 2 == 0 else seller,
                    "b": body,
                    "t": start + timedelta(minutes=7 * n),
                },
            )
        conn.execute(
            text("UPDATE messaging.conversations SET last_message_at = :t WHERE id = :c"),
            {"c": cid, "t": start + timedelta(minutes=7 * (len(script) - 1))},
        )
    print(f"Demo data: {len(users)} students, {len(listing_ids)} listings, 12 conversations.")


if __name__ == "__main__":
    if get_settings().app_env == "production":
        sys.exit("Refusing to load demo data in production.")
    with get_engine().begin() as conn:
        remove(conn)
        if "--remove" in sys.argv:
            print("Demo data removed.")
        else:
            create(conn)
