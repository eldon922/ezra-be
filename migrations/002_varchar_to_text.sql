-- Migration 002: Convert VARCHAR columns to TEXT
-- Version: 002_varchar_to_text
-- Description: Convert all VARCHAR columns to TEXT to support unlimited length strings

-- Check if migration already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM migrations WHERE version = '002_varchar_to_text') THEN
        RAISE NOTICE 'Migration 002_varchar_to_text already applied, skipping...';
        RETURN;
    END IF;

    -- Start migration
    RAISE NOTICE 'Applying migration 002_varchar_to_text...';

    -- Migrate users table
    ALTER TABLE users ALTER COLUMN username TYPE TEXT;
    ALTER TABLE users ALTER COLUMN password TYPE TEXT;

    -- Migrate transcriptions table
    ALTER TABLE transcriptions ALTER COLUMN audio_file_path TYPE TEXT;
    ALTER TABLE transcriptions ALTER COLUMN google_drive_url TYPE TEXT;
    ALTER TABLE transcriptions ALTER COLUMN txt_document_path TYPE TEXT;
    ALTER TABLE transcriptions ALTER COLUMN md_document_path TYPE TEXT;
    ALTER TABLE transcriptions ALTER COLUMN word_document_path TYPE TEXT;
    ALTER TABLE transcriptions ALTER COLUMN status TYPE TEXT;

    -- Migrate transcribe_prompts table
    ALTER TABLE transcribe_prompts ALTER COLUMN version TYPE TEXT;

    -- Migrate proofread_prompts table
    ALTER TABLE proofread_prompts ALTER COLUMN version TYPE TEXT;

    -- Migrate system_settings table
    ALTER TABLE system_settings ALTER COLUMN setting_key TYPE TEXT;

    -- Record migration as applied
    INSERT INTO migrations (version, description, checksum) 
    VALUES ('002_varchar_to_text', 'Convert VARCHAR columns to TEXT for unlimited length support', MD5('002_varchar_to_text_content'));

    RAISE NOTICE 'Migration 002_varchar_to_text completed successfully.';

EXCEPTION 
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration 002_varchar_to_text failed: %', SQLERRM;
END $$;