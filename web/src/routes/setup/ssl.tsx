import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSSLStatus, configureSSL } from '@/api/ssl-setup'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export const Route = createFileRoute('/setup/ssl')({
  component: SSLSetupPage,
})

function SSLSetupPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'domain' | 'ip_only'>('domain')
  const [domain, setDomain] = useState('')
  const [email, setEmail] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Check SSL status on load; redirect to home if already configured
  const { data: sslStatus, isLoading: isStatusLoading } = useQuery({
    queryKey: ['ssl-status'],
    queryFn: getSSLStatus,
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (sslStatus?.ssl_configured) {
      void navigate({ to: '/' })
    }
  }, [sslStatus, navigate])

  const { mutate: submitSSL, isPending, error: mutationError } = useMutation({
    mutationFn: configureSSL,
    onSuccess: (data) => {
      // Invalidate so the root layout sees the updated SSL status
      void queryClient.invalidateQueries({ queryKey: ['ssl-status'] })
      if (data.redirect_url) {
        window.location.href = data.redirect_url
      } else {
        setSuccessMessage(data.message)
      }
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)

    if (mode === 'domain') {
      if (!domain.trim()) {
        setValidationError('Domain name is required.')
        return
      }
      if (!email.trim()) {
        setValidationError('Email address is required for Let\'s Encrypt.')
        return
      }
    }

    submitSSL({ mode, domain: domain.trim() || undefined, email: email.trim() || undefined })
  }

  const errorMessage =
    validationError ??
    (mutationError instanceof Error ? mutationError.message : null)

  if (isStatusLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight">SSL Setup</h1>
          <p className="mt-2 text-muted-foreground">
            Configure secure HTTPS access for your dashboard
          </p>
        </div>

        {successMessage ? (
          <Card>
            <CardHeader>
              <CardTitle>SSL Configured</CardTitle>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertTitle>Success</AlertTitle>
                <AlertDescription>{successMessage}</AlertDescription>
              </Alert>
              <p className="mt-4 text-sm text-muted-foreground">
                Your dashboard is now accessible over HTTPS using your server&apos;s
                IP address. Note: your browser may show a security warning because
                the certificate is self-signed — this is expected for IP-only mode.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Configure SSL</CardTitle>
              <CardDescription>
                Choose how you want to secure your dashboard connection.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-6">
                {/* Mode selection */}
                <div className="space-y-3">
                  <Label className="text-base font-medium">Connection type</Label>

                  <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-border p-4 hover:bg-accent/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-accent/30">
                    <input
                      type="radio"
                      name="ssl-mode"
                      value="domain"
                      checked={mode === 'domain'}
                      onChange={() => setMode('domain')}
                      className="mt-0.5 accent-primary"
                    />
                    <div>
                      <span className="font-medium text-sm">
                        I have a domain name{' '}
                        <span className="text-xs text-muted-foreground font-normal">
                          (recommended)
                        </span>
                      </span>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Automatically obtain a free Let&apos;s Encrypt certificate for
                        your domain.
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-border p-4 hover:bg-accent/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-accent/30">
                    <input
                      type="radio"
                      name="ssl-mode"
                      value="ip_only"
                      checked={mode === 'ip_only'}
                      onChange={() => setMode('ip_only')}
                      className="mt-0.5 accent-primary"
                    />
                    <div>
                      <span className="font-medium text-sm">IP address only</span>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Use a self-signed certificate. Browsers will show a security
                        warning.
                      </p>
                    </div>
                  </label>
                </div>

                {/* Domain/email fields — visible only in "domain" mode */}
                {mode === 'domain' && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="domain">Domain name</Label>
                      <Input
                        id="domain"
                        type="text"
                        placeholder="example.com"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        autoComplete="off"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email address</Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="email"
                      />
                      <p className="text-xs text-muted-foreground">
                        Used by Let&apos;s Encrypt for certificate expiry notifications.
                      </p>
                    </div>
                  </div>
                )}

                {/* IP-only informational warning */}
                {mode === 'ip_only' && (
                  <Alert>
                    <AlertTitle>Browser security warning expected</AlertTitle>
                    <AlertDescription>
                      When using IP-only mode, your browser will display a "Your
                      connection is not private" warning because the certificate is
                      self-signed. You can safely proceed past this warning.
                    </AlertDescription>
                  </Alert>
                )}

                {/* Validation / API error */}
                {errorMessage && (
                  <Alert variant="destructive">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{errorMessage}</AlertDescription>
                  </Alert>
                )}
              </CardContent>

              <CardFooter>
                <Button type="submit" className="w-full" disabled={isPending}>
                  {isPending ? 'Configuring…' : 'Configure SSL'}
                </Button>
              </CardFooter>
            </form>
          </Card>
        )}
      </div>
    </div>
  )
}
