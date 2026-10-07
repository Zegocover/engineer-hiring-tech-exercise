import { crawlPath, forward } from "@/lib/backend";

/** One crawl's details, including its effective limits. */
export async function GET(request: Request, ctx: RouteContext<"/api/crawls/[id]">) {
  const { id } = await ctx.params;
  return forward(request, crawlPath(id));
}

/** Cancel a running crawl. */
export async function DELETE(request: Request, ctx: RouteContext<"/api/crawls/[id]">) {
  const { id } = await ctx.params;
  return forward(request, crawlPath(id));
}
