import { crawlPath, forward } from "@/lib/backend";

/** A crawl's status and statistics, for polling. */
export async function GET(request: Request, ctx: RouteContext<"/api/crawls/[id]/status">) {
  const { id } = await ctx.params;
  return forward(request, crawlPath(id, "/status"));
}
