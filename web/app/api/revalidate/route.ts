import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";

/** Called by the pipeline after it publishes, so pages show the new data on the next visit. */
export async function POST(request: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret || request.headers.get("x-revalidate-secret") !== secret) {
    return Response.json({ revalidated: false }, { status: 401 });
  }
  // expire: 0 -> the next request renders with fresh data instead of serving the stale page.
  revalidateTag("gold", { expire: 0 });
  return Response.json({ revalidated: true });
}
