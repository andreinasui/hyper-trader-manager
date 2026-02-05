/**
 * Enhanced authentication hook that automatically sets up wallets for new users.
 * 
 * This hook wraps the base useAuth hook and adds wallet setup functionality.
 * When a new user logs in and an embedded wallet is created, it automatically
 * adds a server-controlled signer with the configured policy.
 */

import { useEffect, useRef } from 'react'
import { useAuth } from './useAuth'
import { useWalletSetup } from './useWalletSetup'
import { usePrivy } from '@privy-io/react-auth'

/**
 * Hook that combines authentication with automatic wallet setup for new users.
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { authenticated, user, loading } = useAuthWithWalletSetup();
 *   
 *   if (loading) return <div>Loading...</div>;
 *   if (!authenticated) return <div>Please log in</div>;
 *   return <div>Welcome {user.walletAddress}</div>;
 * }
 * ```
 */
export function useAuthWithWalletSetup() {
  const auth = useAuth()
  const { user: privyUser } = usePrivy()
  const setupAttempted = useRef(false)
  const lastUserId = useRef<string | null>(null)
  
  const { setupWallet, isSettingUp, error: setupError } = useWalletSetup({
    signerKeyQuorumId: import.meta.env.VITE_PRIVY_SIGNER_KEY_QUORUM_ID || '',
    policyIds: import.meta.env.VITE_PRIVY_ALL_ACTIONS_POLICY_ID ? [import.meta.env.VITE_PRIVY_ALL_ACTIONS_POLICY_ID] : [],
  })

  // Automatically set up wallet when user logs in for the first time
  useEffect(() => {
    // Reset setup flag if user changes
    if (privyUser && lastUserId.current !== privyUser.id) {
      setupAttempted.current = false
      lastUserId.current = privyUser.id
    }

    const shouldSetupWallet = 
      auth.authenticated && 
      privyUser && 
      !setupAttempted.current &&
      !isSettingUp

    if (shouldSetupWallet) {
      // Check if user has an embedded wallet
      const hasEmbeddedWallet = privyUser.linkedAccounts?.some(
        (account: any) => account.type === 'wallet' && account.walletClientType === 'privy'
      )

      if (hasEmbeddedWallet) {
        console.log('[AuthWithWalletSetup] Setting up wallet for user:', privyUser.id)
        setupAttempted.current = true
        
        setupWallet(privyUser).catch((err) => {
          console.error('[AuthWithWalletSetup] Failed to set up wallet:', err)
          // Don't reset the flag - we don't want to retry automatically
          // User can retry by logging out and back in
        })
      }
    }
  }, [auth.authenticated, privyUser, isSettingUp, setupWallet])

  return {
    ...auth,
    walletSetup: {
      isSettingUp,
      error: setupError,
    },
  }
}
