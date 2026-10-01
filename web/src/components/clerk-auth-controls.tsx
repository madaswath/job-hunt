"use client";

import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

/**
 * Sign-in / sign-up when signed out; profile menu when signed in.
 */
export function ClerkAuthControls({ compact = false }: { compact?: boolean }) {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return null;
  }

  return (
    <div className={compact ? "flex items-center gap-1.5" : "flex flex-col gap-2 px-1"}>
      <SignedOut>
        <div className="flex flex-wrap items-center gap-2">
          <SignInButton mode="modal">
            <button
              type="button"
              className="rounded-md border border-border bg-surface/60 px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface-hover"
            >
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button
              type="button"
              className="rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-brand-foreground transition hover:opacity-90"
            >
              Sign up
            </button>
          </SignUpButton>
        </div>
      </SignedOut>
      <SignedIn>
        <div className="flex items-center gap-2">
          <UserButton
            afterSignOutUrl="/sign-in"
            appearance={{
              elements: {
                avatarBox: compact ? "h-8 w-8" : "h-9 w-9",
              },
            }}
          />
        </div>
      </SignedIn>
    </div>
  );
}
