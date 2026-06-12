'use client';

import { Button } from '@heroui/react';

import Link from 'next/link';
import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center' }}>
      <h2 style={{ marginBottom: 16 }}>Something went wrong!</h2>
      <p className="muted" style={{ marginBottom: 24, maxWidth: 500 }}>
        We experienced an unexpected error. Please try again, or navigate back to the home page.
      </p>
      <div className="tags" style={{ justifyContent: 'center' }}>
        <Button onPress={() => reset()}>
          Try again
        </Button>
        <Link href="/" className="button secondary">
          Go Home
        </Link>
      </div>
    </div>
  );
}
