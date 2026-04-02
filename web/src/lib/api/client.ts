let tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

export function getToken(): Promise<string | null> {
  if (tokenGetter) {
    return tokenGetter();
  }
  return Promise.resolve(null);
}
