"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useRef } from "react";

import type { CrawlDetail, CrawlStatus } from "@/lib/api/types";
import { api, ApiError, isRunning } from "@/lib/client";
import { polling } from "@/lib/polling";

import { ApiErrorNotice } from "./ApiErrorNotice";
import { ResultsTabs } from "./ResultsTabs";
import { StatusBadge } from "./StatusBadge";

function statusOf(detail: CrawlDetail): CrawlStatus {
  const { id, status, started_at, finished_at, stats, error } = detail;
  return { id, status, started_at, finished_at, stats, error };
}

function formatTime(iso: string | null) {
  return iso ? <time dateTime={iso}>{new Date(iso).toLocaleString()}</time> : "-";
}

/** One crawl: details, live status while it runs, its results, and cancel. */
export function CrawlView({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const detail = useQuery({ queryKey: ["crawl", id], queryFn: () => api.getCrawl(id) });
  const status = useQuery({
    queryKey: ["crawl", id, "status"],
    queryFn: () => api.getStatus(id),
    refetchInterval: (query) => (isRunning(query.state.data?.status) ? polling.statusMs : false),
  });

  const current = status.data ?? (detail.data && statusOf(detail.data));
  const running = isRunning(current?.status);

  // When a crawl stops, refresh everything once so the final results and times are shown.
  const wasRunning = useRef(running);
  useEffect(() => {
    if (wasRunning.current && !running) {
      void queryClient.invalidateQueries({ queryKey: ["crawl", id] });
      void queryClient.invalidateQueries({ queryKey: ["crawls"] });
    }
    wasRunning.current = running;
  }, [running, id, queryClient]);

  const cancel = useMutation({
    mutationFn: () => api.cancelCrawl(id),
    onSuccess: (cancelled) => {
      queryClient.setQueryData(["crawl", id], cancelled);
      queryClient.setQueryData(["crawl", id, "status"], statusOf(cancelled));
    },
    onError: (error) => {
      // 409: it finished before the cancel arrived; show what it actually is now.
      if (error instanceof ApiError && error.status === 409) {
        void queryClient.invalidateQueries({ queryKey: ["crawl", id] });
      }
    },
  });

  const loadError = detail.error ?? status.error;
  if (loadError && !current) return <ApiErrorNotice error={loadError} />;
  if (!detail.data || !current) return <p className="text-sm">Loading crawl...</p>;

  const { url, limits } = detail.data;
  const { stats } = current;
  const showCancelError = cancel.error && !(cancel.error instanceof ApiError && cancel.error.status === 409);

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold break-all">{url}</h1>
        <StatusBadge status={current.status} />
        {running && (
          <button
            type="button"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
            className="rounded border border-red-400 px-3 py-1 text-sm text-red-700 disabled:opacity-40 dark:text-red-300"
          >
            {cancel.isPending ? "Cancelling..." : "Cancel crawl"}
          </button>
        )}
      </header>

      {loadError && <ApiErrorNotice error={loadError} />}
      {showCancelError && <ApiErrorNotice error={cancel.error} />}
      {current.error && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {current.error}
        </p>
      )}

      <dl aria-live="polite" aria-label="Crawl progress" className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <Stat label="Status" value={current.status} />
        <Stat label="Pages" value={stats.pages} />
        <Stat label="Fetched" value={stats.fetched} />
        <Stat label="Errors" value={stats.errors} />
        <Stat label="Skipped by robots.txt" value={stats.robots_skipped} />
        <Stat label="Started" value={formatTime(current.started_at)} />
        <Stat label="Finished" value={formatTime(current.finished_at)} />
      </dl>

      <dl aria-label="Limits" className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <Stat label="Page budget" value={limits.max_pages ?? "none"} />
        <Stat label="Max depth" value={limits.max_depth ?? "unlimited"} />
        <Stat label="Concurrency" value={limits.concurrency} />
        <Stat label="robots.txt" value={limits.respect_robots ? "respected" : "ignored"} />
      </dl>

      <ResultsTabs id={id} running={running} />
    </article>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-zinc-500">{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}
