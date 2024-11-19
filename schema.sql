-- Create Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Transcriptions table
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    file_name VARCHAR(255),
    original_file_path VARCHAR(255),
    transcription_text TEXT,
    word_document_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create ErrorLogs table
CREATE TABLE error_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    error_message TEXT,
    stack_trace TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

-- Insert an initial admin user (change the username and password as needed)
INSERT INTO users (username, password, is_admin)
VALUES ('admin', 'admin', TRUE);

GRANT ALL ON SCHEMA public TO ezra_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ezra_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ezra_user;