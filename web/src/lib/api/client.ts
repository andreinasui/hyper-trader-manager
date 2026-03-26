import { client } from './generated/client.gen';
import { config } from '@/config';

// Configure the generated client instance
client.setConfig({
  baseUrl: config.VITE_API_URL,
});

// We need a way to set the token getter dynamically
let tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

// Add interceptor for auth
client.interceptors.request.use(async (request) => {
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
  }
  return request;
});

// Add interceptor for 401
client.interceptors.response.use((response) => {
  if (response.status === 401) {
    // Check if we are already on login page to avoid loops
    if (window.location.pathname !== '/') {
      window.location.href = '/';
    }
  }
  return response;
});

// Re-export the configured client
export { client };
