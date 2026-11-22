"""Initial schema from BATON_BUILD_SPEC.md section 5.3.

Revision ID: 0001
Revises:
Create Date: 2026-11-02
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Verbatim from spec 5.3, except `CREATE SCHEMA system` uses IF NOT EXISTS because
# env.py creates it first to hold system.alembic_version (see docs/DECISIONS.md).
SCHEMA_SQL = r"""
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA identity;
CREATE SCHEMA media;
CREATE SCHEMA catalog;
CREATE SCHEMA messaging;
CREATE SCHEMA trust;
CREATE SCHEMA IF NOT EXISTS system;

-- IDENTITY ---------------------------------------------------------------

CREATE TYPE identity.user_role AS ENUM ('user', 'moderator', 'admin');
CREATE TYPE identity.user_status AS ENUM ('active', 'suspended', 'deleted');

CREATE TABLE identity.users (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email             citext NOT NULL UNIQUE,
    role              identity.user_role NOT NULL DEFAULT 'user',
    status            identity.user_status NOT NULL DEFAULT 'active',
    terms_version     text NOT NULL,
    terms_accepted_at timestamptz NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    deleted_at        timestamptz
);

CREATE TABLE identity.sessions (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    token_hash   bytea NOT NULL UNIQUE,
    device_label text NOT NULL DEFAULT 'Unknown device',
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    reauth_at    timestamptz,
    expires_at   timestamptz NOT NULL
);
CREATE INDEX sessions_user_idx ON identity.sessions (user_id);
CREATE INDEX sessions_expires_idx ON identity.sessions (expires_at);

