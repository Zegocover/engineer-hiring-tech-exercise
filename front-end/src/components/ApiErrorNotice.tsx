import Link from "next/link";

import { ApiError } from "@/lib/client";

/** Explains a failed request: crawler API down, crawl not found, or the API's own message. */
export function ApiErrorNotice({ error }: { error: Error }) {
  let message = error.message;
  let backLink = false;

  if (error instanceof ApiError && error.status === 502) {
    message =
      "The crawler API is unreachable. Check that it is running and that the dashboard's " +
      "CRAWLER_API_URL points at it; this page will recover once it is back.";
  } else if (error instanceof ApiError && error.status === 404) {
    message = "Crawl not found.";
    backLink = true;
  }

  return (
    <div
      role="alert"
      className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100"
    >
      <p>{message}</p>
      {backLink && (
        <p className="mt-2">
          <Link href="/" className="underline">
            Back to all crawls
          </Link>
        </p>
      )}
    </div>
  );
}
