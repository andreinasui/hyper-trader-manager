import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import type { User, LoginRequest } from '@/lib/types'

export interface AuthState {
  user: User | null
  loading: boolean
  authenticated: boolean
  error: string | null
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    authenticated: false,
    error: null,
  })

  const checkAuth = useCallback(async () => {
    // If no token, we are definitely not authenticated
    const token = api.getToken()
    if (!token) {
      setState(s => ({ ...s, loading: false, authenticated: false, user: null, error: null }))
      return
    }

    try {
      // If we have a token, try to fetch user details
      const user = await api.me()
      setState({
        user,
        loading: false,
        authenticated: true,
        error: null,
      })
    } catch (error) {
      // Token invalid or expired
      api.setToken(null)
      setState({
        user: null,
        loading: false,
        authenticated: false,
        error: null,
      })
    }
  }, [])

  // Check auth on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (data: LoginRequest) => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      await api.login(data)
      // After login, fetch user details to update state
      const user = await api.me()
      setState({
        user,
        loading: false,
        authenticated: true,
        error: null,
      })
    } catch (error: any) {
      console.error('Login error:', error)
      setState(s => ({ 
        ...s, 
        loading: false, 
        error: error.message || 'Login failed' 
      }))
      throw error
    }
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setState({
        user: null,
        loading: false,
        authenticated: false,
        error: null,
      })
    }
  }

  return {
    ...state,
    // Add these for compatibility with previous useAuth interface if needed
    ready: !state.loading,
    login,
    logout,
    checkAuth
  }
}