CREATE TABLE identity.login_codes (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email       citext NOT NULL,
    code_hash   bytea NOT NULL,
    attempts    smallint NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    expires_at  timestamptz NOT NULL,
    consumed_at timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_codes_email_idx ON identity.login_codes (email, created_at DESC);
CREATE INDEX login_codes_expires_idx ON identity.login_codes (expires_at);

-- MEDIA ------------------------------------------------------------------

CREATE TABLE media.assets (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id       uuid NOT NULL REFERENCES identity.users(id),
    kind           text NOT NULL CHECK (kind IN ('listing', 'avatar', 'banner')),
    storage_prefix text NOT NULL UNIQUE,
    width          integer NOT NULL CHECK (width > 0),
    height         integer NOT NULL CHECK (height > 0),
    size_bytes     integer NOT NULL CHECK (size_bytes > 0),
    placeholder    text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX assets_owner_idx ON media.assets (owner_id);

-- Public profile lives apart from the private account row.
CREATE TABLE identity.profiles (
    user_id         uuid PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
    handle          citext NOT NULL UNIQUE CHECK (handle ~ '^[a-z0-9_]{3,24}$'),
    display_name    text NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 50),
    tagline         text NOT NULL DEFAULT '' CHECK (char_length(tagline) <= 80),
    bio             text NOT NULL DEFAULT '' CHECK (char_length(bio) <= 300),
    avatar_asset_id uuid REFERENCES media.assets(id) ON DELETE SET NULL,
    banner_asset_id uuid REFERENCES media.assets(id) ON DELETE SET NULL,
    accent_hex      char(7) CHECK (accent_hex ~ '^#[0-9A-Fa-f]{6}$'),
    layout          text NOT NULL DEFAULT 'grid' CHECK (layout IN ('grid', 'list')),
    show_sold       boolean NOT NULL DEFAULT true,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identity.preferences (
    user_id    uuid PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
    version    integer NOT NULL DEFAULT 1,
    settings   jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(settings) = 'object'),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- CATALOG ----------------------------------------------------------------

CREATE TYPE catalog.listing_status AS ENUM (
    'draft', 'active', 'reserved', 'sold', 'expired', 'hidden', 'removed'
);
CREATE TYPE catalog.price_mode AS ENUM ('fixed', 'negotiable', 'free', 'swap');
CREATE TYPE catalog.item_condition AS ENUM ('new', 'like_new', 'good', 'fair', 'for_parts');

CREATE TABLE catalog.categories (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{2,40}$'),
    name       text NOT NULL UNIQUE CHECK (char_length(name) BETWEEN 2 AND 40),
    icon       text NOT NULL,
    position   integer NOT NULL DEFAULT 0,
    is_active  boolean NOT NULL DEFAULT true
);

CREATE TABLE catalog.category_fields (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id uuid NOT NULL REFERENCES catalog.categories(id) ON DELETE CASCADE,
    key         text NOT NULL CHECK (key ~ '^[a-z][a-z0-9_]{1,30}$'),
    label       text NOT NULL CHECK (char_length(label) BETWEEN 1 AND 40),
    hint        text NOT NULL DEFAULT '' CHECK (char_length(hint) <= 120),
    input_type  text NOT NULL CHECK (input_type IN ('text', 'number', 'select', 'boolean')),
    options     text[] NOT NULL DEFAULT '{}',
    is_required boolean NOT NULL DEFAULT false,
    position    integer NOT NULL DEFAULT 0,
    UNIQUE (category_id, key)
);

CREATE TABLE catalog.pickup_points (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name      text NOT NULL UNIQUE CHECK (char_length(name) BETWEEN 2 AND 60),
    position  integer NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE catalog.listings (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id         uuid NOT NULL REFERENCES identity.users(id),
    category_id       uuid REFERENCES catalog.categories(id),
    pickup_point_id   uuid REFERENCES catalog.pickup_points(id),
    title             text NOT NULL DEFAULT '' CHECK (char_length(title) <= 80),
    description       text NOT NULL DEFAULT '' CHECK (char_length(description) <= 2000),
    status            catalog.listing_status NOT NULL DEFAULT 'draft',
    price_mode        catalog.price_mode NOT NULL DEFAULT 'fixed',
    price_paise       integer NOT NULL DEFAULT 0 CHECK (price_paise BETWEEN 0 AND 100000000),
    condition         catalog.item_condition,
    availability_note text NOT NULL DEFAULT '' CHECK (char_length(availability_note) <= 120),
    swap_for          text NOT NULL DEFAULT '' CHECK (char_length(swap_for) <= 120),
    attributes        jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(attributes) = 'object'),
    custom_details    jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(custom_details) = 'array'),
    pinned_at         timestamptz,
    published_at      timestamptz,
    expires_at        timestamptz,
    sold_at           timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    search_vector     tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english'::regconfig, title), 'A') ||
        setweight(to_tsvector('english'::regconfig, description), 'B')
    ) STORED,
    CONSTRAINT listings_publish_ready CHECK (
        status = 'draft' OR (
            char_length(btrim(title)) >= 3
            AND category_id IS NOT NULL
            AND pickup_point_id IS NOT NULL
            AND condition IS NOT NULL
            AND published_at IS NOT NULL
            AND expires_at IS NOT NULL
        )
    ),
    CONSTRAINT listings_price_valid CHECK (
        (price_mode IN ('free', 'swap') AND price_paise = 0)
        OR (price_mode IN ('fixed', 'negotiable') AND (status = 'draft' OR price_paise > 0))
    )
);
CREATE INDEX listings_feed_idx ON catalog.listings (published_at DESC, id DESC)
    WHERE status = 'active';
CREATE INDEX listings_category_feed_idx ON catalog.listings (category_id, published_at DESC, id DESC)
    WHERE status = 'active';
CREATE INDEX listings_price_idx ON catalog.listings (price_paise, id)
    WHERE status = 'active';
CREATE INDEX listings_seller_idx ON catalog.listings (seller_id, status);
CREATE INDEX listings_expiry_idx ON catalog.listings (expires_at)
    WHERE status IN ('active', 'reserved');
CREATE INDEX listings_search_idx ON catalog.listings USING gin (search_vector);
CREATE INDEX listings_title_trgm_idx ON catalog.listings USING gin (title gin_trgm_ops);
CREATE INDEX listings_attributes_idx ON catalog.listings USING gin (attributes jsonb_path_ops);

