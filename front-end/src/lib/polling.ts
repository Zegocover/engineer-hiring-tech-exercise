// How often the dashboard refreshes while something is running, in milliseconds.
// A mutable object so tests can shorten the intervals.
export const polling = {
  /** Crawl list, while any crawl is running or the last fetch failed. */
  listMs: 2000,
  /** One crawl's status, while it is running. */
  statusMs: 1000,
  /** The shown page of a running crawl's pages or links. */
  resultsMs: 2000,
};
