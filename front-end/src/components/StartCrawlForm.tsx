"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import type { CrawlRequest } from "@/lib/api/types";
import { api, ApiError } from "@/lib/client";

const LIMIT_FIELDS = [
  { name: "max_pages", label: "Page budget", hint: "service default" },
  { name: "max_depth", label: "Max depth", hint: "unlimited" },
  { name: "concurrency", label: "Concurrency", hint: "service default" },
  { name: "per_host_concurrency", label: "Per-host concurrency", hint: "no limit" },
] as const;

type LimitName = (typeof LIMIT_FIELDS)[number]["name"];
type FieldName = "url" | LimitName | "allowed_hosts";
type Values = Record<FieldName, string> & { respect_robots: boolean };

const EMPTY: Values = {
  url: "",
  max_pages: "",
  max_depth: "",
  concurrency: "",
  per_host_concurrency: "",
  allowed_hosts: "",
  respect_robots: true,
};
const FIELD_NAMES = new Set<string>(["url", "allowed_hosts", ...LIMIT_FIELDS.map((f) => f.name)]);

/** "*.example.com\n docs.partner.io," -> ["*.example.com", "docs.partner.io"] */
export function parseHostList(text: string): string[] {
  return text.split(/[\s,]+/).filter((host) => host !== "");
}

/** Only the filled-in settings are sent, so the crawler API applies its own defaults. */
function toRequest(values: Values): CrawlRequest {
  const body: CrawlRequest = { url: values.url.trim(), respect_robots: values.respect_robots };
  for (const { name } of LIMIT_FIELDS) {
    if (values[name].trim() !== "") body[name] = Number(values[name]);
  }
  const hosts = parseHostList(values.allowed_hosts);
  if (hosts.length > 0) body.allowed_hosts = hosts;
  return body;
}

/** Splits a rejected request's errors into per-field messages and form-level ones. */
function splitErrors(error: unknown): { fields: Partial<Record<FieldName, string>>; general: string[] } {
  if (!(error instanceof ApiError)) return { fields: {}, general: error ? [String(error)] : [] };
  if (error.validationErrors.length === 0) return { fields: {}, general: [error.message] };
  const fields: Partial<Record<FieldName, string>> = {};
  const general: string[] = [];
  for (const { loc, msg } of error.validationErrors) {
    const field = String(loc[1] ?? "");
    if (FIELD_NAMES.has(field)) fields[field as FieldName] = msg;
    else general.push(msg);
  }
  return { fields, general };
}

export function StartCrawlForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Values>(EMPTY);

  const start = useMutation({
    mutationFn: api.startCrawl,
    onSuccess: async (crawl) => {
      await queryClient.invalidateQueries({ queryKey: ["crawls"] });
      router.push(`/crawls/${encodeURIComponent(crawl.id)}`);
    },
  });
  const errors = splitErrors(start.error);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    start.mutate(toRequest(values));
  }

  const set = (name: FieldName) => (event: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [name]: event.target.value }));
  const input =
    "w-full rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900";
  const fieldError = (name: FieldName) =>
    errors.fields[name] && (
      <p id={`${name}-error`} className="mt-1 text-sm text-red-700 dark:text-red-300">
        {errors.fields[name]}
      </p>
    );

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-label="Start a crawl"
      className="flex flex-col gap-3 rounded border border-zinc-200 p-4 dark:border-zinc-800"
    >
      <h2 className="text-lg font-semibold">Start a crawl</h2>

      {errors.general.length > 0 && (
        <div role="alert" className="text-sm text-red-700 dark:text-red-300">
          {errors.general.map((message) => (
            <p key={message}>{message}</p>
          ))}
        </div>
      )}

      <div>
        <label htmlFor="url" className="block text-sm font-medium">
          URL
        </label>
        <input
          id="url"
          name="url"
          className={input}
          placeholder="https://example.com/"
          inputMode="url"
          required
          value={values.url}
          onChange={set("url")}
          aria-invalid={Boolean(errors.fields.url)}
          aria-describedby={errors.fields.url ? "url-error" : undefined}
        />
        {fieldError("url")}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        {LIMIT_FIELDS.map(({ name, label, hint }) => (
          <div key={name}>
            <label htmlFor={name} className="block text-sm font-medium">
              {label}
            </label>
            <input
              id={name}
              name={name}
              type="number"
              className={input}
              placeholder={hint}
              value={values[name]}
              onChange={set(name)}
              aria-invalid={Boolean(errors.fields[name])}
              aria-describedby={errors.fields[name] ? `${name}-error` : undefined}
            />
            {fieldError(name)}
          </div>
        ))}
      </div>

      <div>
        <label htmlFor="allowed_hosts" className="block text-sm font-medium">
          Also follow hosts
        </label>
        <textarea
          id="allowed_hosts"
          name="allowed_hosts"
          rows={2}
          className={input}
          placeholder={"*.example.com\ndocs.partner.io"}
          value={values.allowed_hosts}
          onChange={set("allowed_hosts")}
          aria-invalid={Boolean(errors.fields.allowed_hosts)}
          aria-describedby={errors.fields.allowed_hosts ? "allowed_hosts-error" : "allowed_hosts-hint"}
        />
        <p id="allowed_hosts-hint" className="mt-1 text-xs text-zinc-500">
          One per line or comma-separated. *.example.com covers every subdomain. Links to other
          hosts are listed but not crawled.
        </p>
        {fieldError("allowed_hosts")}
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={values.respect_robots}
          onChange={(e) => setValues((v) => ({ ...v, respect_robots: e.target.checked }))}
        />
        Respect robots.txt
      </label>

      <div>
        <button
          type="submit"
          disabled={start.isPending || values.url.trim() === ""}
          className="rounded bg-zinc-900 px-4 py-1.5 text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {start.isPending ? "Starting..." : "Start crawl"}
        </button>
      </div>
    </form>
  );
}
