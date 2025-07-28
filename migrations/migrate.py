#!/usr/bin/env python3
"""
Database Migration Runner
Applies database migrations in order and tracks them.
"""

import os
import sys
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class MigrationRunner:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.migrations_dir = os.path.join(os.path.dirname(__file__))
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def setup_migrations_table(self):
        """Setup migrations tracking table"""
        setup_file = os.path.join(self.migrations_dir, '000_setup_migrations.sql')
        if os.path.exists(setup_file):
            with open(setup_file, 'r') as f:
                setup_sql = f.read()
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(setup_sql)
                conn.commit()
            print("✓ Migrations table setup completed")
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT version FROM migrations ORDER BY version")
                return [row['version'] for row in cursor.fetchall()]
    
    def get_pending_migrations(self):
        """Get list of pending migrations"""
        applied = set(self.get_applied_migrations())
        
        migration_files = []
        for filename in os.listdir(self.migrations_dir):
            if filename.endswith('.sql') and not filename.startswith('000_'):
                migration_files.append(filename)
        
        migration_files.sort()
        
        pending = []
        for filename in migration_files:
            version = filename.replace('.sql', '')
            if version not in applied:
                pending.append(filename)
        
        return pending
    
    def calculate_checksum(self, content):
        """Calculate MD5 checksum of migration content"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def apply_migration(self, filename):
        """Apply a single migration"""
        filepath = os.path.join(self.migrations_dir, filename)
        version = filename.replace('.sql', '')
        
        with open(filepath, 'r') as f:
            migration_sql = f.read()
        
        print(f"Applying migration: {version}")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(migration_sql)
                conn.commit()
            print(f"✓ Migration {version} applied successfully")
            return True
        except Exception as e:
            print(f"✗ Migration {version} failed: {str(e)}")
            return False
    
    def run_migrations(self):
        """Run all pending migrations"""
        print("Starting database migrations...")
        
        # Setup migrations table first
        self.setup_migrations_table()
        
        # Get pending migrations
        pending = self.get_pending_migrations()
        
        if not pending:
            print("✓ No pending migrations found")
            return True
        
        print(f"Found {len(pending)} pending migrations:")
        for migration in pending:
            print(f"  - {migration}")
        
        # Apply each migration
        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                print(f"✗ Migration failed, stopping at {migration}")
                break
        
        if success_count == len(pending):
            print(f"✓ All {success_count} migrations applied successfully!")
            return True
        else:
            print(f"✗ {success_count}/{len(pending)} migrations applied")
            return False
    
    def status(self):
        """Show migration status"""
        try:
            self.setup_migrations_table()
            applied = self.get_applied_migrations()
            pending = self.get_pending_migrations()
            
            print("Migration Status:")
            print(f"  Applied: {len(applied)}")
            for migration in applied:
                print(f"    ✓ {migration}")
            
            print(f"  Pending: {len(pending)}")
            for migration in pending:
                print(f"    ○ {migration}")
                
        except Exception as e:
            print(f"Error checking migration status: {e}")

def main():
    runner = MigrationRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'status':
            runner.status()
        elif command == 'migrate':
            runner.run_migrations()
        else:
            print("Usage: python migrate.py [status|migrate]")
    else:
        runner.run_migrations()

if __name__ == '__main__':
    main()