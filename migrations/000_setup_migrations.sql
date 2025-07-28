-- Migration system setup
-- This creates a migrations table to track applied migrations

-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64) -- For integrity checking
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_migrations_version ON migrations(version);

-- Insert initial migration record (assuming your current schema is baseline)
INSERT INTO migrations (version, description, checksum) 
VALUES ('001_initial_schema', 'Initial database schema with VARCHAR columns', 'baseline')
ON CONFLICT (version) DO NOTHING;