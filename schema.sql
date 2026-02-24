-- ═══════════════════════════════════════════════════════════════════════════════
-- RESOURCE BOOKING SYSTEM — Complete Database Schema
-- Database : PostgreSQL (Supabase)
-- Generated: 2026-02-21
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── EXTENSIONS ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- for gen_random_uuid() if needed later


-- ═══════════════════════════════════════════════════════════════════════════════
-- ENUMS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TYPE role_name AS ENUM (
    'EMPLOYEE',
    'APPROVER',
    'ADMIN',
    'DRIVER'
);

CREATE TYPE resource_type AS ENUM (
    'VEHICLE',
    'ROOM'
);

CREATE TYPE resource_status AS ENUM (
    'AVAILABLE',
    'MAINTENANCE',
    'INACTIVE'
);

CREATE TYPE booking_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'ONGOING',
    'COMPLETED',
    'CANCELLED',
    'OVERDUE'
);

CREATE TYPE approval_action AS ENUM (
    'APPROVED',
    'REJECTED'
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- MASTER TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── ROLES ────────────────────────────────────────────────────────────────────
CREATE TABLE roles (
    id   SERIAL       PRIMARY KEY,
    name role_name    NOT NULL UNIQUE
);

COMMENT ON TABLE  roles      IS 'User roles for RBAC';
COMMENT ON COLUMN roles.name IS 'EMPLOYEE | APPROVER | ADMIN | DRIVER';


-- ─── DEPARTMENTS ──────────────────────────────────────────────────────────────
CREATE TABLE departments (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE departments IS 'Company departments / divisions';


-- ─── USERS ────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id             SERIAL       PRIMARY KEY,
    "employeeId"   VARCHAR(50)  NOT NULL UNIQUE,
    name           VARCHAR(150) NOT NULL,
    email          VARCHAR(255) NOT NULL UNIQUE,
    password       VARCHAR(255) NOT NULL,
    "isActive"     BOOLEAN      NOT NULL DEFAULT TRUE,
    "roleId"       INTEGER      NOT NULL REFERENCES roles(id),
    "departmentId" INTEGER      NOT NULL REFERENCES departments(id),
    "createdAt"    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    "updatedAt"    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email        ON users(email);
CREATE INDEX idx_users_employee_id  ON users("employeeId");
CREATE INDEX idx_users_role_id      ON users("roleId");
CREATE INDEX idx_users_department_id ON users("departmentId");
CREATE INDEX idx_users_is_active    ON users("isActive");

COMMENT ON TABLE  users              IS 'System users (employees, approvers, admins, drivers)';
COMMENT ON COLUMN users."employeeId" IS 'Unique company employee identifier e.g. EMP001';
COMMENT ON COLUMN users."isActive"   IS 'Soft deactivation flag — false = cannot login';


-- ═══════════════════════════════════════════════════════════════════════════════
-- AUTH MODULE
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── REFRESH TOKENS ───────────────────────────────────────────────────────────
CREATE TABLE refresh_tokens (
    id          SERIAL      PRIMARY KEY,
    "userId"    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT        NOT NULL UNIQUE,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_refresh_tokens_user_id   ON refresh_tokens("userId");
CREATE INDEX idx_refresh_tokens_token     ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_revoked   ON refresh_tokens(revoked);

COMMENT ON TABLE  refresh_tokens          IS 'JWT refresh tokens — one row per active session';
COMMENT ON COLUMN refresh_tokens.revoked  IS 'TRUE = logged out or invalidated';


-- ─── PASSWORD RESET OTPs ──────────────────────────────────────────────────────
CREATE TABLE password_reset_otps (
    id          SERIAL      PRIMARY KEY,
    "userId"    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    "otpCode"   VARCHAR(10) NOT NULL,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "isUsed"    BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_otp_user_id ON password_reset_otps("userId");
CREATE INDEX idx_otp_is_used ON password_reset_otps("isUsed");

COMMENT ON TABLE  password_reset_otps         IS '6-digit OTP codes for password reset flow';
COMMENT ON COLUMN password_reset_otps."isUsed" IS 'TRUE = already consumed, cannot reuse';


-- ═══════════════════════════════════════════════════════════════════════════════
-- RESOURCE ABSTRACTION
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── RESOURCES ────────────────────────────────────────────────────────────────
CREATE TABLE resources (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(200)    NOT NULL,
    type        resource_type   NOT NULL,
    status      resource_status NOT NULL DEFAULT 'AVAILABLE',
    "createdAt" TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resources_type   ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);

COMMENT ON TABLE  resources        IS 'Abstract resource — parent of vehicles and rooms';
COMMENT ON COLUMN resources.type   IS 'VEHICLE or ROOM — determines which child table has detail';
COMMENT ON COLUMN resources.status IS 'AVAILABLE | MAINTENANCE | INACTIVE';


-- ═══════════════════════════════════════════════════════════════════════════════
-- VEHICLE MODULE
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── VEHICLE CATEGORIES ───────────────────────────────────────────────────────
CREATE TABLE vehicle_categories (
    id   SERIAL       PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

COMMENT ON TABLE vehicle_categories IS 'MPV, SUV, Sedan, Pickup, Bus, etc.';


-- ─── VEHICLES ─────────────────────────────────────────────────────────────────
CREATE TABLE vehicles (
    id                SERIAL       PRIMARY KEY,
    "resourceId"      INTEGER      NOT NULL UNIQUE REFERENCES resources(id) ON DELETE CASCADE,
    "plateNumber"     VARCHAR(20)  NOT NULL UNIQUE,
    brand             VARCHAR(100) NOT NULL,
    model             VARCHAR(100) NOT NULL,
    year              SMALLINT     NOT NULL CHECK (year >= 1900 AND year <= 2100),
    "currentOdometer" INTEGER      NOT NULL DEFAULT 0 CHECK ("currentOdometer" >= 0),
    "categoryId"      INTEGER      NOT NULL REFERENCES vehicle_categories(id)
);

CREATE INDEX idx_vehicles_plate_number ON vehicles("plateNumber");
CREATE INDEX idx_vehicles_category_id  ON vehicles("categoryId");

COMMENT ON TABLE  vehicles                  IS 'Vehicle detail — linked 1:1 to a resource row';
COMMENT ON COLUMN vehicles."plateNumber"    IS 'License plate e.g. B 1234 XY';
COMMENT ON COLUMN vehicles."currentOdometer" IS 'Latest known odometer reading (km)';


-- ═══════════════════════════════════════════════════════════════════════════════
-- ROOM MODULE
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── ROOMS ────────────────────────────────────────────────────────────────────
CREATE TABLE rooms (
    id           SERIAL       PRIMARY KEY,
    "resourceId" INTEGER      NOT NULL UNIQUE REFERENCES resources(id) ON DELETE CASCADE,
    location     VARCHAR(255) NOT NULL,
    capacity     SMALLINT     NOT NULL CHECK (capacity > 0)
);

COMMENT ON TABLE  rooms          IS 'Meeting room detail — linked 1:1 to a resource row';
COMMENT ON COLUMN rooms.capacity IS 'Max number of people the room can accommodate';


-- ═══════════════════════════════════════════════════════════════════════════════
-- DRIVER MODULE
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── DRIVERS ──────────────────────────────────────────────────────────────────
CREATE TABLE drivers (
    id              SERIAL       PRIMARY KEY,
    "userId"        INTEGER      NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    "licenseNumber" VARCHAR(100) NOT NULL,
    "phoneNumber"   VARCHAR(20)  NOT NULL,
    "isActive"      BOOLEAN      NOT NULL DEFAULT TRUE,
    "createdAt"     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_drivers_user_id  ON drivers("userId");
CREATE INDEX idx_drivers_is_active ON drivers("isActive");

COMMENT ON TABLE  drivers               IS 'Driver profile — extends a user with DRIVER role';
COMMENT ON COLUMN drivers."isActive"    IS 'FALSE = driver is suspended / unavailable';


-- ═══════════════════════════════════════════════════════════════════════════════
-- BOOKING MODULE
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── BOOKINGS ─────────────────────────────────────────────────────────────────
CREATE TABLE bookings (
    id             SERIAL         PRIMARY KEY,
    "userId"       INTEGER        NOT NULL REFERENCES users(id),
    "resourceId"   INTEGER        NOT NULL REFERENCES resources(id),
    "startDate"    TIMESTAMPTZ    NOT NULL,
    "endDate"      TIMESTAMPTZ    NOT NULL,
    purpose        TEXT           NOT NULL,
    status         booking_status NOT NULL DEFAULT 'PENDING',
    "approvedById" INTEGER        REFERENCES users(id),
    "approvedAt"   TIMESTAMPTZ,
    "returnedAt"   TIMESTAMPTZ,
    "createdAt"    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    "updatedAt"    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    -- Business rules enforced at DB level
    CONSTRAINT chk_booking_dates    CHECK ("endDate" > "startDate"),
    CONSTRAINT chk_approved_by_set  CHECK (
        (status IN ('APPROVED','REJECTED') AND "approvedById" IS NOT NULL)
        OR status NOT IN ('APPROVED','REJECTED')
    )
);

CREATE INDEX idx_bookings_user_id      ON bookings("userId");
CREATE INDEX idx_bookings_resource_id  ON bookings("resourceId");
CREATE INDEX idx_bookings_status       ON bookings(status);
CREATE INDEX idx_bookings_start_date   ON bookings("startDate");
CREATE INDEX idx_bookings_end_date     ON bookings("endDate");
CREATE INDEX idx_bookings_approved_by  ON bookings("approvedById");

-- Partial index: fast lookup of active bookings (used in conflict detection)
CREATE INDEX idx_bookings_active ON bookings("resourceId", "startDate", "endDate")
    WHERE status IN ('PENDING', 'APPROVED', 'ONGOING');

COMMENT ON TABLE  bookings              IS 'Resource booking requests and their lifecycle';
COMMENT ON COLUMN bookings.purpose      IS 'User-provided reason for booking';
COMMENT ON COLUMN bookings."returnedAt" IS 'Actual return timestamp — set when COMPLETED';


-- ─── APPROVAL LOGS ────────────────────────────────────────────────────────────
CREATE TABLE approval_logs (
    id           SERIAL          PRIMARY KEY,
    "bookingId"  INTEGER         NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    "approverId" INTEGER         NOT NULL REFERENCES users(id),
    action       approval_action NOT NULL,
    note         TEXT,
    "createdAt"  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_logs_booking_id  ON approval_logs("bookingId");
CREATE INDEX idx_approval_logs_approver_id ON approval_logs("approverId");

COMMENT ON TABLE approval_logs IS 'History of every approve/reject action on a booking';


-- ═══════════════════════════════════════════════════════════════════════════════
-- DRIVER ASSIGNMENT (History)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE driver_assignments (
    id           SERIAL      PRIMARY KEY,
    "driverId"   INTEGER     NOT NULL REFERENCES drivers(id),
    "vehicleId"  INTEGER     NOT NULL REFERENCES vehicles(id),
    "assignedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "releasedAt" TIMESTAMPTZ             -- NULL = currently assigned
);

CREATE INDEX idx_driver_assignments_driver_id  ON driver_assignments("driverId");
CREATE INDEX idx_driver_assignments_vehicle_id ON driver_assignments("vehicleId");

-- Partial unique: only one active assignment per driver and per vehicle at a time
CREATE UNIQUE INDEX idx_driver_assignments_active_driver
    ON driver_assignments("driverId") WHERE "releasedAt" IS NULL;

CREATE UNIQUE INDEX idx_driver_assignments_active_vehicle
    ON driver_assignments("vehicleId") WHERE "releasedAt" IS NULL;

COMMENT ON TABLE  driver_assignments              IS 'History of driver-to-vehicle assignments';
COMMENT ON COLUMN driver_assignments."releasedAt" IS 'NULL = assignment still active';


-- ═══════════════════════════════════════════════════════════════════════════════
-- FUEL EXPENSE
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE fuel_expenses (
    id              SERIAL         PRIMARY KEY,
    "driverId"      INTEGER        NOT NULL REFERENCES drivers(id),
    "vehicleId"     INTEGER        NOT NULL REFERENCES vehicles(id),
    "bookingId"     INTEGER        REFERENCES bookings(id),   -- optional
    liter           NUMERIC(10,2)  NOT NULL CHECK (liter > 0),
    "pricePerLiter" NUMERIC(12,2)  NOT NULL CHECK ("pricePerLiter" > 0),
    "totalAmount"   NUMERIC(14,2)  NOT NULL CHECK ("totalAmount" > 0),
    "odometerBefore" INTEGER       NOT NULL CHECK ("odometerBefore" >= 0),
    "odometerAfter"  INTEGER       NOT NULL CHECK ("odometerAfter" > "odometerBefore"),
    note            TEXT,
    "createdAt"     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fuel_expenses_driver_id  ON fuel_expenses("driverId");
CREATE INDEX idx_fuel_expenses_vehicle_id ON fuel_expenses("vehicleId");
CREATE INDEX idx_fuel_expenses_booking_id ON fuel_expenses("bookingId");
CREATE INDEX idx_fuel_expenses_created_at ON fuel_expenses("createdAt");

COMMENT ON TABLE  fuel_expenses               IS 'Fuel fill-up records submitted by drivers';
COMMENT ON COLUMN fuel_expenses."totalAmount" IS 'Auto-calculated: liter * pricePerLiter';
COMMENT ON COLUMN fuel_expenses."odometerAfter" IS 'Must be greater than odometerBefore';


-- ═══════════════════════════════════════════════════════════════════════════════
-- MAINTENANCE RECORDS (Polymorphic via Resource)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE maintenance_records (
    id            SERIAL        PRIMARY KEY,
    "resourceId"  INTEGER       NOT NULL REFERENCES resources(id),
    description   TEXT          NOT NULL,
    "startDate"   TIMESTAMPTZ   NOT NULL,
    "endDate"     TIMESTAMPTZ,                  -- NULL = maintenance ongoing
    cost          NUMERIC(12,2) CHECK (cost >= 0),
    "createdById" INTEGER       NOT NULL REFERENCES users(id),
    "createdAt"   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_maintenance_dates CHECK (
        "endDate" IS NULL OR "endDate" > "startDate"
    )
);

CREATE INDEX idx_maintenance_resource_id   ON maintenance_records("resourceId");
CREATE INDEX idx_maintenance_created_by_id ON maintenance_records("createdById");
CREATE INDEX idx_maintenance_start_date    ON maintenance_records("startDate");

COMMENT ON TABLE  maintenance_records          IS 'Maintenance / service records for any resource';
COMMENT ON COLUMN maintenance_records."endDate" IS 'NULL = resource still under maintenance';


-- ═══════════════════════════════════════════════════════════════════════════════
-- AUDIT LOG
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE audit_logs (
    id           SERIAL       PRIMARY KEY,
    "userId"     INTEGER      REFERENCES users(id),   -- NULL = system action
    action       VARCHAR(100) NOT NULL,               -- CREATE, UPDATE, DELETE, APPROVE, etc.
    "entityType" VARCHAR(100) NOT NULL,               -- Booking, User, Vehicle, etc.
    "entityId"   INTEGER,
    description  TEXT,
    "createdAt"  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id     ON audit_logs("userId");
CREATE INDEX idx_audit_logs_entity_type ON audit_logs("entityType");
CREATE INDEX idx_audit_logs_entity_id   ON audit_logs("entityId");
CREATE INDEX idx_audit_logs_action      ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at  ON audit_logs("createdAt");

COMMENT ON TABLE  audit_logs             IS 'Immutable log of all significant user actions';
COMMENT ON COLUMN audit_logs."userId"    IS 'NULL when action is triggered by system/scheduler';
COMMENT ON COLUMN audit_logs.action      IS 'Verb: CREATE | UPDATE | DELETE | APPROVE | REJECT | LOGIN | LOGOUT';
COMMENT ON COLUMN audit_logs."entityType" IS 'Model name: Booking | User | Vehicle | Room | Driver';


-- ═══════════════════════════════════════════════════════════════════════════════
-- TRIGGERS — auto-update "updatedAt" columns
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updatedAt" = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_resources
    BEFORE UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER set_updated_at_bookings
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- ═══════════════════════════════════════════════════════════════════════════════
-- SEED DATA
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Roles ────────────────────────────────────────────────────────────────────
INSERT INTO roles (name) VALUES
    ('EMPLOYEE'),
    ('APPROVER'),
    ('ADMIN'),
    ('DRIVER');

-- ─── Departments ──────────────────────────────────────────────────────────────
INSERT INTO departments (name) VALUES
    ('Information Technology'),
    ('Human Resources'),
    ('Finance & Accounting'),
    ('Operations'),
    ('Marketing');

-- ─── Users ────────────────────────────────────────────────────────────────────
-- Passwords are bcrypt hashes of "Password123!"
-- Hash generated with: passlib.hash.bcrypt.hash("Password123!")
INSERT INTO users ("employeeId", name, email, password, "isActive", "roleId", "departmentId") VALUES
    ('ADM001', 'Admin Utama',    'admin@company.com',         'admin', TRUE, 3, 1),
    ('APR001', 'Siti Rahayu',    'siti.rahayu@company.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 2, 2),
    ('APR002', 'Budi Prasetyo',  'budi.prasetyo@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 2, 4),
    ('EMP001', 'John Doe',       'john.doe@company.com',      '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 1, 1),
    ('EMP002', 'Jane Smith',     'jane.smith@company.com',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 1, 3),
    ('EMP003', 'Dewi Lestari',   'dewi.lestari@company.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 1, 5),
    ('EMP004', 'Reza Firmansyah','reza.firmansyah@company.com','$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 1, 4),
    ('DRV001', 'Pak Supir Satu', 'supir1@company.com',        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 4, 4),
    ('DRV002', 'Pak Supir Dua',  'supir2@company.com',        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYQkGDsQtW', TRUE, 4, 4);

-- ─── Vehicle Categories ───────────────────────────────────────────────────────
INSERT INTO vehicle_categories (name) VALUES
    ('MPV'),
    ('SUV'),
    ('Sedan'),
    ('Pickup'),
    ('Bus / Minibus');

-- ─── Resources (Vehicles) ─────────────────────────────────────────────────────
INSERT INTO resources (name, type, status) VALUES
    ('Toyota Avanza - B 1234 XY',   'VEHICLE', 'AVAILABLE'),    -- id 1
    ('Honda CR-V - B 5678 AB',       'VEHICLE', 'AVAILABLE'),    -- id 2
    ('Toyota Fortuner - B 9999 CD',  'VEHICLE', 'AVAILABLE'),    -- id 3
    ('Mitsubishi L300 - B 2222 EF',  'VEHICLE', 'MAINTENANCE'),  -- id 4
    ('Daihatsu Xenia - B 3333 GH',   'VEHICLE', 'AVAILABLE'),    -- id 5
    ('Toyota HiAce - B 4444 IJ',     'VEHICLE', 'INACTIVE');     -- id 6

-- ─── Vehicles ─────────────────────────────────────────────────────────────────
INSERT INTO vehicles ("resourceId", "plateNumber", brand, model, year, "currentOdometer", "categoryId") VALUES
    (1, 'B 1234 XY', 'Toyota',     'Avanza',    2022, 15000, 1),
    (2, 'B 5678 AB', 'Honda',      'CR-V',      2021, 28500, 2),
    (3, 'B 9999 CD', 'Toyota',     'Fortuner',  2023,  5200, 2),
    (4, 'B 2222 EF', 'Mitsubishi', 'L300',      2020, 72000, 4),
    (5, 'B 3333 GH', 'Daihatsu',   'Xenia',     2022, 18300, 1),
    (6, 'B 4444 IJ', 'Toyota',     'HiAce',     2019, 95000, 5);

-- ─── Resources (Rooms) ────────────────────────────────────────────────────────
INSERT INTO resources (name, type, status) VALUES
    ('Meeting Room A - Lt.2',   'ROOM', 'AVAILABLE'),   -- id 7
    ('Meeting Room B - Lt.3',   'ROOM', 'AVAILABLE'),   -- id 8
    ('Board Room - Lt.5',        'ROOM', 'AVAILABLE'),   -- id 9
    ('Training Room - Annex Lt.1','ROOM','INACTIVE');    -- id 10

-- ─── Rooms ────────────────────────────────────────────────────────────────────
INSERT INTO rooms ("resourceId", location, capacity) VALUES
    (7,  'Gedung Utama Lt. 2',  10),
    (8,  'Gedung Utama Lt. 3',  20),
    (9,  'Gedung Utama Lt. 5',  50),
    (10, 'Gedung Annex Lt. 1',  30);

-- ─── Drivers ──────────────────────────────────────────────────────────────────
-- userId 8 = DRV001, userId 9 = DRV002
INSERT INTO drivers ("userId", "licenseNumber", "phoneNumber", "isActive") VALUES
    (8, 'SIM-B1-2024-001', '+6281234567890', TRUE),
    (9, 'SIM-B1-2024-002', '+6287654321098', TRUE);

-- ─── Driver Assignments ───────────────────────────────────────────────────────
-- Driver 1 assigned to Avanza (vehicleId 1), Driver 2 assigned to CR-V (vehicleId 2)
INSERT INTO driver_assignments ("driverId", "vehicleId", "assignedAt") VALUES
    (1, 1, NOW() - INTERVAL '30 days'),
    (2, 2, NOW() - INTERVAL '15 days');

-- ─── Bookings ─────────────────────────────────────────────────────────────────
INSERT INTO bookings ("userId", "resourceId", "startDate", "endDate", purpose, status, "approvedById", "approvedAt", "returnedAt") VALUES
    -- Completed booking (vehicle)
    (4, 1,
     NOW() - INTERVAL '10 days',
     NOW() - INTERVAL '9 days',
     'Kunjungan klien ke site proyek',
     'COMPLETED', 2, NOW() - INTERVAL '11 days', NOW() - INTERVAL '9 days'),

    -- Approved booking (room) - upcoming
    (5, 8,
     NOW() + INTERVAL '2 days',
     NOW() + INTERVAL '2 days' + INTERVAL '3 hours',
     'Rapat koordinasi tim Finance Q1',
     'APPROVED', 2, NOW() - INTERVAL '1 day', NULL),

    -- Pending booking (vehicle)
    (4, 3,
     NOW() + INTERVAL '5 days',
     NOW() + INTERVAL '6 days',
     'Perjalanan dinas ke Bandung',
     'PENDING', NULL, NULL, NULL),

    -- Pending booking (room)
    (6, 9,
     NOW() + INTERVAL '3 days',
     NOW() + INTERVAL '3 days' + INTERVAL '4 hours',
     'Presentasi Marketing Campaign Q2',
     'PENDING', NULL, NULL, NULL),

    -- Rejected booking
    (7, 1,
     NOW() - INTERVAL '5 days',
     NOW() - INTERVAL '4 days',
     'Acara keluarga (bukan keperluan kantor)',
     'REJECTED', 2, NOW() - INTERVAL '6 days', NULL),

    -- Ongoing booking
    (4, 5,
     NOW() - INTERVAL '1 hour',
     NOW() + INTERVAL '6 hours',
     'Antar dokumen ke kantor pusat',
     'ONGOING', 3, NOW() - INTERVAL '2 days', NULL),

    -- Overdue booking
    (7, 2,
     NOW() - INTERVAL '3 days',
     NOW() - INTERVAL '1 day',
     'Perjalanan survey lokasi',
     'OVERDUE', 2, NOW() - INTERVAL '4 days', NULL),

    -- Cancelled booking
    (5, 7,
     NOW() + INTERVAL '1 day',
     NOW() + INTERVAL '1 day' + INTERVAL '2 hours',
     'Meeting yang dibatalkan',
     'CANCELLED', NULL, NULL, NULL);

-- ─── Approval Logs ────────────────────────────────────────────────────────────
INSERT INTO approval_logs ("bookingId", "approverId", action, note) VALUES
    (1, 2, 'APPROVED', 'Disetujui — keperluan klien prioritas'),
    (2, 2, 'APPROVED', 'OK, silakan'),
    (5, 2, 'REJECTED', 'Booking untuk keperluan pribadi tidak diizinkan'),
    (7, 2, 'APPROVED', 'Disetujui untuk survey lokasi proyek');

-- ─── Fuel Expenses ────────────────────────────────────────────────────────────
INSERT INTO fuel_expenses ("driverId", "vehicleId", "bookingId", liter, "pricePerLiter", "totalAmount", "odometerBefore", "odometerAfter", note) VALUES
    (1, 1, 1, 40.50, 10000.00, 405000.00, 14600, 15000, 'SPBU Pertamina Jl. Sudirman'),
    (1, 1, 6, 35.00, 10000.00, 350000.00, 15000, 15320, 'SPBU Shell Jl. Gatot Subroto'),
    (2, 2, NULL, 50.00, 10200.00, 510000.00, 28000, 28500, 'SPBU Pertamina Bekasi');

-- ─── Maintenance Records ──────────────────────────────────────────────────────
INSERT INTO maintenance_records ("resourceId", description, "startDate", "endDate", cost, "createdById") VALUES
    (4, 'Ganti oli mesin, filter oli, dan filter udara — servis berkala 70.000 km',
     NOW() - INTERVAL '2 days', NULL, 850000.00, 1),

    (1, 'Ganti ban depan 2 buah — ban aus',
     NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days' + INTERVAL '4 hours',
     1200000.00, 1),

    (9, 'Perbaikan AC — kompresor bermasalah',
     NOW() - INTERVAL '7 days', NOW() - INTERVAL '5 days',
     2500000.00, 1);

-- ─── Audit Logs ───────────────────────────────────────────────────────────────
INSERT INTO audit_logs ("userId", action, "entityType", "entityId", description) VALUES
    (1, 'CREATE', 'User',    4, 'Admin created user John Doe (EMP001)'),
    (1, 'CREATE', 'Vehicle', 1, 'Admin registered vehicle Toyota Avanza B 1234 XY'),
    (1, 'CREATE', 'Room',    1, 'Admin registered Meeting Room A Lt.2'),
    (2, 'APPROVE','Booking', 1, 'Booking #1 approved for John Doe (Avanza, site visit)'),
    (2, 'REJECT', 'Booking', 5, 'Booking #5 rejected — personal use not permitted'),
    (4, 'CREATE', 'Booking', 3, 'John Doe created booking #3 for Fortuner to Bandung'),
    (1, 'CREATE', 'MaintenanceRecord', 1, 'Maintenance started for L300 (oil change)');


-- ═══════════════════════════════════════════════════════════════════════════════
-- USEFUL VIEWS (optional — for reporting queries)
-- ═══════════════════════════════════════════════════════════════════════════════

-- Active bookings with resource and user info
CREATE OR REPLACE VIEW v_active_bookings AS
SELECT
    b.id              AS booking_id,
    b.status,
    b."startDate",
    b."endDate",
    b.purpose,
    u.name            AS user_name,
    u."employeeId",
    d.name            AS department,
    r.name            AS resource_name,
    r.type            AS resource_type,
    r.status          AS resource_status
FROM bookings b
JOIN users      u ON u.id = b."userId"
JOIN departments d ON d.id = u."departmentId"
JOIN resources  r ON r.id = b."resourceId"
WHERE b.status IN ('PENDING','APPROVED','ONGOING');

-- Vehicle utilization summary
CREATE OR REPLACE VIEW v_vehicle_summary AS
SELECT
    v.id,
    r.name            AS vehicle_name,
    v."plateNumber",
    vc.name           AS category,
    r.status,
    v."currentOdometer",
    COUNT(b.id)       AS total_bookings,
    SUM(CASE WHEN b.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_bookings,
    COALESCE(SUM(fe."totalAmount"), 0) AS total_fuel_cost
FROM vehicles v
JOIN resources          r  ON r.id  = v."resourceId"
JOIN vehicle_categories vc ON vc.id = v."categoryId"
LEFT JOIN bookings      b  ON b."resourceId" = r.id
LEFT JOIN fuel_expenses fe ON fe."vehicleId" = v.id
GROUP BY v.id, r.name, v."plateNumber", vc.name, r.status, v."currentOdometer";


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