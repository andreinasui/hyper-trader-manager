# Privy Integration: Web UI + Backend Implementation Guide

## Overview

This document guides you through integrating **Privy wallet authentication** into the Hyper-Trader web application and FastAPI backend using the **Agent Wallet Pattern**.

### What We're Building

- **User Authentication:** Users connect via MetaMask/Rabby using Privy's embedded wallets
- **Secure Trading:** Rust trader uses local agent keys (not calling Privy on every trade)

### Authentication Flow

```
User → Connect Wallet (Privy) → 
Frontend receives access token → 
Backend verifies token → 
Creates/retrieves user → 
```

### Agent Creation Flow

```
User creates trader → 
Deploy Rust pod with privy required data to get signer in Rust pod
Rust pod generates agent wallet locally → 
Rust pod calls Privy RPC API to sign approveAgent → 
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
| 3 | Backend | Deploy K8s pod | Privy user_id used to get signer |
| 4 | Rust Pod | Generate agent wallet | From privy |
| 5 | Rust Pod | Sign approveAgent via Privy RPC | Signature |
| 6 | Rust Pod | Submit to Hyperliquid | Agent approval |
| 7 | Rust Pod | Trade using agent key | Order signatures |

