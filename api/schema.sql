-- HyperTrader Database Schema
-- Version: 1.0
-- Created: Phase 1 - Foundation Layer
--
-- This file serves as reference documentation for the database schema.
-- The actual schema is applied via Kubernetes ConfigMap (postgres-init-scripts)
-- during PostgreSQL initialization.
--
-- Tables:
--   users          - User accounts and API credentials
--   traders        - Trader instances (linked to K8s deployments)
--   trader_configs - Versioned configuration for each trader
--   trader_secrets - Encrypted private keys for traders
--   deployments    - Deployment history and status tracking
--   usage_metrics  - Resource usage for billing/analytics

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
-- Stores user accounts with API key authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash VARCHAR(255),
    password_hash VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    plan_tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Traders table
-- Each trader maps to a Kubernetes StatefulSet
CREATE TABLE IF NOT EXISTS traders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    k8s_name VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    image_tag VARCHAR(100) DEFAULT 'latest',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trader configs (versioned)
-- Stores JSON configuration with version history
CREATE TABLE IF NOT EXISTS trader_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    config_json JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(trader_id, version)
);

-- Trader secrets (encrypted private keys)
-- One-to-one relationship with traders
CREATE TABLE IF NOT EXISTS trader_secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID UNIQUE REFERENCES traders(id) ON DELETE CASCADE,
    encrypted_private_key TEXT NOT NULL,
    encryption_key_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Deployment history
-- Tracks all deployments for audit and rollback
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    image_tag VARCHAR(100),
    status VARCHAR(50),
    k8s_metadata JSONB,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Usage metrics
-- Time-series data for billing and analytics
CREATE TABLE IF NOT EXISTS usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metric_type VARCHAR(50),
    value NUMERIC,
    metadata JSONB
);

-- Refresh tokens for JWT authentication
-- Stores refresh tokens for revocation support and session management
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_traders_user_id ON traders(user_id);
CREATE INDEX IF NOT EXISTS idx_traders_status ON traders(status);
CREATE INDEX IF NOT EXISTS idx_deployments_trader_id ON deployments(trader_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_trader_id ON usage_metrics(trader_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_timestamp ON usage_metrics(timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_traders_updated_at ON traders;
CREATE TRIGGER update_traders_updated_at
    BEFORE UPDATE ON traders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_trader_secrets_updated_at ON trader_secrets;
CREATE TRIGGER update_trader_secrets_updated_at
    BEFORE UPDATE ON trader_secrets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
