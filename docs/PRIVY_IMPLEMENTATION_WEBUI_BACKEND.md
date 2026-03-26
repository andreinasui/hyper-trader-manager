# Privy Integration: Web UI + Backend Implementation Guide

**Document Version:** 1.0  
**Last Updated:** February 3, 2026  
**Architecture:** Agent Wallet Pattern

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Privy Account Setup](#phase-1-privy-account-setup)
5. [Phase 2: Frontend Implementation (React)](#phase-2-frontend-implementation-react)
6. [Phase 3: Backend Implementation (FastAPI)](#phase-3-backend-implementation-fastapi)
7. [Phase 4: Database Migrations](#phase-4-database-migrations)
8. [Phase 5: Testing](#phase-5-testing)
9. [Phase 6: Deployment](#phase-6-deployment)
10. [Security Considerations](#security-considerations)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This document guides you through integrating **Privy wallet authentication** into the Hyper-Trader web application and FastAPI backend using the **Agent Wallet Pattern**.

### What We're Building

- **User Authentication:** Users connect via MetaMask/Rabby using Privy's embedded wallets
- **Agent Creation:** Backend generates local agent wallets approved by user's Privy wallet
- **Secure Trading:** Rust trader uses local agent keys (not calling Privy on every trade)
- **Key Rotation:** Daily automatic rotation of agent keys for security

### Authentication Flow

```
User → Connect Wallet (Privy) → 
Frontend receives access token → 
Backend verifies token → 
Creates/retrieves user → 
Returns JWT for API access
```

### Agent Creation Flow

```
User creates trader → 
Backend generates agent wallet locally → 
Backend calls Privy RPC API to sign approveAgent → 
Submit to Hyperliquid → 
Deploy Rust pod with agent key
```

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  - Privy SDK for wallet connection                              │
│  - User authentication UI                                       │
│  - Trader management dashboard                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTPS + JWT
┌────────────────────▼────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  - Privy token verification                                     │
│  - Agent wallet generation                                      │
│  - Privy RPC signing for agent approval                         │
│  - K8s deployment orchestration                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ K8s API
┌────────────────────▼────────────────────────────────────────────┐
│                   RUST TRADER POD                                │
│  - Local agent wallet (PrivateKeySigner)                        │
│  - Trades on behalf of master wallet                            │
│  - NO Privy API calls during trading                            │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow

| Step | Component | Action | Data |
|------|-----------|--------|------|
| 1 | Frontend | User connects wallet | Privy access token |
| 2 | Backend | Verify token, create user | User DB record |
| 3 | Backend | Generate agent wallet | Agent private key |
| 4 | Backend | Sign approveAgent via Privy RPC | Signature |
| 5 | Backend | Submit to Hyperliquid | Agent approval |
| 6 | Backend | Deploy K8s pod | Agent key in Secret |
| 7 | Rust Pod | Trade using agent key | Order signatures |

---

## Prerequisites

### Required Accounts

- [ ] Privy account (https://dashboard.privy.io)
- [ ] Hyperliquid testnet account (for testing)

### Development Environment

- [ ] Node.js 18+ and pnpm
- [ ] Python 3.11+ with uv
- [ ] PostgreSQL 14+
- [ ] Access to Kubernetes cluster

### Required API Keys

You'll need the following from Privy dashboard:

1. **App ID** - Your Privy application identifier
2. **App Secret** - For backend API authentication
3. **Verification Key** - Public key for JWT verification (PEM format)

---

## Phase 1: Privy Account Setup

### Step 1.1: Create Privy Application

1. Go to https://dashboard.privy.io
2. Click "Create Application"
3. Configure your app:
   - **Name:** Hyper-Trader
   - **Environment:** Development (for now)
   - **Chain:** Arbitrum (Hyperliquid uses Arbitrum)

### Step 1.2: Configure Authentication Methods

1. Navigate to **Login Methods**
2. Enable:
   - ✅ Ethereum Wallet (MetaMask, Rabby, etc.)
   - ✅ Embedded Wallets (auto-create for users)
3. Disable (for now):
   - ❌ Email
   - ❌ SMS
   - ❌ Social logins

### Step 1.3: Enable Embedded Wallets

1. Go to **Embedded Wallets** settings
2. Enable **Auto-creation**:
   - ✅ Create embedded wallet automatically on first login
3. Configure wallet options:
   - **Chain:** Arbitrum
   - **Recovery:** Enabled (user can export via UI if needed)

### Step 1.4: Get API Credentials

1. Navigate to **Settings** → **API Keys**
2. Copy the following:
   ```
   App ID: clxxx_xxxxxxxxxxxxxxxxx
   App Secret: [KEEP SECRET - NEVER COMMIT]
   ```

3. Navigate to **Settings** → **JWT Verification**
4. Copy the **Verification Key** (PEM format):
   ```
   -----BEGIN PUBLIC KEY-----
   MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
   -----END PUBLIC KEY-----
   ```

### Step 1.5: Configure Allowed Domains

1. Go to **Settings** → **Allowed Domains**
2. Add your domains:
   - Development: `http://localhost:3000`
   - Production: `https://app.hyper-trader.com`

---

## Phase 2: Frontend Implementation (React)

### Step 2.1: Install Dependencies

```bash
cd web
pnpm add @privy-io/react-auth
```

### Step 2.2: Create Environment Configuration

Create or update `web/.env.development`:

```bash
# Privy Configuration
VITE_PRIVY_APP_ID=clxxx_xxxxxxxxxxxxxxxxx

# API Configuration (existing)
VITE_API_URL=http://localhost:8000
```

**⚠️ IMPORTANT:** Never commit `.env.development` with real credentials!

### Step 2.3: Configure Privy Provider

Update `web/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { PrivyProvider } from '@privy-io/react-auth'
import { arbitrum } from 'viem/chains'
import App from './App'
import './index.css'

const privyConfig = {
  appId: import.meta.env.VITE_PRIVY_APP_ID,
  config: {
    // Appearance
    appearance: {
      theme: 'dark',
      accentColor: '#6366f1',
      logo: '/logo.png',
    },
    // Login methods
    loginMethods: ['wallet', 'email'], // Can add email later
    // Embedded wallets
    embeddedWallets: {
      createOnLogin: 'all-users', // Auto-create embedded wallet
      requireUserPasswordOnCreate: false, // Simplify UX
    },
    // Default chain
    defaultChain: arbitrum,
    supportedChains: [arbitrum],
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <PrivyProvider
      appId={privyConfig.appId}
      config={privyConfig.config}
    >
      <App />
    </PrivyProvider>
  </React.StrictMode>
)
```

### Step 2.4: Create Authentication Hook

Create `web/src/hooks/useAuth.ts`:

```typescript
import { usePrivy } from '@privy-io/react-auth'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export interface User {
  id: number
  privy_user_id: string
  wallet_address: string
  created_at: string
}

export function useAuth() {
  const { 
    ready, 
    authenticated, 
    user, 
    login, 
    logout: privyLogout,
    getAccessToken 
  } = usePrivy()
  
  const [backendUser, setBackendUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Sync with backend when Privy authentication changes
  useEffect(() => {
    const syncWithBackend = async () => {
      if (!ready) return
      
      if (!authenticated) {
        setBackendUser(null)
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        
        // Get Privy access token
        const accessToken = await getAccessToken()
        if (!accessToken) {
          throw new Error('No access token available')
        }

        // Get embedded wallet address
        const embeddedWallet = user?.linkedAccounts?.find(
          (account: any) => 
            account.type === 'wallet' && 
            account.walletClientType === 'privy'
        )

        if (!embeddedWallet) {
          throw new Error('No embedded wallet found')
        }

        // Authenticate with backend
        const response = await api.post('/auth/privy-login', {
          access_token: accessToken,
          wallet_address: embeddedWallet.address,
        })

        // Store JWT token for subsequent API calls
        localStorage.setItem('jwt_token', response.data.access_token)
        setBackendUser(response.data.user)
      } catch (error) {
        console.error('Backend authentication failed:', error)
        // If backend auth fails, logout from Privy
        await privyLogout()
      } finally {
        setLoading(false)
      }
    }

    syncWithBackend()
  }, [ready, authenticated, user, getAccessToken])

  const logout = async () => {
    // Clear backend token
    localStorage.removeItem('jwt_token')
    setBackendUser(null)
    // Logout from Privy
    await privyLogout()
  }

  return {
    ready,
    authenticated,
    user: backendUser,
    privyUser: user,
    loading,
    login,
    logout,
  }
}
```

### Step 2.5: Update API Client

Update `web/src/lib/api.ts` to include JWT token:

```typescript
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add JWT token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors (expired token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired, clear and redirect to login
      localStorage.removeItem('jwt_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

### Step 2.6: Create Login Page

Create or update `web/src/routes/login.tsx`:

```tsx
import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function LoginPage() {
  const { authenticated, loading, login } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (authenticated && !loading) {
      // Redirect to dashboard after successful login
      navigate({ to: '/dashboard' })
    }
  }, [authenticated, loading, navigate])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto" />
          <p className="mt-4 text-gray-600">Connecting to wallet...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold">
            Welcome to HyperTrader
          </CardTitle>
          <CardDescription>
            Connect your wallet to start copy trading
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={login}
            className="w-full"
            size="lg"
          >
            <svg 
              className="mr-2 h-5 w-5" 
              fill="currentColor" 
              viewBox="0 0 24 24"
            >
              <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm7.5 12.75h-3.75v3.75h-1.5v-3.75h-3.75v-1.5h3.75v-3.75h1.5v3.75h3.75v1.5z"/>
            </svg>
            Connect Wallet
          </Button>
          
          <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <p className="flex items-center">
              <svg className="mr-2 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              Supports MetaMask, Rabby, and other wallets
            </p>
            <p className="flex items-center">
              <svg className="mr-2 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              Your private keys never leave your wallet
            </p>
            <p className="flex items-center">
              <svg className="mr-2 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              Secure agent wallets for automated trading
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

### Step 2.7: Update Trader Creation

Update `web/src/routes/traders/new.tsx` to remove private key input:

```tsx
import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function NewTraderPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setLoading(true)
      
      // Backend will generate agent wallet and deploy
      const response = await api.post('/traders', {
        name: name || 'My Trader',
      })

      // Redirect to trader detail page
      navigate({ 
        to: `/traders/${response.data.id}` 
      })
    } catch (error: any) {
      console.error('Failed to create trader:', error)
      alert(error.response?.data?.detail || 'Failed to create trader')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Create New Trader</CardTitle>
          <CardDescription>
            Your wallet: {user?.wallet_address}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">Trader Name (Optional)</Label>
              <Input
                id="name"
                placeholder="My Aggressive Strategy"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                How it works:
              </h4>
              <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex items-start">
                  <svg className="mr-2 h-5 w-5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  A secure <strong>agent wallet</strong> will be created automatically
                </li>
                <li className="flex items-start">
                  <svg className="mr-2 h-5 w-5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  The agent can <strong>trade on your behalf</strong> but cannot withdraw funds
                </li>
                <li className="flex items-start">
                  <svg className="mr-2 h-5 w-5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  Your master wallet's private key <strong>stays in Privy's secure enclave</strong>
                </li>
                <li className="flex items-start">
                  <svg className="mr-2 h-5 w-5 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  Agent keys <strong>rotate daily</strong> for maximum security
                </li>
              </ul>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loading}
            >
              {loading ? 'Creating Trader...' : 'Create Trader'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## Phase 3: Backend Implementation (FastAPI)

### Step 3.1: Install Python Dependencies

Update `api/pyproject.toml` or `api/requirements.txt`:

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.5.0",
    "python-jose[cryptography]>=3.3.0",
    "httpx>=0.25.0",
    "web3>=6.11.0",
    "eth-account>=0.10.0",
    # Existing dependencies...
]
```

Then install:

```bash
cd api
uv pip install -e .
```

### Step 3.2: Update Configuration

Update `api/config.py`:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Existing settings
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days
    
    # Privy configuration
    privy_app_id: str
    privy_app_secret: str
    privy_verification_key: str  # PEM-formatted public key
    
    # Hyperliquid configuration
    hyperliquid_api_url: str = "https://api.hyperliquid-testnet.xyz"
    
    # Kubernetes
    k8s_namespace: str = "hyper-trader"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

Create `api/.env.development`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hypertrader

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# Privy
PRIVY_APP_ID=clxxx_xxxxxxxxxxxxxxxxx
PRIVY_APP_SECRET=your-privy-app-secret-keep-this-secret
PRIVY_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"

# Hyperliquid
HYPERLIQUID_API_URL=https://api.hyperliquid-testnet.xyz

# Kubernetes
K8S_NAMESPACE=hyper-trader
```

### Step 3.3: Create Privy Service

Create `api/services/privy_service.py`:

```python
import httpx
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from datetime import datetime
import logging

from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PrivyError(Exception):
    """Custom exception for Privy-related errors"""
    pass


class PrivyService:
    """Service for interacting with Privy API"""
    
    PRIVY_API_BASE = "https://api.privy.io/v1"
    
    def __init__(self):
        self.app_id = settings.privy_app_id
        self.app_secret = settings.privy_app_secret
        self.verification_key = settings.privy_verification_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "privy-app-id": self.app_id,
            }
        )
    
    async def verify_access_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify Privy access token and extract user information.
        
        Args:
            access_token: JWT access token from Privy frontend
            
        Returns:
            Dict containing user info (privy_user_id, wallet_address, etc.)
            
        Raises:
            PrivyError: If token is invalid or expired
        """
        try:
            # Decode JWT token using Privy's verification key
            payload = jwt.decode(
                access_token,
                self.verification_key,
                algorithms=["ES256"],  # Privy uses ES256
                audience=self.app_id,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                }
            )
            
            # Extract user ID (DID format: did:privy:xxx)
            privy_user_id = payload.get("sub")
            if not privy_user_id:
                raise PrivyError("No user ID in token")
            
            # Token is valid
            logger.info(f"Verified Privy token for user: {privy_user_id}")
            
            return {
                "privy_user_id": privy_user_id,
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
            }
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise PrivyError(f"Invalid access token: {e}")
    
    async def get_user_info(self, privy_user_id: str) -> Dict[str, Any]:
        """
        Fetch user information from Privy API.
        
        Args:
            privy_user_id: User's Privy ID (DID format)
            
        Returns:
            Dict with user info including linked wallets
        """
        url = f"{self.PRIVY_API_BASE}/users/{privy_user_id}"
        
        response = await self.client.get(
            url,
            auth=(self.app_id, self.app_secret),
        )
        
        if response.status_code != 200:
            raise PrivyError(
                f"Failed to fetch user info: {response.status_code} {response.text}"
            )
        
        return response.json()
    
    async def get_embedded_wallet_address(self, privy_user_id: str) -> Optional[str]:
        """
        Get user's embedded wallet address from Privy.
        
        Args:
            privy_user_id: User's Privy ID
            
        Returns:
            Wallet address or None if not found
        """
        user_info = await self.get_user_info(privy_user_id)
        
        # Find embedded wallet in linked accounts
        for account in user_info.get("linked_accounts", []):
            if account.get("type") == "wallet" and account.get("wallet_client_type") == "privy":
                return account.get("address")
        
        return None
    
    async def sign_message_via_rpc(
        self, 
        wallet_id: str, 
        message: str
    ) -> str:
        """
        Sign a message using Privy's RPC endpoint.
        
        Args:
            wallet_id: Privy wallet ID (format: privy:xxx)
            message: Message to sign (hex-encoded)
            
        Returns:
            Signature (hex string with 0x prefix)
        """
        url = f"{self.PRIVY_API_BASE}/wallets/{wallet_id}/rpc"
        
        payload = {
            "method": "personal_sign",
            "params": {
                "message": message,
            }
        }
        
        response = await self.client.post(
            url,
            json=payload,
            auth=(self.app_id, self.app_secret),
        )
        
        if response.status_code != 200:
            raise PrivyError(
                f"RPC signing failed: {response.status_code} {response.text}"
            )
        
        result = response.json()
        return result["data"]["signature"]
    
    async def sign_typed_data_via_rpc(
        self,
        wallet_id: str,
        typed_data: Dict[str, Any]
    ) -> str:
        """
        Sign EIP-712 typed data using Privy's RPC endpoint.
        
        Args:
            wallet_id: Privy wallet ID
            typed_data: EIP-712 structured data
            
        Returns:
            Signature (hex string)
        """
        url = f"{self.PRIVY_API_BASE}/wallets/{wallet_id}/rpc"
        
        payload = {
            "method": "eth_signTypedData_v4",
            "params": {
                "typedData": typed_data,
            }
        }
        
        response = await self.client.post(
            url,
            json=payload,
            auth=(self.app_id, self.app_secret),
        )
        
        if response.status_code != 200:
            raise PrivyError(
                f"Typed data signing failed: {response.status_code} {response.text}"
            )
        
        result = response.json()
        return result["data"]["signature"]
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
_privy_service: Optional[PrivyService] = None

def get_privy_service() -> PrivyService:
    """Get or create Privy service instance"""
    global _privy_service
    if _privy_service is None:
        _privy_service = PrivyService()
    return _privy_service
```

### Step 3.4: Create Hyperliquid Agent Service

Create `api/services/hyperliquid_agent_service.py`:

```python
import secrets
import httpx
from typing import Dict, Any
from eth_account import Account
from eth_account.messages import encode_typed_data
import logging

from api.services.privy_service import PrivyService, PrivyError
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HyperliquidAgentService:
    """
    Service for managing Hyperliquid agent wallets.
    Uses Privy to sign agent approval transactions.
    """
    
    def __init__(self, privy_service: PrivyService):
        self.privy_service = privy_service
        self.hyperliquid_api = settings.hyperliquid_api_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def generate_agent_wallet(self) -> Dict[str, str]:
        """
        Generate a new agent wallet locally.
        
        Returns:
            Dict with 'private_key' and 'address'
        """
        # Generate random 32-byte private key
        private_key_bytes = secrets.token_bytes(32)
        private_key_hex = private_key_bytes.hex()
        
        # Create account from private key
        account = Account.from_key(private_key_bytes)
        
        logger.info(f"Generated new agent wallet: {account.address}")
        
        return {
            "private_key": private_key_hex,
            "address": account.address,
        }
    
    def build_approve_agent_typed_data(
        self,
        agent_address: str,
        master_address: str,
        agent_name: str = None,
        is_mainnet: bool = False,
    ) -> Dict[str, Any]:
        """
        Build EIP-712 typed data for approving an agent.
        
        Args:
            agent_address: Address of the agent wallet to approve
            master_address: Address of the master wallet (user's Privy wallet)
            agent_name: Optional name for the agent
            is_mainnet: Whether this is for mainnet or testnet
            
        Returns:
            EIP-712 typed data structure
        """
        import time
        
        # Hyperliquid chain info
        chain_id = 42161 if is_mainnet else 421614  # Arbitrum mainnet or sepolia
        chain_name = "Mainnet" if is_mainnet else "Testnet"
        
        # Current timestamp in milliseconds
        nonce = int(time.time() * 1000)
        
        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Agent": [
                    {"name": "source", "type": "string"},
                    {"name": "connectionId", "type": "bytes32"},
                ]
            },
            "primaryType": "Agent",
            "domain": {
                "name": "Hyperliquid",
                "version": "1",
                "chainId": chain_id,
                "verifyingContract": "0x0000000000000000000000000000000000000000",
            },
            "message": {
                "source": "app.hyperliquid.xyz" if is_mainnet else "testnet.hyperliquid.xyz",
                "connectionId": f"0x{agent_address[2:].lower().zfill(64)}",  # Pad to 32 bytes
            }
        }
        
        return typed_data
    
    async def approve_agent(
        self,
        privy_wallet_id: str,
        agent_address: str,
        master_address: str,
        agent_name: str = None,
        is_mainnet: bool = False,
    ) -> Dict[str, Any]:
        """
        Approve an agent wallet to trade on behalf of master wallet.
        
        Args:
            privy_wallet_id: Privy wallet ID (did:privy:xxx)
            agent_address: Address of agent to approve
            master_address: Master wallet address
            agent_name: Optional agent name
            is_mainnet: Mainnet or testnet
            
        Returns:
            Response from Hyperliquid API
        """
        # Build typed data
        typed_data = self.build_approve_agent_typed_data(
            agent_address=agent_address,
            master_address=master_address,
            agent_name=agent_name,
            is_mainnet=is_mainnet,
        )
        
        # Sign with Privy
        try:
            signature = await self.privy_service.sign_typed_data_via_rpc(
                wallet_id=privy_wallet_id,
                typed_data=typed_data,
            )
            
            logger.info(f"Privy signed agent approval: {agent_address}")
        except PrivyError as e:
            logger.error(f"Failed to sign agent approval: {e}")
            raise
        
        # Submit to Hyperliquid
        response = await self._submit_agent_approval(
            master_address=master_address,
            agent_address=agent_address,
            signature=signature,
            typed_data=typed_data,
        )
        
        return response
    
    async def _submit_agent_approval(
        self,
        master_address: str,
        agent_address: str,
        signature: str,
        typed_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Submit agent approval to Hyperliquid exchange API.
        
        Args:
            master_address: Master wallet address
            agent_address: Agent wallet address
            signature: Signature from Privy
            typed_data: EIP-712 typed data that was signed
            
        Returns:
            API response
        """
        import time
        
        payload = {
            "action": {
                "type": "approveAgent",
                "hyperliquidChain": typed_data["domain"].get("name", "Testnet"),
                "signatureChainId": typed_data["domain"]["chainId"],
                "agentAddress": agent_address,
                "agentName": None,  # Optional
                "nonce": int(time.time() * 1000),
            },
            "signature": {
                "r": signature[:66],  # First 32 bytes + 0x
                "s": "0x" + signature[66:130],  # Next 32 bytes
                "v": int(signature[130:], 16),  # Last byte
            },
            "nonce": int(time.time() * 1000),
        }
        
        url = f"{self.hyperliquid_api}/exchange"
        
        response = await self.client.post(url, json=payload)
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Hyperliquid agent approval failed: {error_text}")
            raise Exception(f"Agent approval failed: {error_text}")
        
        result = response.json()
        logger.info(f"Agent approved successfully: {result}")
        
        return result
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

### Step 3.5: Update User Model

Update `api/models/user.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from api.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Privy authentication
    privy_user_id = Column(String, unique=True, index=True, nullable=False)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    
    # Privy wallet ID for signing (format: did:privy:xxx)
    privy_wallet_id = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    traders = relationship("Trader", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.wallet_address}>"
```

### Step 3.6: Update Trader Model

Update `api/models/trader.py`:

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from api.database import Base


class TraderStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVING_AGENT = "approving_agent"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Trader(Base):
    __tablename__ = "traders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Trader info
    name = Column(String, nullable=True)
    status = Column(SQLEnum(TraderStatus), default=TraderStatus.PENDING)
    
    # Agent wallet (approved by user's Privy wallet)
    agent_address = Column(String, index=True, nullable=False)
    # Note: agent_private_key is NOT stored in DB for security
    # It's only passed directly to K8s Secret
    
    # K8s deployment
    k8s_deployment_name = Column(String, nullable=True)
    k8s_pod_name = Column(String, nullable=True)
    
    # Agent rotation tracking
    agent_created_at = Column(DateTime, default=datetime.utcnow)
    agent_expires_at = Column(DateTime, nullable=True)  # For rotation
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="traders")
    
    def __repr__(self):
        return f"<Trader {self.id} - {self.name}>"
```

### Step 3.7: Create Auth Router

Create or update `api/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt

from api.database import get_db
from api.models.user import User
from api.services.privy_service import get_privy_service, PrivyService, PrivyError
from api.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


class PrivyLoginRequest(BaseModel):
    access_token: str
    wallet_address: str


class PrivyLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/privy-login", response_model=PrivyLoginResponse)
async def privy_login(
    request: PrivyLoginRequest,
    db: Session = Depends(get_db),
    privy: PrivyService = Depends(get_privy_service),
):
    """
    Authenticate user with Privy access token.
    Creates user account if first login.
    """
    try:
        # Verify Privy access token
        token_data = await privy.verify_access_token(request.access_token)
        privy_user_id = token_data["privy_user_id"]
        
        # Get embedded wallet info from Privy
        wallet_address = await privy.get_embedded_wallet_address(privy_user_id)
        
        if not wallet_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No embedded wallet found for user"
            )
        
        # Normalize wallet address
        wallet_address = wallet_address.lower()
        
        # Verify wallet address matches what frontend sent
        if wallet_address != request.wallet_address.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet address mismatch"
            )
        
        # Get or create user
        user = db.query(User).filter(User.privy_user_id == privy_user_id).first()
        
        if not user:
            # First login - create user
            user = User(
                privy_user_id=privy_user_id,
                wallet_address=wallet_address,
                privy_wallet_id=privy_user_id,  # Can extract actual wallet ID if needed
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Generate our own JWT token for API access
        access_token = create_access_token(
            data={"sub": str(user.id), "wallet": wallet_address}
        )
        
        return PrivyLoginResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "privy_user_id": user.privy_user_id,
                "wallet_address": user.wallet_address,
                "created_at": user.created_at.isoformat(),
            }
        )
        
    except PrivyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Privy token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


def create_access_token(data: dict) -> str:
    """Create JWT access token for our API"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from JWT"""
    from jose import JWTError
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


# OAuth2 scheme for Swagger docs
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/privy-login")
```

### Step 3.8: Update Trader Router

Update `api/routers/traders.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from api.database import get_db
from api.models.user import User
from api.models.trader import Trader, TraderStatus
from api.routers.auth import get_current_user
from api.services.privy_service import get_privy_service, PrivyService
from api.services.hyperliquid_agent_service import HyperliquidAgentService
from api.services.k8s_controller import K8sController

router = APIRouter(prefix="/traders", tags=["traders"])
logger = logging.getLogger(__name__)


class CreateTraderRequest(BaseModel):
    name: str | None = None


class TraderResponse(BaseModel):
    id: int
    name: str | None
    status: str
    agent_address: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=TraderResponse, status_code=status.HTTP_201_CREATED)
async def create_trader(
    request: CreateTraderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    privy: PrivyService = Depends(get_privy_service),
):
    """
    Create a new trader with agent wallet.
    
    Process:
    1. Generate agent wallet locally
    2. Sign agent approval with Privy
    3. Submit to Hyperliquid
    4. Deploy to Kubernetes
    """
    try:
        # Initialize services
        hyperliquid_agent = HyperliquidAgentService(privy)
        k8s_controller = K8sController()
        
        # Step 1: Generate agent wallet
        logger.info(f"Generating agent wallet for user {current_user.id}")
        agent_wallet = hyperliquid_agent.generate_agent_wallet()
        
        # Step 2: Create trader record
        trader = Trader(
            user_id=current_user.id,
            name=request.name or f"Trader {datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            status=TraderStatus.APPROVING_AGENT,
            agent_address=agent_wallet["address"],
            agent_created_at=datetime.utcnow(),
            agent_expires_at=datetime.utcnow() + timedelta(hours=23),  # Rotate daily
        )
        db.add(trader)
        db.commit()
        db.refresh(trader)
        
        # Step 3: Approve agent with Privy
        logger.info(f"Approving agent {agent_wallet['address']} via Privy")
        try:
            await hyperliquid_agent.approve_agent(
                privy_wallet_id=current_user.privy_wallet_id,
                agent_address=agent_wallet["address"],
                master_address=current_user.wallet_address,
                agent_name=trader.name,
                is_mainnet=False,  # Use testnet for now
            )
        except Exception as e:
            logger.error(f"Agent approval failed: {e}")
            trader.status = TraderStatus.ERROR
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to approve agent: {str(e)}"
            )
        
        # Step 4: Deploy to Kubernetes
        logger.info(f"Deploying trader {trader.id} to Kubernetes")
        trader.status = TraderStatus.DEPLOYING
        db.commit()
        
        try:
            deployment_name = await k8s_controller.deploy_trader(
                trader_id=trader.id,
                agent_private_key=agent_wallet["private_key"],
                master_wallet_address=current_user.wallet_address,
                privy_wallet_id=current_user.privy_wallet_id,
            )
            
            trader.k8s_deployment_name = deployment_name
            trader.status = TraderStatus.RUNNING
            db.commit()
            
        except Exception as e:
            logger.error(f"Kubernetes deployment failed: {e}")
            trader.status = TraderStatus.ERROR
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deploy trader: {str(e)}"
            )
        
        logger.info(f"Trader {trader.id} created and deployed successfully")
        
        return TraderResponse.from_orm(trader)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create trader: {str(e)}"
        )


