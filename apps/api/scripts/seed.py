"""Idempotent seed from spec section 5.9. Safe to run repeatedly.

Pickup points and campus name are development placeholders until the owner supplies
real values (spec 0.2). Production launch is blocked on replacing them.
"""

import json

from sqlalchemy import Connection, text

from app.db import get_engine

# (slug, name, icon, fields) — field: (key, label, input_type, hint, options)
CATEGORIES = [
    (
        "books-notes",
        "Books and Notes",
        "book-open",
        [
            ("subject", "Subject", "text", "Example: Engineering Mathematics II", []),
            ("edition", "Edition", "text", "Example: 4th", []),
            ("semester", "Semester", "number", "Example: 3", []),
        ],
    ),
    (
        "electronics",
        "Electronics",
        "laptop",
        [
            ("brand", "Brand", "text", "Example: Lenovo", []),
            ("model", "Model", "text", "Example: IdeaPad Slim 3", []),
            ("warranty_left", "Warranty left", "boolean", "Is any warranty still valid?", []),
        ],
    ),
    (
        "calculators-instruments",
        "Calculators and Instruments",
        "calculator",
        [
            ("brand", "Brand", "text", "Example: Casio", []),
            ("model", "Model", "text", "Example: FX-991ES Plus", []),
        ],
    ),
    (
        "lab-gear-uniforms",
        "Lab Gear and Uniforms",
        "flask-conical",
        [
            ("size", "Size", "text", "Example: M", []),
            ("department", "Department", "text", "Example: Chemistry", []),
        ],
    ),
    (
        "hostel-room",
        "Hostel and Room",
        "bed",
        [
            ("dimensions", "Size or dimensions", "text", "Example: 120 x 60 cm", []),
        ],
    ),
    (
        "cycles-transport",
        "Cycles and Transport",
        "bike",
        [
            ("brand", "Brand", "text", "Example: Hero", []),
            ("gear_count", "Gear count", "number", "Example: 21", []),
        ],
    ),
    (
        "clothing-accessories",
        "Clothing and Accessories",
        "shirt",
        [
            ("size", "Size", "text", "Example: L", []),
        ],
    ),
    (
        "sports-hobbies",
        "Sports and Hobbies",
        "trophy",
        [
            ("item_type", "Item type", "text", "Example: Badminton racket", []),
        ],
    ),
    (
        "tickets-passes",
        "Tickets and Passes",
        "ticket",
        [
            ("event_date", "Event date", "text", "Example: 14 Nov 2026", []),
        ],
    ),
    ("other", "Other", "package", []),
]

PICKUP_POINTS = ["DEV Main gate", "DEV Library entrance", "DEV Canteen"]

SETTINGS = {
    "campus_name": "DEV Campus",
    "public_browsing": True,
    "listing_expiry_days": 60,
    "max_active_listings": 30,
    "notice_banner": "",
}


def seed(conn: Connection) -> None:
    for pos, (slug, name, icon, fields) in enumerate(CATEGORIES):
        cat_id = conn.execute(
            text(
                """
                INSERT INTO catalog.categories (slug, name, icon, position)
                VALUES (:slug, :name, :icon, :pos)
                ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
                RETURNING id
                """
            ),
            {"slug": slug, "name": name, "icon": icon, "pos": pos},
        ).scalar_one()
        for fpos, (key, label, input_type, hint, options) in enumerate(fields):
            conn.execute(
                text(
                    """
                    INSERT INTO catalog.category_fields
                        (category_id, key, label, input_type, hint, options, position)
                    VALUES (:cat, :key, :label, :type, :hint, :options, :pos)
                    ON CONFLICT (category_id, key) DO NOTHING
                    """
                ),
                {
                    "cat": cat_id,
                    "key": key,
                    "label": label,
                    "type": input_type,
                    "hint": hint,
                    "options": options,
                    "pos": fpos,
                },
            )
    for pos, name in enumerate(PICKUP_POINTS):
        conn.execute(
            text(
                "INSERT INTO catalog.pickup_points (name, position) VALUES (:name, :pos) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "pos": pos},
        )
    for key, value in SETTINGS.items():
        conn.execute(
            text(
                "INSERT INTO system.site_settings (key, value) "
                "VALUES (:key, CAST(:value AS jsonb)) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {"key": key, "value": json.dumps(value)},
        )


if __name__ == "__main__":
    with get_engine().begin() as conn:
        seed(conn)
    print("Seeded categories, pickup points and site settings.")
