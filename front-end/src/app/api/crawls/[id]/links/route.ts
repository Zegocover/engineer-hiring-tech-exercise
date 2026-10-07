import { crawlPath, forward } from "@/lib/backend";

/** The distinct links a crawl has found (?offset&limit). */
export async function GET(request: Request, ctx: RouteContext<"/api/crawls/[id]/links">) {
  const { id } = await ctx.params;
  return forward(request, crawlPath(id, "/links"));
}
