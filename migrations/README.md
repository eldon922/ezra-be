# Database Migration System

This directory contains database migration scripts for managing schema changes.

## Usage

### Run all pending migrations:
```bash
python migrate.py
# or
python migrate.py migrate
```

### Check migration status:
```bash
python migrate.py status
```

## Migration Files

- `000_setup_migrations.sql` - Sets up the migrations tracking table
- `002_varchar_to_text.sql` - Converts VARCHAR columns to TEXT

## Creating New Migrations

1. Create a new SQL file with format: `XXX_description.sql` (where XXX is the next version number)
2. Include proper error handling and rollback logic
3. Add migration tracking at the end
4. Test thoroughly before applying to production

## Migration File Template

```sql
-- Migration XXX: Description
-- Version: XXX_migration_name
-- Description: What this migration does

-- Check if migration already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM migrations WHERE version = 'XXX_migration_name') THEN
        RAISE NOTICE 'Migration XXX_migration_name already applied, skipping...';
        RETURN;
    END IF;

    -- Start migration
    RAISE NOTICE 'Applying migration XXX_migration_name...';

    -- Your migration code here
    -- ALTER TABLE ...
    -- CREATE INDEX ...
    -- etc.

    -- Record migration as applied
    INSERT INTO migrations (version, description, checksum) 
    VALUES ('XXX_migration_name', 'Description of changes', MD5('XXX_migration_name_content'));

    RAISE NOTICE 'Migration XXX_migration_name completed successfully.';

EXCEPTION 
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Migration XXX_migration_name failed: %', SQLERRM;
END $$;
```

## Safety Notes

1. Always backup your database before running migrations
2. Test migrations on a copy of production data first
3. Migrations are wrapped in transactions and include error handling
4. The system tracks applied migrations to prevent re-application