CREATE TABLE catalog.listing_images (
    listing_id uuid NOT NULL REFERENCES catalog.listings(id) ON DELETE CASCADE,
    asset_id   uuid NOT NULL UNIQUE REFERENCES media.assets(id) ON DELETE CASCADE,
    position   smallint NOT NULL CHECK (position BETWEEN 0 AND 7),
    PRIMARY KEY (listing_id, asset_id),
    CONSTRAINT listing_images_position_unique UNIQUE (listing_id, position)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE catalog.favorites (
    user_id    uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    listing_id uuid NOT NULL REFERENCES catalog.listings(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, listing_id)
);
CREATE INDEX favorites_listing_idx ON catalog.favorites (listing_id);

-- MESSAGING --------------------------------------------------------------

CREATE TABLE messaging.conversations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id          uuid NOT NULL REFERENCES catalog.listings(id),
    buyer_id            uuid NOT NULL REFERENCES identity.users(id),
    last_message_at     timestamptz,
    buyer_last_read_at  timestamptz,
    seller_last_read_at timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (listing_id, buyer_id)
);
CREATE INDEX conversations_buyer_idx ON messaging.conversations (buyer_id, last_message_at DESC);

CREATE TABLE messaging.messages (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES messaging.conversations(id) ON DELETE CASCADE,
    sender_id       uuid NOT NULL REFERENCES identity.users(id),
    client_nonce    uuid NOT NULL,
    body            text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, client_nonce)
);
CREATE INDEX messages_thread_idx ON messaging.messages (conversation_id, id);

-- TRUST ------------------------------------------------------------------

CREATE TABLE trust.reports (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id      uuid NOT NULL REFERENCES identity.users(id),
    listing_id       uuid REFERENCES catalog.listings(id) ON DELETE SET NULL,
    reported_user_id uuid REFERENCES identity.users(id),
    message_id       bigint REFERENCES messaging.messages(id) ON DELETE SET NULL,
    reason           text NOT NULL CHECK (reason IN (
        'prohibited_item', 'scam', 'harassment', 'spam', 'wrong_info', 'other'
    )),
    details          text NOT NULL DEFAULT '' CHECK (char_length(details) <= 1000),
    status           text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'actioned', 'dismissed')),
    resolved_by      uuid REFERENCES identity.users(id),
    resolved_at      timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX reports_queue_idx ON trust.reports (created_at) WHERE status = 'open';

CREATE TABLE trust.blocks (
    blocker_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    blocked_id uuid NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);
CREATE INDEX blocks_blocked_idx ON trust.blocks (blocked_id);

CREATE TABLE trust.moderation_actions (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id       uuid NOT NULL REFERENCES identity.users(id),
    action         text NOT NULL,
    report_id      uuid REFERENCES trust.reports(id),
    listing_id     uuid REFERENCES catalog.listings(id),
    target_user_id uuid REFERENCES identity.users(id),
    note           text NOT NULL DEFAULT '' CHECK (char_length(note) <= 1000),
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- SYSTEM -----------------------------------------------------------------

CREATE TABLE system.site_settings (
    key        text PRIMARY KEY,
    value      jsonb NOT NULL,
    updated_by uuid REFERENCES identity.users(id),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE system.rate_limits (
    bucket       text NOT NULL,
    window_start timestamptz NOT NULL,
    hits         integer NOT NULL DEFAULT 1,
    PRIMARY KEY (bucket, window_start)
);
"""

# Spec 5.7. Skipped when baton_app does not exist (e.g. a scratch database).
GRANTS_SQL = r"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'baton_app') THEN
        GRANT USAGE ON SCHEMA identity, media, catalog, messaging, trust, system TO baton_app;
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA identity, media, catalog, messaging, trust, system TO baton_app;
        GRANT USAGE, SELECT
            ON ALL SEQUENCES IN SCHEMA identity, media, catalog, messaging, trust, system TO baton_app;
        REVOKE ALL ON system.alembic_version FROM baton_app;
        REVOKE UPDATE, DELETE ON trust.moderation_actions FROM baton_app;
    END IF;
END
$$;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)
    op.execute(GRANTS_SQL)


def downgrade() -> None:
    # system holds alembic_version, so drop its tables rather than the schema.
    op.execute(
        """
        DROP SCHEMA trust, messaging, catalog, media, identity CASCADE;
        DROP TABLE system.site_settings, system.rate_limits;
        """
    )
