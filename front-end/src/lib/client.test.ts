import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, test } from "vitest";

import { api, ApiError, isRunning } from "./client";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("ApiError", () => {
  test("with a message detail", () => {
    const error = new ApiError(404, "crawl x not found");
    expect(error.message).toBe("crawl x not found");
    expect(error.validationErrors).toEqual([]);
  });

  test("with validation errors", () => {
    const errors = [
      { loc: ["body", "max_depth"], msg: "Input should be greater than or equal to 0", type: "x" },
      { loc: ["body"], msg: "base URL must be an absolute http(s) URL", type: "value_error" },
    ];
    const error = new ApiError(422, errors);
    expect(error.validationErrors).toEqual(errors);
    expect(error.message).toBe(
      "Input should be greater than or equal to 0; base URL must be an absolute http(s) URL",
    );
  });
});

describe("api", () => {
  test("returns the JSON body", async () => {
    server.use(http.get("*/api/crawls", () => HttpResponse.json([])));
    await expect(api.listCrawls()).resolves.toEqual([]);
  });

  test("throws ApiError carrying the response's detail", async () => {
    server.use(
      http.get("*/api/crawls/x/status", () =>
        HttpResponse.json({ detail: "Crawler API is unreachable" }, { status: 502 }),
      ),
    );
    await expect(api.getStatus("x")).rejects.toMatchObject({
      status: 502,
      detail: "Crawler API is unreachable",
    });
  });

  test("handles an error response that isn't JSON", async () => {
    server.use(
      http.get(
        "*/api/crawls/x",
        () => new HttpResponse("<html>", { status: 404, statusText: "Not Found" }),
      ),
    );
    await expect(api.getCrawl("x")).rejects.toMatchObject({ status: 404, detail: "Not Found" });
  });

  test("sends paging parameters and escapes ids", async () => {
    let seen = "";
    server.use(
      http.get("*/api/crawls/:id/pages", ({ request }) => {
        const url = new URL(request.url);
        seen = url.pathname + url.search;
        return HttpResponse.json({ total: 0, offset: 50, limit: 50, items: [] });
      }),
    );
    await api.getPages("a b", 50);
    expect(seen).toBe("/api/crawls/a%20b/pages?offset=50&limit=50");
  });
});

test("isRunning", () => {
  expect(isRunning("running")).toBe(true);
  expect(isRunning("completed")).toBe(false);
  expect(isRunning(undefined)).toBe(false);
});
