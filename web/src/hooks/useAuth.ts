/**
 * Authentication hook wrapping Privy SDK.
 * 
 * Provides a clean interface for authentication throughout the app.
 */

import { usePrivy as useRealPrivy } from '@privy-io/react-auth'
import { usePrivy as useMockPrivy } from '@/test/mocks/MockPrivyProvider'
import { useEffect } from 'react'
import { api } from '@/lib/api'
import { setTokenGetter } from '@/lib/api/client'

export interface AuthUser {
  walletAddress: string
  privyUserId: string
}

// Check if we're in mock mode (for E2E tests)
function isMockMode(): boolean {
  return typeof window !== 'undefined' && !!(window as any).__PRIVY_MOCK__?.enabled;
}

export function useAuth() {
  // Use mock or real Privy based on environment
  const privyHook = isMockMode() ? useMockPrivy : useRealPrivy;
  
  const { 
    ready, 
    authenticated, 
    user: privyUser, 
    login, 
    logout: privyLogout,
    getAccessToken 
  } = privyHook()

  // Set up API client token getter when hook initializes
  useEffect(() => {
    api.setPrivyTokenGetter(getAccessToken)
    setTokenGetter(getAccessToken)
  }, [getAccessToken])

  // Extract wallet address from Privy user
  const getWalletAddress = (): string | null => {
    if (!privyUser || !authenticated) return null
    
    // First try to use the primary wallet if available
    if (privyUser.wallet?.address) return privyUser.wallet.address

    // Fallback to finding the first external wallet in linked accounts
    const wallet = privyUser.linkedAccounts?.find(
      (account: any) => 
        account.type === 'wallet' && 
        account.walletClientType !== 'privy'
    )
    
    return wallet?.address || null
  }

  const user: AuthUser | null = authenticated && privyUser ? {
    walletAddress: getWalletAddress() || '',
    privyUserId: privyUser.id || '',
  } : null

  const logout = async () => {
    await privyLogout()
  }

  return {
    ready,
    authenticated,
    user,
    loading: !ready,
    login,
    logout,
    getAccessToken,
  }
}
