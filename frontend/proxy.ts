import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Mobile Detection Middleware
 *
 * Detects mobile users and optionally redirects them to the mobile PWA experience.
 * Users can opt-out via cookie or query parameter.
 */
function detectMobile(request: NextRequest): boolean {
  const userAgent = request.headers.get("user-agent") || "";

  // Check for mobile devices
  const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
  return mobileRegex.test(userAgent);
}

export default clerkMiddleware((auth, request) => {
  const { pathname, searchParams } = request.nextUrl;

  // Skip middleware for static files, API routes, and mobile routes
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/mobile") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Check for desktop preference cookie or query param
  const preferDesktop =
    request.cookies.get("prefer-desktop")?.value === "true" ||
    searchParams.get("desktop") === "true";

  // If user explicitly wants desktop, set cookie and continue
  if (searchParams.get("desktop") === "true") {
    const response = NextResponse.next();
    response.cookies.set("prefer-desktop", "true", {
      maxAge: 60 * 60 * 24 * 30, // 30 days
      path: "/",
    });
    return response;
  }

  // If user explicitly wants mobile, clear cookie and redirect
  if (searchParams.get("mobile") === "true") {
    const url = request.nextUrl.clone();
    url.pathname = "/mobile";
    url.searchParams.delete("mobile");

    const response = NextResponse.redirect(url);
    response.cookies.delete("prefer-desktop");
    return response;
  }

  // Auto-redirect mobile users to /mobile (unless they opted out)
  if (detectMobile(request) && !preferDesktop && pathname === "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/mobile";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
