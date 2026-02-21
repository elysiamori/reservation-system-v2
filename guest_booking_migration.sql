-- ═══════════════════════════════════════════════════════════════════════════════
-- GUEST BOOKING MIGRATION
-- Jalankan di pgAdmin SETELAH schema_fixed.sql
-- ═══════════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS guest_bookings CASCADE;

CREATE TABLE guest_bookings (
    id               SERIAL         PRIMARY KEY,
    "guestName"      VARCHAR(150)   NOT NULL,
    "guestEmail"     VARCHAR(255)   NOT NULL,
    "guestPhone"     VARCHAR(20)    NOT NULL,
    "departmentName" VARCHAR(100)   NOT NULL,
    "resourceId"     INTEGER        NOT NULL REFERENCES resources(id),
    "startDate"      TIMESTAMPTZ    NOT NULL,
    "endDate"        TIMESTAMPTZ    NOT NULL,
    purpose          TEXT           NOT NULL,
    status           booking_status NOT NULL DEFAULT 'PENDING',
    "accessToken"    VARCHAR(64)    NOT NULL UNIQUE,
    "approvedById"   INTEGER        REFERENCES users(id),
    "approvedAt"     TIMESTAMPTZ,
    "rejectionNote"  TEXT,
    "returnedAt"     TIMESTAMPTZ,
    "createdAt"      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    "updatedAt"      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_guest_dates CHECK ("endDate" > "startDate")
);

CREATE INDEX idx_guest_bookings_token       ON guest_bookings("accessToken");
CREATE INDEX idx_guest_bookings_email       ON guest_bookings("guestEmail");
CREATE INDEX idx_guest_bookings_status      ON guest_bookings(status);
CREATE INDEX idx_guest_bookings_resource_id ON guest_bookings("resourceId");

CREATE TRIGGER set_updated_at_guest_bookings
    BEFORE UPDATE ON guest_bookings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
