-- HyperTrader Database Schema
-- Version: 2.0 - SQLite
--
-- This file serves as reference documentation for the database schema.
-- The actual schema is created via SQLAlchemy models and bootstrap.py
-- for SQLite deployment.
--
-- Tables:
--   users            - User accounts with local username/password auth
--   traders          - Trader instances (linked to Docker containers)
--   trader_configs   - Versioned configuration for each trader
--   trader_secrets   - Encrypted private keys for traders
--   session_tokens   - JWT session tokens for revocation tracking

-- Users table
-- Stores user accounts with local authentication
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);

-- Traders table
-- Each trader maps to a Docker container
CREATE TABLE traders (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    runtime_name VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    image_tag VARCHAR(100) DEFAULT 'latest',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_traders_user_id ON traders(user_id);
CREATE INDEX idx_traders_status ON traders(status);

-- Trader configs (versioned)
-- Stores JSON configuration with version history
CREATE TABLE trader_configs (
    id VARCHAR(36) PRIMARY KEY,
    trader_id VARCHAR(36) REFERENCES traders(id) ON DELETE CASCADE,
    config_json TEXT NOT NULL,  -- JSON stored as TEXT in SQLite
    version INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trader_id, version)
);

-- Trader secrets
-- Stores encrypted private keys (one per trader)
CREATE TABLE trader_secrets (
    id VARCHAR(36) PRIMARY KEY,
    trader_id VARCHAR(36) UNIQUE REFERENCES traders(id) ON DELETE CASCADE,
    private_key_encrypted TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session tokens
-- Tracks JWT tokens for revocation (logout)
CREATE TABLE session_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_tokens_user_id ON session_tokens(user_id);
CREATE INDEX idx_session_tokens_token_hash ON session_tokens(token_hash);
CREATE INDEX idx_session_tokens_expires_at ON session_tokens(expires_at);
