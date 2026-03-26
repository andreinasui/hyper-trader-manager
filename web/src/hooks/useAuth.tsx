import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react'
import { config } from '@/config'

export interface AuthUser {
  id: string
  username: string
  is_admin: boolean
}

interface AuthState {
  user: AuthUser | null
  token: string | null
  authenticated: boolean
  isInitialized: boolean
  loading: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  bootstrap: (username: string, password: string) => Promise<void>
  checkAuth: () => Promise<void>
  checkSetup: () => Promise<void>
  ready: boolean
}

// Initial state
const initialState: AuthState = {
  user: null,
  token: null,
  authenticated: false,
  isInitialized: false,
  loading: true,
}

const AuthContext = createContext<AuthContextType | null>(null)

// Helper to make API requests
async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${config.VITE_API_URL}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  return response.json()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(initialState)

  const checkSetup = useCallback(async () => {
    try {
      const data = await apiRequest<{ initialized: boolean }>('/api/v1/auth/setup-status')
      setState(s => ({ ...s, isInitialized: data.initialized }))
    } catch (error) {
      console.error('Failed to check setup status:', error)
    }
  }, [])

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setState(s => ({ ...s, loading: false }))
      return
    }

    try {
      const user = await apiRequest<AuthUser>('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      setState(s => ({
        ...s,
        token,
        user,
        authenticated: true,
        loading: false,
      }))
    } catch (error) {
      console.error('Auth check failed:', error)
      // Invalid token
      localStorage.removeItem('auth_token')
      setState(s => ({
        ...s,
        token: null,
        user: null,
        authenticated: false,
        loading: false,
      }))
    }
  }, [])

  // Initialize
  useEffect(() => {
    const init = async () => {
      await checkSetup()
      await checkAuth()
    }
    init()
  }, [checkSetup, checkAuth])

  const login = useCallback(async (username: string, password: string) => {
    const data = await apiRequest<{ access_token: string; user: AuthUser }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    
    const { access_token, user } = data
    
    localStorage.setItem('auth_token', access_token)
    
    setState(s => ({
      ...s,
      token: access_token,
      user,
      authenticated: true,
    }))
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setState(s => ({
      ...s,
      token: null,
      user: null,
      authenticated: false,
    }))
  }, [])

  const bootstrap = useCallback(async (username: string, password: string) => {
    await apiRequest('/api/v1/auth/bootstrap', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    // Auto-login after bootstrap
    await login(username, password)
    // Update initialization status
    setState(s => ({ ...s, isInitialized: true }))
  }, [login])

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    bootstrap,
    checkAuth,
    checkSetup,
    ready: !state.loading,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
