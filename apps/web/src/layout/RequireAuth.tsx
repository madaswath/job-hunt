import { useAuth } from "@clerk/clerk-react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getTestToken } from "../lib/api/client";

function ClerkGate({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <p className="p-8">Loading session…</p>;
  if (!isSignedIn) return <Navigate to="/sign-in" replace />;
  return <>{children}</>;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  if (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY) {
    return <ClerkGate>{children}</ClerkGate>;
  }
  if (!getTestToken()) return <Navigate to="/sign-in" replace />;
  return <>{children}</>;
}

