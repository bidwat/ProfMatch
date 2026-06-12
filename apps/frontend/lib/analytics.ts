// Fire-and-forget product analytics (doc.md §7.3). Events are name-allowlisted
// server-side and properties are size-clamped; never send raw query text,
// document content, or emails.
export function track(name: string, properties: Record<string, string | number | boolean | null> = {}) {
  try {
    void fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, properties }),
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    // Analytics must never break the product.
  }
}
