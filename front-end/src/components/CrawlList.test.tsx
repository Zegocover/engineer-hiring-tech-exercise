import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { makeCrawl } from "@/test/fakeApi";
import { renderWithClient, serveFakeApi } from "@/test/render";

import { CrawlList } from "./CrawlList";

const fake = serveFakeApi();

const rows = () => screen.getAllByRole("row").slice(1); // skip the header row
const settle = () => new Promise((resolve) => setTimeout(resolve, 150)); // several poll intervals

describe("CrawlList", () => {
  test("lists crawls newest first with status, pages and errors", async () => {
    const older = makeCrawl({ url: "https://old.example/" }, 3);
    const newer = makeCrawl({ url: "https://new.example/", status: "running", finished_at: null }, 1);
    older.detail.stats.errors = 2;
    fake().add(older, newer);

    renderWithClient(<CrawlList />);

    await screen.findByText("https://new.example/");
    const [first, second] = rows();
    expect(within(first).getByRole("link")).toHaveTextContent("https://new.example/");
    expect(within(first).getByRole("link")).toHaveAttribute("href", `/crawls/${newer.detail.id}`);
    expect(first).toHaveTextContent("running");
    expect(second).toHaveTextContent("https://old.example/");
    expect(second).toHaveTextContent("completed");
    expect(within(second).getAllByRole("cell").map((c) => c.textContent)).toEqual(
      expect.arrayContaining(["3", "2"]),
    );
  });

  test("refreshes while a crawl is running", async () => {
    const crawl = makeCrawl({ status: "running", finished_at: null }, 1);
    fake().add(crawl);
    renderWithClient(<CrawlList />);
    await screen.findByText(crawl.detail.url);

    fake().progress(crawl.detail.id, 7);

    await waitFor(() => expect(rows()[0]).toHaveTextContent("7"));
  });

  test("stops refreshing when nothing is running", async () => {
    fake().add(makeCrawl({}, 2));
    renderWithClient(<CrawlList />);
    await screen.findByRole("table");

    const before = fake().count("GET /api/crawls");
    await settle();

    expect(fake().count("GET /api/crawls")).toBe(before);
  });

  test("says when no crawls have been started", async () => {
    renderWithClient(<CrawlList />);
    expect(await screen.findByText("No crawls have been started yet.")).toBeInTheDocument();
  });

  test("shows an unreachable crawler API, then recovers without a reload", async () => {
    fake().failWith = 502;
    renderWithClient(<CrawlList />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/crawler API is unreachable/i);

    fake().failWith = null;
    fake().add(makeCrawl({ url: "https://back.example/" }));

    expect(await screen.findByText("https://back.example/")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
