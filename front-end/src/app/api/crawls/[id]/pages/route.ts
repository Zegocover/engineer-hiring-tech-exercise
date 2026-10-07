import { crawlPath, forward } from "@/lib/backend";

/** The pages a crawl has reported (?offset&limit). */
export async function GET(request: Request, ctx: RouteContext<"/api/crawls/[id]/pages">) {
  const { id } = await ctx.params;
  return forward(request, crawlPath(id, "/pages"));
}
