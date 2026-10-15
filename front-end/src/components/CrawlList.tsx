"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import type { CrawlSummary } from "@/lib/api/types";
import { api, isRunning } from "@/lib/client";
import { polling } from "@/lib/polling";

import { ApiErrorNotice } from "./ApiErrorNotice";
import { StatusBadge } from "./StatusBadge";

/** Every crawl, newest first. Refreshes while any is running, or until a failed load recovers. */
export function CrawlList() {
  const crawls = useQuery({
    queryKey: ["crawls"],
    queryFn: api.listCrawls,
    refetchInterval: (query) =>
      query.state.status === "error" || query.state.data?.some((c) => isRunning(c.status))
        ? polling.listMs
        : false,
  });

  return (
    <section aria-labelledby="crawls-heading" className="flex flex-col gap-3">
      <h2 id="crawls-heading" className="text-lg font-semibold">
        All crawls
      </h2>
      {crawls.error && <ApiErrorNotice error={crawls.error} />}
      {crawls.isPending && !crawls.error && <p className="text-sm">Loading crawls...</p>}
      {crawls.data?.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">No crawls have been started yet.</p>
      )}
      {crawls.data && crawls.data.length > 0 && <CrawlTable crawls={crawls.data} />}
    </section>
  );
}

function CrawlTable({ crawls }: { crawls: CrawlSummary[] }) {
  const cell = "border-b border-zinc-200 px-2 py-1.5 dark:border-zinc-800";
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr>
          <th className={cell}>URL</th>
          <th className={cell}>Status</th>
          <th className={`${cell} text-right`}>Pages</th>
          <th className={`${cell} text-right`}>Errors</th>
          <th className={cell}>Started</th>
        </tr>
      </thead>
      <tbody>
        {crawls.map((crawl) => (
          <tr key={crawl.id}>
            <td className={`${cell} max-w-xs truncate`}>
              <Link href={`/crawls/${encodeURIComponent(crawl.id)}`} className="underline">
                {crawl.url}
              </Link>
            </td>
            <td className={cell}>
              <StatusBadge status={crawl.status} />
            </td>
            <td className={`${cell} text-right tabular-nums`}>{crawl.stats.pages}</td>
            <td className={`${cell} text-right tabular-nums`}>{crawl.stats.errors}</td>
            <td className={cell}>
              <time dateTime={crawl.started_at}>{new Date(crawl.started_at).toLocaleString()}</time>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
