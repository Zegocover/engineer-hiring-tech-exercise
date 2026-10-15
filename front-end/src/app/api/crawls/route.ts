// The dashboard's API for the crawl list. Each handler forwards to the crawler API.
import { forward } from "@/lib/backend";

/** List crawls, newest first. */
export async function GET(request: Request) {
  return forward(request, "/crawls");
}

/** Start a crawl. */
export async function POST(request: Request) {
  return forward(request, "/crawls");
}
