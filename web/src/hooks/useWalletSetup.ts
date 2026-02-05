/**
 * Hook for setting up newly created embedded wallets with backend signing capability.
 * 
 * When a user logs in for the first time and an embedded wallet is created,
 * this hook automatically adds your backend's authorization key as a signer.
 * This allows your backend to sign transactions on behalf of users.
 * 
 * Uses Privy's React SDK `useSigners` hook.
 */

import { useCallback, useState } from 'react'
import { useSigners } from '@privy-io/react-auth'
import type { User } from '@privy-io/react-auth'

interface WalletSetupConfig {
  /**
   * The ID of the key quorum (authorization key) for your backend.
   * Created in Privy Dashboard under "Authorization Keys"
   */
  signerKeyQuorumId: string
  
  /**
   * Policy IDs to restrict what the backend signer can do.
   * Leave empty [] for unrestricted backend access.
   */
  policyIds: string[]
}

interface WalletSetupResult {
  /**
   * Adds your backend signer to the user's embedded wallet
   */
  setupWallet: (user: User) => Promise<void>
  
  /**
   * Whether the setup is currently in progress
   */
  isSettingUp: boolean
  
  /**
   * Any error that occurred during setup
   */
  error: Error | null
}

/**
 * Custom hook to add backend signing capability to embedded wallets.
 * 
 * @example
 * ```tsx
 * const { setupWallet } = useWalletSetup({
 *   signerKeyQuorumId: import.meta.env.VITE_PRIVY_SIGNER_KEY_QUORUM_ID,
 *   policyIds: [import.meta.env.VITE_PRIVY_ALL_ACTIONS_POLICY_ID], // or [] for no restrictions
 * });
 * 
 * // Call after new user logs in
 * await setupWallet(user);
 * ```
 */
export function useWalletSetup(config: WalletSetupConfig): WalletSetupResult {
  const { addSigners } = useSigners()
  const [isSettingUp, setIsSettingUp] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const setupWallet = useCallback(async (user: User) => {
    setIsSettingUp(true)
    setError(null)

    try {
      // Get the embedded wallet
      const embeddedWallet = user.linkedAccounts?.find(
        (account: any) => account.type === 'wallet' && account.walletClientType === 'privy'
      ) as any

      if (!embeddedWallet) {
        throw new Error('No embedded wallet found for user')
      }

      const walletAddress = embeddedWallet.address

      console.log('[WalletSetup] Adding backend signer to wallet:', { 
        walletAddress,
        signerId: config.signerKeyQuorumId,
        policies: config.policyIds,
      })

      // Use Privy's React SDK to add the signer
      await addSigners({
        address: walletAddress,
        signers: [
          {
            signerId: config.signerKeyQuorumId,
            policyIds: config.policyIds,
          },
        ],
      })

      console.log('[WalletSetup] Backend signer added successfully')
      
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error occurred')
      console.error('[WalletSetup] Error setting up wallet:', error)
      setError(error)
      throw error
    } finally {
      setIsSettingUp(false)
    }
  }, [config, addSigners])

  return {
    setupWallet,
    isSettingUp,
    error,
  }
}
