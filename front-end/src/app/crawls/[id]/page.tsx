import { Suspense } from "react";

import { CrawlView } from "@/components/CrawlView";

export const metadata = { title: "Crawl | Crawler dashboard" };

// The id is only known at request time, so it is read inside Suspense (Cache Components).
export default function CrawlPage({ params }: PageProps<"/crawls/[id]">) {
  return (
    <Suspense fallback={<p className="text-sm">Loading crawl...</p>}>
      {params.then(({ id }) => (
        <CrawlView id={id} />
      ))}
    </Suspense>
  );
}
