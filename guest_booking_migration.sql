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


-- ═══════════════════════════════════════════════════════════════
-- MIGRATION: Attachments + Profile Photo
-- Jalankan di pgAdmin setelah schema_fixed.sql
-- ═══════════════════════════════════════════════════════════════

-- 1. Kolom foto profil user
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS "profilePhoto" VARCHAR(500) NULL;

-- 2. Tabel attachments
DROP TABLE IF EXISTS attachments CASCADE;
CREATE TABLE attachments (
    id             SERIAL        PRIMARY KEY,
    "uploadedById" INTEGER       NOT NULL REFERENCES users(id),
    "vehicleId"    INTEGER       REFERENCES vehicles(id)  ON DELETE CASCADE,
    "roomId"       INTEGER       REFERENCES rooms(id)     ON DELETE CASCADE,
    "bookingId"    INTEGER       REFERENCES bookings(id)  ON DELETE CASCADE,
    "fileUrl"      VARCHAR(500)  NOT NULL,
    "fileName"     VARCHAR(255)  NOT NULL,
    "fileType"     VARCHAR(100)  NOT NULL,
    "fileSize"     INTEGER       NULL,
    description    TEXT          NULL,
    "createdAt"    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_one_target CHECK (
        (CASE WHEN "vehicleId"  IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN "roomId"     IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN "bookingId"  IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
);

CREATE INDEX idx_att_vehicle  ON attachments("vehicleId");
CREATE INDEX idx_att_room     ON attachments("roomId");
CREATE INDEX idx_att_booking  ON attachments("bookingId");
CREATE INDEX idx_att_uploader ON attachments("uploadedById");

-- Verifikasi
SELECT 'attachments table created' AS status, count(*) AS cols
FROM information_schema.columns WHERE table_name = 'attachments';
SELECT 'profilePhoto column added' AS status
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'profilePhoto';