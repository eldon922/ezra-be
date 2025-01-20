CREATE USER ezra_user WITH PASSWORD '[PASSWORD]' CREATEDB;
ALTER USER ezra_user WITH PASSWORD '[PASSWORD]';

SET ROLE ezra_user;

---------------------------------------------------------------------------------------------------

CREATE DATABASE ezra_be OWNER ezra_user;

---------------------------------------------------------------------------------------------------

-- Create Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- First, ensure the uuid-ossp extension is enabled (if not already done)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create Transcriptions table with UUID
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id),
    audio_file_path VARCHAR(255),
    google_drive_url VARCHAR(255),
    txt_document_path VARCHAR(255),
    md_document_path VARCHAR(255),
    word_document_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create ErrorLogs table
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    transcription_id UUID REFERENCES transcriptions(id),
    error_message TEXT,
    stack_trace TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create TranscribePrompts table
CREATE TABLE transcribe_prompts (
    id SERIAL PRIMARY KEY,
    version VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create ProofreadPrompts table
CREATE TABLE proofread_prompts (
    id SERIAL PRIMARY KEY,
    version VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create SystemSettings table
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on transcribe_prompts table for faster version lookups
CREATE INDEX idx_transcribe_prompts_version ON transcribe_prompts(version);

-- Create index on proofread_prompts table for faster version lookups
CREATE INDEX idx_proofread_prompts_version ON proofread_prompts(version);

-- Create index on users table for faster lookups
CREATE INDEX idx_users_username ON users(username);

-- Create index on transcriptions table for faster user-specific queries
CREATE INDEX idx_transcriptions_user_id ON transcriptions(user_id);

-- Create index on error_logs table for faster user-specific queries
CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);

-- Create a function to update the 'updated_at' column
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to automatically update the 'updated_at' column in the transcriptions table
CREATE TRIGGER update_transcriptions_modtime
BEFORE UPDATE ON transcriptions
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Create a trigger to automatically update the 'updated_at' column in the system_settings table
CREATE TRIGGER update_system_settings_modtime
BEFORE UPDATE ON system_settings
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

---------------------------------------------------------------------------------------------------

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ezra_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ezra_user;

GRANT ALL ON SCHEMA public TO ezra_user;

---------------------------------------------------------------------------------------------------

-- Insert an initial admin user (change the username and password as needed)
INSERT INTO users (username, password, is_admin)
VALUES ('admin', 'scrypt:32768:8:1$Kp4H6ecI5RX33V91$f52fcf74b6ca0c0ba5c983d2ee0a8d23f5bd76f7963bbab210aeea9d4c973bf57af5ee8f3d78b555d5cd157d5af21d095793a17f3d8b2065511149bde23d957b', TRUE);

-- Insert initial transcribe prompt
INSERT INTO transcribe_prompts (version, prompt)
VALUES ('EMPTY', '');

-- Insert initial proofread prompt
INSERT INTO proofread_prompts (version, prompt)
VALUES ('EMPTY', '');

-- Insert initial transcribe settings
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES ('active_transcribe_prompt_id', '1', 'The ID of the currently active transcribe prompt');

-- Insert initial system settings
INSERT INTO system_settings (setting_key, setting_value, description)
VALUES ('active_proofread_prompt_id', '1', 'The ID of the currently active proofread prompt');
