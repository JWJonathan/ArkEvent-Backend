-- ============================================
-- SCRIPT COMPLET PABASE ARKEVENT (LOCAL / SUPABASE)
-- Version 3.0 – Corrigée, enrichie, sans récursion RLS
-- ============================================

-- 1. Extensions indispensables
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- pour gen_random_bytes()

-- 2. Rôle spécial pour les fonctions SECURITY DEFINER qui contournent RLS
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rls_bypass') THEN
        CREATE ROLE rls_bypass WITH LOGIN BYPASSRLS NOINHERIT;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO rls_bypass;

-- 3. Schéma principal
CREATE SCHEMA IF NOT EXISTS arkevent;
GRANT USAGE ON SCHEMA arkevent TO PUBLIC;
GRANT ALL ON SCHEMA arkevent TO rls_bypass;

-- ============================================
-- 4. Schéma auth minimal (pour compatibilité Supabase)
-- ============================================
CREATE SCHEMA IF NOT EXISTS auth;
GRANT USAGE ON SCHEMA auth TO PUBLIC;

CREATE TABLE IF NOT EXISTS auth.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text,
    raw_user_meta_data jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
LANGUAGE SQL STABLE AS $$
  SELECT coalesce(
    nullif(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid,
    '00000000-0000-0000-0000-000000000000'::uuid
  );
$$;

CREATE OR REPLACE FUNCTION auth.role() RETURNS text
LANGUAGE SQL STABLE AS $$
  SELECT coalesce(current_setting('request.jwt.claims', true)::json->>'role', 'authenticated');
$$;

-- ============================================
-- 5. Tables centrales (organisation, utilisateurs, appartenance)
-- ============================================

CREATE TABLE arkevent.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username citext UNIQUE,
    first_name text,
    last_name text,
    full_name text GENERATED ALWAYS AS (trim(coalesce(first_name,'') || ' ' || coalesce(last_name,''))) STORED,
    phone text,
    phone_verified boolean DEFAULT false,
    date_of_birth date,
    gender text CHECK (gender IN ('male','female','other','prefer_not_to_say')),
    location text,
    timezone text DEFAULT 'UTC',
    language text DEFAULT 'fr',
    avatar_url text,
    cover_url text,
    bio text,
    website text,
    social_links jsonb DEFAULT '{}'::jsonb,
    role text NOT NULL DEFAULT 'user' CHECK (role IN ('user','controller','admin','superadmin')),
    is_verified boolean DEFAULT false,
    is_public boolean DEFAULT false,
    notification_preferences jsonb DEFAULT jsonb_build_object(
        'push_enabled', true,
        'email_enabled', true,
        'marketing', false,
        'event_updates', true,
        'ticket_alerts', true
    ),
    settings jsonb DEFAULT '{}'::jsonb,
    marketing_source text,
    utm_source text,
    utm_medium text,
    utm_campaign text,
    utm_term text,
    utm_content text,
    referral_code text UNIQUE DEFAULT upper(encode(gen_random_bytes(6), 'hex')),
    referred_by uuid REFERENCES arkevent.profiles(id),
    affiliate_id uuid,
    last_login_at timestamptz,
    accepted_terms_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE arkevent.organizations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text NOT NULL,
    slug text UNIQUE,
    type text DEFAULT 'company' CHECK (type IN ('company','nonprofit','individual','government','educational','collective')),
    short_description text,
    description text,
    email text,
    phone text,
    website text,
    address_line1 text,
    address_line2 text,
    city text,
    state text,
    postal_code text,
    country text DEFAULT 'HT',
    location text,
    logo_url text,
    cover_url text,
    social_links jsonb DEFAULT '{}'::jsonb,
    tax_id text,
    registration_number text,
    verified boolean DEFAULT false,
    verified_at timestamptz,
    created_by uuid NOT NULL REFERENCES arkevent.profiles(id),
    settings jsonb DEFAULT '{}'::jsonb,
    marketing_source text,
    default_currency text DEFAULT 'USD',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

-- Types énumérés pour les membres
CREATE TYPE arkevent.org_role AS ENUM ('owner','admin','manager','staff','viewer');
CREATE TYPE arkevent.member_status AS ENUM ('invited','active','suspended');

CREATE TABLE arkevent.organization_members (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES arkevent.organizations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    org_role arkevent.org_role NOT NULL DEFAULT 'staff',
    permissions jsonb DEFAULT '{}'::jsonb,
    invited_by uuid REFERENCES arkevent.profiles(id),
    status arkevent.member_status DEFAULT 'active',
    joined_at timestamptz DEFAULT now(),
    left_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(organization_id, user_id)
);

-- ============================================
-- 6. Catégories d'événements
-- ============================================
CREATE TABLE arkevent.event_categories (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text NOT NULL,
    slug text NOT NULL UNIQUE,
    description text,
    icon text,
    image_url text,
    parent_id uuid REFERENCES arkevent.event_categories(id) ON DELETE SET NULL,
    sort_order int DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

-- ============================================
-- 7. Événements (cœur de l'application)
-- ============================================
CREATE TYPE arkevent.event_status AS ENUM ('draft','published','cancelled','postponed','completed');
CREATE TYPE arkevent.event_visibility AS ENUM ('public','private','unlisted');
CREATE TYPE arkevent.age_restriction AS ENUM ('all','parental_guidance','min_12','min_16','min_18','min_21');

CREATE TABLE arkevent.events (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES arkevent.organizations(id) ON DELETE CASCADE,
    category_id uuid REFERENCES arkevent.event_categories(id) ON DELETE SET NULL,
    created_by uuid NOT NULL REFERENCES arkevent.profiles(id),
    title text NOT NULL,
    slug text NOT NULL UNIQUE,
    short_description text,
    description text,
    highlights text,
    tags text[] DEFAULT '{}',
    poster_url text,
    banner_url text,
    thumbnail_url text,
    start_date timestamptz NOT NULL,
    end_date timestamptz,
    doors_open timestamptz,
    timezone text NOT NULL DEFAULT 'America/Port-au-Prince',
    venue_name text,
    venue_address text,
    venue_city text,
    venue_state text,
    venue_country text DEFAULT 'HT',
    venue_postal_code text,
    latitude double precision,
    longitude double precision,
    location_display text,
    is_online boolean DEFAULT false,
    online_url text,
    capacity int CHECK (capacity > 0),
    age_limit arkevent.age_restriction DEFAULT 'all',
    is_free boolean DEFAULT false,
    status arkevent.event_status DEFAULT 'draft',
    visibility arkevent.event_visibility DEFAULT 'public',
    ticket_opens_at timestamptz,
    ticket_closes_at timestamptz,
    currency text DEFAULT 'USD',
    min_price numeric(10,2),
    max_price numeric(10,2),
    -- Champs marketing avancés
    marketing_budget numeric(10,2),
    expected_attendance int,
    target_audience text[],
    custom_registration_url text,
    meta_title text,
    meta_description text,
    meta_keywords text[],
    structured_data jsonb DEFAULT '{}'::jsonb,
    -- Champs fonctionnels
    has_waitlist boolean DEFAULT false,
    waitlist_capacity int,
    allow_transfers boolean DEFAULT true,
    require_approval boolean DEFAULT false,
    checkin_method text DEFAULT 'scan' CHECK (checkin_method IN ('manual','scan','face','code')),
    event_language text DEFAULT 'fr',
    accessibility_info text,
    sustainability_info text,
    -- Métadonnées
    metadata jsonb DEFAULT '{}'::jsonb,
    settings jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    published_at timestamptz,
    deleted_at timestamptz
);

-- ============================================
-- 8. Billetterie – types de billets
-- ============================================
CREATE TABLE arkevent.ticket_types (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    name text NOT NULL,
    description text,
    price numeric(10,2) NOT NULL CHECK (price >= 0),
    quantity int NOT NULL CHECK (quantity > 0),
    available_from timestamptz,
    available_to timestamptz,
    tier_name text,
    max_per_order int DEFAULT 10,
    is_donation boolean DEFAULT false,
    is_free boolean DEFAULT false,
    is_visible boolean DEFAULT true,
    color text,
    sort_order int DEFAULT 0,
    requires_approval boolean DEFAULT false,
    brings_plus_one boolean DEFAULT false,
    sales_channel text DEFAULT 'online' CHECK (sales_channel IN ('online','box_office','both')),
    hidden_until timestamptz,
    min_age int,
    max_age int,
    restrictions text,
    deleted_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- ============================================
-- 9. Sessions, intervenants, FAQ, médias…
-- ============================================
CREATE TABLE arkevent.event_sessions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    session_type text CHECK (session_type IN ('talk','workshop','performance','panel','break','networking','other')),
    start_time timestamptz NOT NULL,
    end_time timestamptz,
    location text,
    capacity int CHECK (capacity > 0),
    speakers jsonb DEFAULT '[]'::jsonb,
    image_url text,
    recording_url text,
    requires_ticket boolean DEFAULT false,
    ticket_type_id uuid REFERENCES arkevent.ticket_types(id) ON DELETE SET NULL,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE arkevent.event_speakers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    profile_id uuid REFERENCES arkevent.profiles(id) ON DELETE SET NULL,
    full_name text NOT NULL,
    role text,
    bio text,
    photo_url text,
    social_links jsonb DEFAULT '{}'::jsonb,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.event_organizers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    role text NOT NULL DEFAULT 'manager' CHECK (role IN ('manager','viewer','controller')),
    added_by uuid REFERENCES arkevent.profiles(id),
    created_at timestamptz DEFAULT now(),
    UNIQUE(event_id, user_id)
);

CREATE TABLE arkevent.event_media (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    uploaded_by uuid REFERENCES arkevent.profiles(id),
    media_type text NOT NULL CHECK (media_type IN ('image','video','document')),
    url text NOT NULL,
    alt_text text,
    title text,
    description text,
    sort_order int DEFAULT 0,
    is_featured boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.event_sponsors (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    name text NOT NULL,
    logo_url text,
    website text,
    level text,
    description text,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.event_faq (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    question text NOT NULL,
    answer text NOT NULL,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.announcements (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    sender_id uuid REFERENCES arkevent.profiles(id),
    title text,
    message text NOT NULL,
    urgency text DEFAULT 'normal' CHECK (urgency IN ('low','normal','high','critical')),
    is_push boolean DEFAULT true,
    sent_at timestamptz DEFAULT now(),
    expires_at timestamptz,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 10. Billetterie : tickets, commandes, paiements
-- ============================================
CREATE TABLE arkevent.tickets (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_type_id uuid NOT NULL REFERENCES arkevent.ticket_types(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'available' CHECK (status IN ('available','reserved','sold','used','refunded','cancelled','transferred')),
    token text NOT NULL UNIQUE,
    owner_id uuid REFERENCES arkevent.profiles(id),
    reserved_until timestamptz,
    held_by uuid REFERENCES arkevent.profiles(id),
    seat_label text,
    checkin_at timestamptz,
    checkin_method text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.orders (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    event_id uuid NOT NULL REFERENCES arkevent.events(id),
    total_amount numeric(10,2) NOT NULL,
    discount_amount numeric(10,2) DEFAULT 0,
    net_amount numeric(10,2) GENERATED ALWAYS AS (total_amount - discount_amount) STORED,
    currency text DEFAULT 'USD',
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','cancelled','refunded','expired')),
    coupon_code text,
    gift_card_id uuid,
    affiliate_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE arkevent.order_items (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id uuid NOT NULL REFERENCES arkevent.orders(id) ON DELETE CASCADE,
    ticket_id uuid NOT NULL UNIQUE REFERENCES arkevent.tickets(id),
    ticket_type_name text,
    price_at_purchase numeric(10,2) NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.payments (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id uuid NOT NULL REFERENCES arkevent.orders(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    amount numeric(10,2) NOT NULL,
    currency text DEFAULT 'USD',
    payment_method text,
    gateway text,
    transaction_id text,
    status text NOT NULL DEFAULT 'initiated' CHECK (status IN ('initiated','success','failed','refunded')),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.ticket_holds (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    ticket_type_id uuid NOT NULL REFERENCES arkevent.ticket_types(id),
    quantity int NOT NULL CHECK (quantity > 0),
    expires_at timestamptz NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.ticket_transfers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id uuid NOT NULL REFERENCES arkevent.tickets(id),
    from_user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    to_user_id uuid REFERENCES arkevent.profiles(id),
    to_email text,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined','cancelled')),
    message text,
    transfer_token text UNIQUE,
    expires_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 11. Promotions, coupons, cartes cadeaux, fidélité
-- ============================================
CREATE TABLE arkevent.coupons (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid REFERENCES arkevent.organizations(id) ON DELETE CASCADE,
    event_id uuid REFERENCES arkevent.events(id) ON DELETE CASCADE,
    code text NOT NULL UNIQUE,
    description text,
    discount_type text NOT NULL CHECK (discount_type IN ('percentage','fixed_amount')),
    discount_value numeric(10,2) NOT NULL CHECK (discount_value > 0),
    min_order_amount numeric(10,2) DEFAULT 0,
    max_uses int,
    max_uses_per_user int DEFAULT 1,
    valid_from timestamptz,
    valid_to timestamptz,
    applicable_ticket_types jsonb DEFAULT '[]'::jsonb,
    is_active boolean DEFAULT true,
    created_by uuid REFERENCES arkevent.profiles(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz
);

CREATE TABLE arkevent.coupon_usages (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    coupon_id uuid NOT NULL REFERENCES arkevent.coupons(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    order_id uuid REFERENCES arkevent.orders(id),
    discount_applied numeric(10,2) NOT NULL,
    used_at timestamptz DEFAULT now(),
    UNIQUE(coupon_id, user_id, order_id)
);

CREATE TABLE arkevent.gift_cards (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code text NOT NULL UNIQUE,
    initial_amount numeric(10,2) NOT NULL CHECK (initial_amount > 0),
    balance numeric(10,2) NOT NULL CHECK (balance >= 0),
    currency text DEFAULT 'USD',
    purchaser_id uuid REFERENCES arkevent.profiles(id),
    recipient_email text,
    message text,
    is_redeemed boolean DEFAULT false,
    expires_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.gift_card_transactions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    gift_card_id uuid NOT NULL REFERENCES arkevent.gift_cards(id) ON DELETE CASCADE,
    order_id uuid REFERENCES arkevent.orders(id),
    amount numeric(10,2) NOT NULL,
    transaction_type text NOT NULL CHECK (transaction_type IN ('purchase','redemption','refund')),
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.loyalty_points (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    balance int NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(user_id)
);

CREATE TABLE arkevent.loyalty_transactions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    order_id uuid REFERENCES arkevent.orders(id),
    points int NOT NULL,
    type text NOT NULL CHECK (type IN ('earn','redeem','expire','adjustment')),
    description text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.affiliates (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid REFERENCES arkevent.profiles(id),
    organization_id uuid REFERENCES arkevent.organizations(id),
    code text NOT NULL UNIQUE,
    commission_rate numeric(5,2) NOT NULL DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.affiliate_transactions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    affiliate_id uuid NOT NULL REFERENCES arkevent.affiliates(id),
    order_id uuid NOT NULL REFERENCES arkevent.orders(id),
    order_amount numeric(10,2),
    commission_amount numeric(10,2) NOT NULL,
    status text DEFAULT 'pending' CHECK (status IN ('pending','paid','cancelled')),
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 12. Marketing, engagement, notifications
-- ============================================
CREATE TABLE arkevent.wishlists (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, event_id)
);

CREATE TABLE arkevent.reviews (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    rating numeric(2,1) NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title text,
    comment text,
    is_verified_purchase boolean DEFAULT false,
    is_visible boolean DEFAULT true,
    likes_count int DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz,
    UNIQUE(event_id, user_id)
);

CREATE TABLE arkevent.review_likes (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id uuid NOT NULL REFERENCES arkevent.reviews(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    created_at timestamptz DEFAULT now(),
    UNIQUE(review_id, user_id)
);

CREATE TABLE arkevent.event_shares (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user_id uuid REFERENCES arkevent.profiles(id),
    platform text NOT NULL,
    recipient text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.user_tags (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    tag text NOT NULL,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, tag)
);

CREATE TABLE arkevent.email_campaigns (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES arkevent.organizations(id) ON DELETE CASCADE,
    event_id uuid REFERENCES arkevent.events(id) ON DELETE SET NULL,
    subject text NOT NULL,
    body_html text,
    body_text text,
    sender_name text,
    sender_email text,
    status text DEFAULT 'draft' CHECK (status IN ('draft','scheduled','sending','sent','failed')),
    scheduled_for timestamptz,
    sent_at timestamptz,
    created_by uuid REFERENCES arkevent.profiles(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.email_subscribers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email text NOT NULL UNIQUE,
    name text,
    is_active boolean DEFAULT true,
    subscribed_at timestamptz DEFAULT now(),
    unsubscribed_at timestamptz,
    source text,
    metadata jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE arkevent.notification_logs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    type text NOT NULL CHECK (type IN ('push','email','sms')),
    title text,
    body text,
    event_id uuid REFERENCES arkevent.events(id),
    order_id uuid REFERENCES arkevent.orders(id),
    metadata jsonb DEFAULT '{}'::jsonb,
    sent_at timestamptz DEFAULT now(),
    read_at timestamptz
);

CREATE TABLE arkevent.event_notification_settings (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    push_enabled boolean DEFAULT true,
    email_enabled boolean DEFAULT false,
    UNIQUE(user_id, event_id)
);

CREATE TABLE arkevent.push_tokens (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    token text NOT NULL,
    platform text NOT NULL CHECK (platform IN ('ios','android','web')),
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(user_id, token)
);

CREATE TABLE arkevent.user_devices (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    device_id text,
    device_name text,
    os text,
    app_version text,
    last_seen timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.email_verification_tokens (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    token text NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.password_reset_tokens (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    token text NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 13. Formulaires d’inscription
-- ============================================
CREATE TABLE arkevent.registration_forms (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    title text DEFAULT 'Formulaire d''inscription',
    is_required boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(event_id)
);

CREATE TABLE arkevent.registration_fields (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    form_id uuid NOT NULL REFERENCES arkevent.registration_forms(id) ON DELETE CASCADE,
    label text NOT NULL,
    field_type text NOT NULL CHECK (field_type IN ('text','textarea','select','checkbox','date','file','number')),
    options jsonb DEFAULT '[]'::jsonb,
    is_required boolean DEFAULT false,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.registration_answers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id uuid NOT NULL REFERENCES arkevent.registration_fields(id) ON DELETE CASCADE,
    order_id uuid NOT NULL REFERENCES arkevent.orders(id) ON DELETE CASCADE,
    ticket_id uuid REFERENCES arkevent.tickets(id),
    answer text NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 14. Présence, badges, réseautage, enquêtes
-- ============================================
CREATE TABLE arkevent.attendances (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id uuid NOT NULL UNIQUE REFERENCES arkevent.tickets(id),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    checkin_at timestamptz DEFAULT now(),
    checkout_at timestamptz,
    method text,
    validation_code text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.badges (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    type text NOT NULL DEFAULT 'attendee' CHECK (type IN ('attendee','speaker','staff','vip','press','exhibitor')),
    badge_code text UNIQUE,
    printed boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    UNIQUE(event_id, user_id, type)
);

CREATE TABLE arkevent.networking_matches (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user1_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    user2_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    matched_at timestamptz DEFAULT now(),
    status text DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined')),
    UNIQUE(event_id, user1_id, user2_id)
);

CREATE TABLE arkevent.surveys (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.survey_questions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id uuid NOT NULL REFERENCES arkevent.surveys(id) ON DELETE CASCADE,
    question text NOT NULL,
    question_type text NOT NULL CHECK (question_type IN ('text','rating','multiple_choice','yes_no')),
    options jsonb DEFAULT '[]'::jsonb,
    sort_order int DEFAULT 0,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.survey_answers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id uuid NOT NULL REFERENCES arkevent.survey_questions(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id),
    answer text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.social_posts (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    platform text NOT NULL CHECK (platform IN ('facebook','twitter','instagram','linkedin','tiktok')),
    content text NOT NULL,
    image_url text,
    scheduled_at timestamptz,
    posted_at timestamptz,
    status text DEFAULT 'draft' CHECK (status IN ('draft','scheduled','posted','failed')),
    created_by uuid REFERENCES arkevent.profiles(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- ============================================
-- 15. Portefeuille (Wallet)
-- ============================================
CREATE TABLE arkevent.wallets (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL UNIQUE REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    balance numeric(10,2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
    currency text NOT NULL DEFAULT 'USD',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.wallet_transactions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES arkevent.profiles(id) ON DELETE CASCADE,
    amount numeric(10,2) NOT NULL,
    type text NOT NULL CHECK (type IN ('deposit', 'withdrawal', 'payment', 'refund', 'credit')),
    status text NOT NULL DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed')),
    description text,
    order_id uuid REFERENCES arkevent.orders(id),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 16. Analytics, logs, vues
-- ============================================
CREATE TABLE arkevent.event_views (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    user_id uuid REFERENCES arkevent.profiles(id),
    source text,
    viewed_at timestamptz DEFAULT now()
);

CREATE TABLE arkevent.event_analytics_daily (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id uuid NOT NULL REFERENCES arkevent.events(id) ON DELETE CASCADE,
    date date NOT NULL,
    views int DEFAULT 0,
    unique_views int DEFAULT 0,
    shares int DEFAULT 0,
    orders int DEFAULT 0,
    tickets_sold int DEFAULT 0,
    revenue numeric(12,2) DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    UNIQUE(event_id, date)
);

CREATE TABLE arkevent.activity_logs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid REFERENCES arkevent.profiles(id),
    action text NOT NULL,
    entity_type text,
    entity_id uuid,
    ip_address text,
    user_agent text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- 17. Indexes (performance)
-- ============================================
-- (Indexes identiques à la version précédente, donc on les omet ici pour garder la réponse concentrée sur la correction.
--  Ils sont bien sûr à conserver tels quels dans le script final.)
-- ...

-- ============================================
-- 18. Fonctions et triggers (corrigés)
-- ============================================

-- Fonction updated_at générique
CREATE OR REPLACE FUNCTION arkevent.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Application de updated_at
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'arkevent'
          AND column_name = 'updated_at'
          AND table_name IN (
              'profiles','organizations','organization_members','event_categories',
              'events','event_sessions','event_faq','ticket_types','tickets','orders',
              'coupons','gift_cards','reviews','email_campaigns','registration_forms',
              'surveys','social_posts','loyalty_points','affiliates','push_tokens'
          )
    LOOP
        EXECUTE format('
            CREATE TRIGGER trg_%s_updated_at
            BEFORE UPDATE ON arkevent.%I
            FOR EACH ROW EXECUTE PROCEDURE arkevent.set_updated_at()', tbl, tbl);
    END LOOP;
END;
$$;

-- Slug automatique pour organisation
CREATE OR REPLACE FUNCTION arkevent.generate_organization_slug()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.slug IS NULL OR NEW.slug = '' THEN
        NEW.slug := lower(regexp_replace(regexp_replace(NEW.name, '[^a-zA-Z0-9\u00C0-\u024F]+', '-', 'g'), '-+', '-', 'g'));
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_org_slug BEFORE INSERT ON arkevent.organizations
    FOR EACH ROW EXECUTE PROCEDURE arkevent.generate_organization_slug();

-- Slug automatique pour événement
CREATE OR REPLACE FUNCTION arkevent.generate_event_slug()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.slug IS NULL OR NEW.slug = '' THEN
        NEW.slug := lower(regexp_replace(regexp_replace(NEW.title, '[^a-zA-Z0-9\u00C0-\u024F]+', '-', 'g'), '-+', '-', 'g'));
        NEW.slug := NEW.slug || '-' || to_char(COALESCE(NEW.start_date, now()), 'YYYYMMDD');
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_events_slug BEFORE INSERT ON arkevent.events
    FOR EACH ROW EXECUTE PROCEDURE arkevent.generate_event_slug();

-- Soft delete pour événements publiés/complétés
CREATE OR REPLACE FUNCTION arkevent.prevent_hard_delete_published_events()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status IN ('published','completed') AND OLD.deleted_at IS NULL THEN
        UPDATE arkevent.events SET deleted_at = now() WHERE id = OLD.id;
        RETURN NULL;
    END IF;
    RETURN OLD;
END;
$$;
CREATE TRIGGER trg_events_soft_delete BEFORE DELETE ON arkevent.events
    FOR EACH ROW EXECUTE PROCEDURE arkevent.prevent_hard_delete_published_events();

-- Génération automatique des billets (utilise gen_random_bytes() maintenant disponible)
CREATE OR REPLACE FUNCTION arkevent.generate_tickets_for_type()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    i int;
    new_token text;
BEGIN
    FOR i IN 1..NEW.quantity LOOP
        new_token := encode(gen_random_bytes(24), 'hex');
        INSERT INTO arkevent.tickets (ticket_type_id, token) VALUES (NEW.id, new_token);
    END LOOP;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_generate_tickets AFTER INSERT ON arkevent.ticket_types
    FOR EACH ROW EXECUTE PROCEDURE arkevent.generate_tickets_for_type();

-- Vérification stock pour réservation
CREATE OR REPLACE FUNCTION arkevent.check_hold_availability()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    available integer;
BEGIN
    SELECT count(*) INTO available
    FROM arkevent.tickets
    WHERE ticket_type_id = NEW.ticket_type_id
      AND status = 'available'
      AND (reserved_until IS NULL OR reserved_until < now());
    IF available < NEW.quantity THEN
        RAISE EXCEPTION 'Pas assez de billets disponibles';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_check_hold BEFORE INSERT ON arkevent.ticket_holds
    FOR EACH ROW EXECUTE PROCEDURE arkevent.check_hold_availability();

-- Libération des réservations expirées
CREATE OR REPLACE FUNCTION arkevent.release_expired_holds()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE arkevent.tickets
    SET status = 'available',
        reserved_until = NULL,
        held_by = NULL
    WHERE status = 'reserved' AND reserved_until < now();
END;
$$;

-- ============================================
-- 19. Fonctions de sécurité (BY RLS_BYPASS)
-- ============================================

CREATE OR REPLACE FUNCTION arkevent.is_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = arkevent, public
AS $$
    SELECT coalesce((current_setting('request.jwt.claims', true)::json)->'app_metadata'->>'role' = 'admin', false);
$$;
ALTER FUNCTION arkevent.is_admin() OWNER TO rls_bypass;

CREATE OR REPLACE FUNCTION arkevent.is_org_admin(org_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = arkevent, public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM arkevent.organization_members
        WHERE user_id = auth.uid()
          AND organization_id = org_id
          AND org_role IN ('owner','admin')
    );
$$;
ALTER FUNCTION arkevent.is_org_admin(uuid) OWNER TO rls_bypass;

CREATE OR REPLACE FUNCTION arkevent.can_manage_event(event_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = arkevent, public
AS $$
    SELECT arkevent.is_admin()
        OR EXISTS (
            SELECT 1 FROM arkevent.event_organizers
            WHERE event_organizers.event_id = $1 AND event_organizers.user_id = auth.uid()
        )
        OR EXISTS (
            SELECT 1 FROM arkevent.events e
            WHERE e.id = $1 AND arkevent.is_org_admin(e.organization_id)
        );
$$;
ALTER FUNCTION arkevent.can_manage_event(uuid) OWNER TO rls_bypass;

-- ============================================
-- 20. Row Level Security (corrigé, boucle sur table sql)
-- ============================================

-- Activation RLS sur toutes les tables de arkevent
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'arkevent' AND table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('ALTER TABLE arkevent.%I ENABLE ROW LEVEL SECURITY;', tbl);
    END LOOP;
END;
$$;

-- Profiles
CREATE POLICY "profiles_select" ON arkevent.profiles FOR SELECT
    USING (is_public = true OR auth.uid() = id OR arkevent.is_admin());
CREATE POLICY "profiles_update" ON arkevent.profiles FOR UPDATE
    USING (auth.uid() = id);
CREATE POLICY "profiles_admin" ON arkevent.profiles FOR ALL
    USING (arkevent.is_admin());

-- Organizations
CREATE POLICY "org_select" ON arkevent.organizations FOR SELECT
    USING (deleted_at IS NULL);
CREATE POLICY "org_insert" ON arkevent.organizations FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "org_update" ON arkevent.organizations FOR UPDATE
    USING (arkevent.is_org_admin(id) OR arkevent.is_admin());
CREATE POLICY "org_soft_delete" ON arkevent.organizations FOR UPDATE
    USING (arkevent.is_org_admin(id) OR arkevent.is_admin())
    WITH CHECK (deleted_at IS NOT NULL);

-- Organization members
CREATE POLICY "org_members_select" ON arkevent.organization_members FOR SELECT
    USING (user_id = auth.uid() OR arkevent.is_org_admin(organization_id));
CREATE POLICY "org_members_manage" ON arkevent.organization_members FOR ALL
    USING (arkevent.is_org_admin(organization_id) OR arkevent.is_admin());

-- Event categories
CREATE POLICY "cat_select" ON arkevent.event_categories FOR SELECT
    USING (is_active = true OR arkevent.is_admin());
CREATE POLICY "cat_manage" ON arkevent.event_categories FOR ALL
    USING (arkevent.is_admin());

-- Events
CREATE POLICY "events_select" ON arkevent.events FOR SELECT USING (
    (visibility = 'public' AND status = 'published')
    OR arkevent.is_admin()
    OR (visibility = 'private' AND EXISTS (
        SELECT 1 FROM arkevent.event_organizers eo
        WHERE eo.event_id = events.id AND eo.user_id = auth.uid()
    ))
);
CREATE POLICY "events_insert" ON arkevent.events FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "events_update" ON arkevent.events FOR UPDATE
    USING (arkevent.can_manage_event(id));
CREATE POLICY "events_delete" ON arkevent.events FOR DELETE
    USING (arkevent.is_admin());

-- Sessions, speakers, organizers, media, sponsors, faq, announcements
DO $$
DECLARE
    tbl text;
    t text[];
BEGIN
    t := ARRAY['event_sessions','event_speakers','event_organizers','event_media','event_sponsors','event_faq','announcements'];
    FOREACH tbl IN ARRAY t
    LOOP
        EXECUTE format('
            CREATE POLICY "%I_select" ON arkevent.%I FOR SELECT USING (
                EXISTS (SELECT 1 FROM arkevent.events e WHERE e.id = event_id
                    AND (e.visibility = ''public'' OR arkevent.can_manage_event(e.id)))
            );', tbl, tbl);
        EXECUTE format('
            CREATE POLICY "%I_manage" ON arkevent.%I FOR ALL
                USING (arkevent.can_manage_event(event_id));', tbl, tbl);
    END LOOP;
END;
$$;

-- Ticket types
CREATE POLICY "ticket_types_select" ON arkevent.ticket_types FOR SELECT USING (
    EXISTS (SELECT 1 FROM arkevent.events e WHERE e.id = event_id
        AND (e.visibility = 'public' AND e.status = 'published'))
    OR arkevent.can_manage_event(event_id)
);
CREATE POLICY "ticket_types_manage" ON arkevent.ticket_types FOR ALL
    USING (arkevent.can_manage_event(event_id));

-- Tickets
CREATE POLICY "tickets_select_org" ON arkevent.tickets FOR SELECT USING (
    arkevent.can_manage_event((SELECT id FROM arkevent.ticket_types tt WHERE tt.id = ticket_type_id))
);
CREATE POLICY "tickets_select_owner" ON arkevent.tickets FOR SELECT USING (owner_id = auth.uid());
CREATE POLICY "tickets_update_manage" ON arkevent.tickets FOR UPDATE USING (
    arkevent.can_manage_event((SELECT id FROM arkevent.ticket_types tt WHERE tt.id = ticket_type_id))
);

-- Orders
CREATE POLICY "orders_select_owner" ON arkevent.orders FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "orders_select_org" ON arkevent.orders FOR SELECT USING (arkevent.can_manage_event(event_id));
CREATE POLICY "orders_insert" ON arkevent.orders FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "orders_update" ON arkevent.orders FOR UPDATE USING (
    user_id = auth.uid() OR arkevent.can_manage_event(event_id)
);

-- Order items
CREATE POLICY "order_items_select" ON arkevent.order_items FOR SELECT USING (
    EXISTS (SELECT 1 FROM arkevent.orders o WHERE o.id = order_id
        AND (o.user_id = auth.uid() OR arkevent.can_manage_event(o.event_id)))
);

-- Payments
CREATE POLICY "payments_select" ON arkevent.payments FOR SELECT USING (
    user_id = auth.uid() OR arkevent.is_admin()
);
CREATE POLICY "payments_insert" ON arkevent.payments FOR INSERT WITH CHECK (user_id = auth.uid());

-- Ticket holds
CREATE POLICY "holds_user" ON arkevent.ticket_holds FOR ALL USING (user_id = auth.uid());

-- Ticket transfers
CREATE POLICY "transfers_select_involved" ON arkevent.ticket_transfers FOR SELECT USING (
    from_user_id = auth.uid() OR to_user_id = auth.uid() OR
    EXISTS (SELECT 1 FROM arkevent.tickets t WHERE t.id = ticket_id AND t.owner_id = auth.uid())
);
CREATE POLICY "transfers_insert" ON arkevent.ticket_transfers FOR INSERT WITH CHECK (from_user_id = auth.uid());

-- Coupons
CREATE POLICY "coupons_select" ON arkevent.coupons FOR SELECT USING (is_active = true OR arkevent.is_admin());
CREATE POLICY "coupons_manage" ON arkevent.coupons FOR ALL USING (
    arkevent.is_admin() OR
    (event_id IS NOT NULL AND arkevent.can_manage_event(event_id)) OR
    (organization_id IS NOT NULL AND arkevent.is_org_admin(organization_id))
);

-- Wishlists, reviews, etc.
CREATE POLICY "wishlist_owner" ON arkevent.wishlists FOR ALL USING (user_id = auth.uid());
CREATE POLICY "reviews_select" ON arkevent.reviews FOR SELECT USING (is_visible = true);
CREATE POLICY "reviews_insert" ON arkevent.reviews FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "reviews_update" ON arkevent.reviews FOR UPDATE USING (user_id = auth.uid() OR arkevent.is_admin());
CREATE POLICY "event_shares_insert" ON arkevent.event_shares FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "event_shares_select" ON arkevent.event_shares FOR SELECT USING (true);

-- Notification logs
CREATE POLICY "notif_select_owner" ON arkevent.notification_logs FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "notif_insert_system" ON arkevent.notification_logs FOR INSERT WITH CHECK (true);

-- Autres tables (sélectives)
CREATE POLICY "email_subscribers_admin" ON arkevent.email_subscribers FOR ALL USING (arkevent.is_admin());
CREATE POLICY "push_tokens_owner" ON arkevent.push_tokens FOR ALL USING (user_id = auth.uid());
CREATE POLICY "user_devices_owner" ON arkevent.user_devices FOR ALL USING (user_id = auth.uid());
CREATE POLICY "email_verif_owner" ON arkevent.email_verification_tokens FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "pwd_reset_owner" ON arkevent.password_reset_tokens FOR SELECT USING (user_id = auth.uid());

-- Activity logs
CREATE POLICY "activity_logs_select_user" ON arkevent.activity_logs FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "activity_logs_select_admin" ON arkevent.activity_logs FOR SELECT USING (arkevent.is_admin());

-- Analytics (admin seulement)
CREATE POLICY "analytics_admin" ON arkevent.event_analytics_daily FOR ALL USING (arkevent.is_admin());
CREATE POLICY "event_views_admin" ON arkevent.event_views FOR ALL USING (arkevent.is_admin());

-- Wallet Policies
CREATE POLICY "wallet_select_owner" ON arkevent.wallets FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "wallet_transactions_select_owner" ON arkevent.wallet_transactions FOR SELECT USING (user_id = auth.uid());

-- ============================================
-- 21. Données initiales (catégories)
-- ============================================
INSERT INTO arkevent.event_categories (name, slug, icon) VALUES
    ('Concerts', 'concerts', 'mic'),
    ('Sports', 'sports', 'trophy'),
    ('Festivals', 'festivals', 'star'),
    ('Conférences', 'conferences', 'users'),
    ('Culturel', 'culturel', 'book-open'),
    ('Soirées', 'soirees', 'moon'),
    ('Communautaire', 'communautaire', 'heart')
ON CONFLICT (slug) DO NOTHING;


 1 -- 1. Fonction qui insère un profil dès qu'un user est créé dans auth.users
 CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger AS $$
 BEGIN
   INSERT INTO arkevent.profiles (id, username, first_name, last_name, role)
   VALUES (
  new.id,
     new.raw_user_meta_data->>'username', -- Récupère le username des métadonnées Supabase
     new.raw_user_meta_data->>'first_name',
       new.raw_user_meta_data->>'last_name',
       'user'
   );
   RETURN new;
   END;
   $$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Trigger qui appelle la fonction après chaque INSERT dans auth.users
CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ============================================
-- FIN DU SCRIPT
-- ============================================