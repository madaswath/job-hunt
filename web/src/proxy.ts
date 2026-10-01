import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  checkRequest,
  parseAllowedHosts,
  parseAllowedOrigins,
} from "@/lib/origin-guard.mjs";

const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/marketing(.*)",
]);

const clerk = clerkMiddleware(async (auth, req) => {
  const pathname = req.nextUrl.pathname;

  if (pathname.startsWith("/api/")) {
    const decision = checkRequest({
      secFetchSite: req.headers.get("sec-fetch-site"),
      origin: req.headers.get("origin"),
      host: req.headers.get("host"),
      allowedHosts: parseAllowedHosts(process.env.CAREER_OPS_WEB_ALLOWED_HOSTS),
      allowedOrigins: parseAllowedOrigins(process.env.CAREER_OPS_ALLOWED_ORIGINS),
    });
    if (!decision.ok) {
      return NextResponse.json({ error: decision.reason }, { status: decision.status });
    }
  }

  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

/** Next.js 16 proxy (replaces middleware.ts). Clerk + /api origin guard. */
export function proxy(req: NextRequest, event: unknown) {
  // @ts-expect-error clerk middleware matches Next proxy signature
  return clerk(req, event);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/:path*",
  ],
};