@router.get("", response_model=list[TraderResponse])
async def list_traders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all traders for current user"""
    traders = db.query(Trader).filter(Trader.user_id == current_user.id).all()
    return [TraderResponse.from_orm(t) for t in traders]


@router.get("/{trader_id}", response_model=TraderResponse)
async def get_trader(
    trader_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get trader details"""
    trader = db.query(Trader).filter(
        Trader.id == trader_id,
        Trader.user_id == current_user.id
    ).first()
    
    if not trader:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trader not found"
        )
    
    return TraderResponse.from_orm(trader)


@router.delete("/{trader_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trader(
    trader_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete trader and clean up K8s resources"""
    trader = db.query(Trader).filter(
        Trader.id == trader_id,
        Trader.user_id == current_user.id
    ).first()
    
    if not trader:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trader not found"
        )
    
    # Delete K8s resources
    if trader.k8s_deployment_name:
        k8s_controller = K8sController()
        await k8s_controller.delete_trader(trader.k8s_deployment_name)
    
    # Delete from database
    db.delete(trader)
    db.commit()
    
    return None
```

### Step 3.9: Update K8s Controller

Update `api/services/k8s_controller.py` to include Privy credentials:

```python
from kubernetes import client, config
from api.config import get_settings
import base64
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class K8sController:
    """Controller for managing Kubernetes deployments"""
    
    def __init__(self):
        # Load K8s config (in-cluster or kubeconfig)
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = settings.k8s_namespace
    
    async def deploy_trader(
        self,
        trader_id: int,
        agent_private_key: str,
        master_wallet_address: str,
        privy_wallet_id: str,
    ) -> str:
        """
        Deploy a trader pod with agent wallet.
        
        Args:
            trader_id: Database ID of trader
            agent_private_key: Agent wallet private key (hex)
            master_wallet_address: User's Privy wallet address
            privy_wallet_id: Privy wallet ID for rotation
            
        Returns:
            Deployment name
        """
        deployment_name = f"trader-{trader_id}"
        secret_name = f"trader-{trader_id}-secret"
        
        # Create Secret with agent credentials
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name,
                namespace=self.namespace,
            ),
            string_data={
                "AGENT_PRIVATE_KEY": agent_private_key,
                "MASTER_WALLET_ADDRESS": master_wallet_address,
                "PRIVY_WALLET_ID": privy_wallet_id,
                "PRIVY_APP_ID": settings.privy_app_id,
                "PRIVY_APP_SECRET": settings.privy_app_secret,
            },
            type="Opaque"
        )
        
        try:
            self.core_v1.create_namespaced_secret(
                namespace=self.namespace,
                body=secret
            )
            logger.info(f"Created secret: {secret_name}")
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                self.core_v1.replace_namespaced_secret(
                    name=secret_name,
                    namespace=self.namespace,
                    body=secret
                )
                logger.info(f"Updated secret: {secret_name}")
            else:
                raise
        
        # Create Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                namespace=self.namespace,
                labels={
                    "app": "hyper-trader",
                    "trader-id": str(trader_id),
                }
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"trader-id": str(trader_id)}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            "app": "hyper-trader",
                            "trader-id": str(trader_id),
                        }
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="trader",
                                image="hyper-trader:latest",  # Your Rust trader image
                                env_from=[
                                    client.V1EnvFromSource(
                                        secret_ref=client.V1SecretEnvSource(
                                            name=secret_name
                                        )
                                    )
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "100m", "memory": "128Mi"},
                                    limits={"cpu": "500m", "memory": "512Mi"},
                                ),
                            )
                        ],
                        restart_policy="Always",
                    )
                )
            )
        )
        
        try:
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace,
                body=deployment
            )
            logger.info(f"Created deployment: {deployment_name}")
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                self.apps_v1.replace_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace,
                    body=deployment
                )
                logger.info(f"Updated deployment: {deployment_name}")
            else:
                raise
        
        return deployment_name
    
    async def delete_trader(self, deployment_name: str):
        """Delete trader deployment and secret"""
        secret_name = f"{deployment_name}-secret"
        
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            logger.info(f"Deleted deployment: {deployment_name}")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise
        
        try:
            self.core_v1.delete_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )
            logger.info(f"Deleted secret: {secret_name}")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise
```

---

## Phase 4: Database Migrations

### Step 4.1: Create Migration

```bash
cd api
uv run alembic revision -m "add_privy_authentication"
```

### Step 4.2: Edit Migration File

Edit the generated file in `api/alembic/versions/`:

```python
"""add_privy_authentication

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add Privy fields to users table
    op.add_column('users', sa.Column('privy_user_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('wallet_address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('privy_wallet_id', sa.String(), nullable=True))
    
    # Create indexes
    op.create_index('ix_users_privy_user_id', 'users', ['privy_user_id'], unique=True)
    op.create_index('ix_users_wallet_address', 'users', ['wallet_address'], unique=True)
    
    # Update traders table
    op.add_column('traders', sa.Column('agent_address', sa.String(), nullable=True))
    op.add_column('traders', sa.Column('agent_created_at', sa.DateTime(), nullable=True))
    op.add_column('traders', sa.Column('agent_expires_at', sa.DateTime(), nullable=True))
    op.add_column('traders', sa.Column('status', sa.String(), nullable=True))
    
    # Remove old private key column (if exists)
    # op.drop_column('traders', 'encrypted_private_key')


def downgrade():
    op.drop_index('ix_users_wallet_address', 'users')
    op.drop_index('ix_users_privy_user_id', 'users')
    op.drop_column('users', 'privy_wallet_id')
    op.drop_column('users', 'wallet_address')
    op.drop_column('users', 'privy_user_id')
    
    op.drop_column('traders', 'status')
    op.drop_column('traders', 'agent_expires_at')
    op.drop_column('traders', 'agent_created_at')
    op.drop_column('traders', 'agent_address')
```

### Step 4.3: Run Migration

```bash
uv run alembic upgrade head
```

---

## Phase 5: Testing

### Step 5.1: Unit Tests

Create `api/tests/test_privy_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from api.services.privy_service import PrivyService, PrivyError


@pytest.mark.asyncio
async def test_verify_valid_token():
    """Test verifying a valid Privy token"""
    privy = PrivyService()
    
    # Mock JWT verification
    with patch('api.services.privy_service.jwt.decode') as mock_decode:
        mock_decode.return_value = {
            "sub": "did:privy:test123",
            "iat": 1234567890,
            "exp": 9999999999,
        }
        
        result = await privy.verify_access_token("fake_token")
        
        assert result["privy_user_id"] == "did:privy:test123"


@pytest.mark.asyncio
async def test_verify_expired_token():
    """Test verifying an expired token"""
    privy = PrivyService()
    
    with patch('api.services.privy_service.jwt.decode') as mock_decode:
        from jose import JWTError
        mock_decode.side_effect = JWTError("Token expired")
        
        with pytest.raises(PrivyError):
            await privy.verify_access_token("expired_token")
```

### Step 5.2: Integration Tests

Create `web/tests/privy-auth.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

test.describe('Privy Authentication', () => {
  test('should show connect wallet button', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('button', { name: /connect wallet/i })).toBeVisible()
  })
  
  test('should redirect to dashboard after login', async ({ page }) => {
    // This would require mocking Privy in test environment
    // See Privy docs for testing guidance
  })
})
```

### Step 5.3: Manual Testing Checklist

- [ ] User can connect wallet via Privy
- [ ] Backend receives valid access token
- [ ] User record created in database
- [ ] JWT token returned to frontend
- [ ] Subsequent API calls include JWT
- [ ] Agent wallet created successfully
- [ ] Agent approval signed by Privy
- [ ] Trader deployed to Kubernetes
- [ ] Rust pod starts with agent credentials

---

## Phase 6: Deployment

### Step 6.1: Production Environment Setup

Create `.env.production`:

```bash
# NEVER commit this file!

