"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";

import { api, PAGE_SIZE } from "@/lib/client";
import { polling } from "@/lib/polling";

import { ApiErrorNotice } from "./ApiErrorNotice";
import { Paginator } from "./Paginator";

type Tab = "pages" | "links";

/** Paged tabs for a crawl's pages (with their links) and its distinct links. */
export function ResultsTabs({ id, running }: { id: string; running: boolean }) {
  const [tab, setTab] = useState<Tab>("pages");
  const base = useId();
  const tabClass = (name: Tab) =>
    `rounded-t px-3 py-1.5 text-sm ${tab === name ? "border border-b-0 border-zinc-300 font-semibold dark:border-zinc-700" : "text-zinc-600 dark:text-zinc-400"}`;

  return (
    <section className="flex flex-col gap-3">
      <div role="tablist" aria-label="Crawl results" className="flex gap-1 border-b border-zinc-300 dark:border-zinc-700">
        {(["pages", "links"] as const).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            id={`${base}-${name}-tab`}
            aria-selected={tab === name}
            aria-controls={`${base}-${name}-panel`}
            className={tabClass(name)}
            onClick={() => setTab(name)}
          >
            {name === "pages" ? "Pages" : "Links"}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-${tab}-panel`} aria-labelledby={`${base}-${tab}-tab`}>
        {tab === "pages" ? <PagesTab id={id} running={running} /> : <LinksTab id={id} running={running} />}
      </div>
    </section>
  );
}

function PagesTab({ id, running }: { id: string; running: boolean }) {
  const [offset, setOffset] = useState(0);
  const pages = useQuery({
    queryKey: ["crawl", id, "pages", offset],
    queryFn: () => api.getPages(id, offset),
    placeholderData: keepPreviousData,
    refetchInterval: running ? polling.resultsMs : false,
  });

  if (pages.error) return <ApiErrorNotice error={pages.error} />;
  if (!pages.data) return <p className="text-sm">Loading pages...</p>;
  return (
    <div className="flex flex-col gap-3">
      <Paginator offset={offset} limit={PAGE_SIZE} total={pages.data.total} onChange={setOffset} label="Pages" />
      {pages.data.items.length === 0 ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">No pages reported yet.</p>
      ) : (
        <ol start={offset + 1} className="flex list-decimal flex-col gap-2 pl-8 text-sm" aria-label="Pages">
          {pages.data.items.map((page) => (
            <li key={page.url}>
              <details>
                <summary className="cursor-pointer break-all">
                  {page.url} <span className="text-zinc-500">({page.links.length} links)</span>
                </summary>
                <ul className="mt-1 list-disc pl-6 break-all text-zinc-700 dark:text-zinc-300">
                  {page.links.map((link) => (
                    <li key={link}>{link}</li>
                  ))}
                </ul>
              </details>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function LinksTab({ id, running }: { id: string; running: boolean }) {
  const [offset, setOffset] = useState(0);
  const links = useQuery({
    queryKey: ["crawl", id, "links", offset],
    queryFn: () => api.getLinks(id, offset),
    placeholderData: keepPreviousData,
    refetchInterval: running ? polling.resultsMs : false,
  });

  if (links.error) return <ApiErrorNotice error={links.error} />;
  if (!links.data) return <p className="text-sm">Loading links...</p>;
  return (
    <div className="flex flex-col gap-3">
      <Paginator offset={offset} limit={PAGE_SIZE} total={links.data.total} onChange={setOffset} label="Links" />
      {links.data.items.length === 0 ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">No links found yet.</p>
      ) : (
        <ol start={offset + 1} className="list-decimal pl-8 text-sm break-all" aria-label="Links">
          {links.data.items.map((link) => (
            <li key={link}>{link}</li>
          ))}
        </ol>
      )}
    </div>
  );
}