# Database
DATABASE_URL=postgresql://prod_user:prod_password@postgres:5432/hypertrader

# JWT
JWT_SECRET_KEY=super-secret-production-key-use-secrets-manager

# Privy
PRIVY_APP_ID=clxxx_production_app_id
PRIVY_APP_SECRET=production_secret_from_privy_dashboard
PRIVY_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
...production key...
-----END PUBLIC KEY-----"

# Hyperliquid
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz

# Kubernetes
K8S_NAMESPACE=hyper-trader-prod
```

### Step 6.2: Secrets Management

**Use Kubernetes Secrets or external secrets manager:**

```bash
# Create K8s secret for backend
kubectl create secret generic hyper-trader-backend \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=JWT_SECRET_KEY=... \
  --from-literal=PRIVY_APP_ID=... \
  --from-literal=PRIVY_APP_SECRET=... \
  --from-literal=PRIVY_VERIFICATION_KEY="$(cat privy_verification_key.pem)" \
  -n hyper-trader-prod
```

### Step 6.3: Deploy Backend

```bash
cd api
docker build -t hyper-trader-api:latest .
docker push your-registry/hyper-trader-api:latest
kubectl apply -f kubernetes/api-deployment.yaml
```

### Step 6.4: Deploy Frontend

```bash
cd web
pnpm build
# Deploy to Vercel/Netlify or serve static files
```

---

## Security Considerations

### 🔒 Critical Security Practices

1. **Never Commit Secrets**
   - Add `.env*` to `.gitignore`
   - Use environment variables or secrets managers
   - Rotate secrets regularly

2. **Token Expiration**
   - JWT tokens should have reasonable expiration (7 days default)
   - Implement refresh token mechanism if needed
   - Validate tokens on every request

3. **Agent Key Security**
   - Agent private keys never stored in database
   - Only exists in K8s Secrets (encrypted at rest)
   - Rotate daily for defense-in-depth

4. **HTTPS Only**
   - All communication over HTTPS
   - Set secure cookies
   - Enable HSTS headers

5. **Rate Limiting**
   - Limit login attempts
   - Rate limit API endpoints
   - Monitor for abuse

6. **Input Validation**
   - Validate all user inputs
   - Sanitize addresses
   - Check signature formats

---

## Troubleshooting

### Common Issues

#### "Invalid Privy token"
- **Cause:** Token expired or malformed
- **Fix:** Check token format, ensure Verification Key matches Privy dashboard

#### "No embedded wallet found"
- **Cause:** User hasn't created embedded wallet yet
- **Fix:** Ensure `embeddedWallets.createOnLogin` is set in Privy config

#### "Agent approval failed"
- **Cause:** Privy signature incorrect or Hyperliquid API issue
- **Fix:** Check typed data structure matches Hyperliquid requirements

#### "K8s deployment failed"
- **Cause:** Insufficient permissions or invalid image
- **Fix:** Check K8s RBAC, verify image exists

### Debug Logging

Enable debug logging:

```python
# api/main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## Next Steps

After completing this guide:

1. ✅ Implement daily agent rotation cron job
2. ✅ Add monitoring and alerting
3. ✅ Implement Rust trader (see separate doc)
4. ✅ Test on Hyperliquid testnet
5. ✅ Security audit before mainnet
6. ✅ Deploy to production

---

## References

- [Privy Documentation](https://docs.privy.io)
- [Hyperliquid API Docs](https://hyperliquid.gitbook.io)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [React Query Docs](https://tanstack.com/query)

---

**Document Status:** Ready for Implementation  
**Review Required:** Security team approval before production
