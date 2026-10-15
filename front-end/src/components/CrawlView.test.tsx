import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import { makeCrawl } from "@/test/fakeApi";
import { renderWithClient, serveFakeApi } from "@/test/render";

import { CrawlView } from "./CrawlView";

const fake = serveFakeApi();

const settle = () => new Promise((resolve) => setTimeout(resolve, 150)); // several poll intervals
const progress = () => screen.getByLabelText("Crawl progress");
const stat = (label: string) => {
  const term = within(progress()).getByText(label, { selector: "dt" });
  return term.nextElementSibling as HTMLElement;
};
const running = (pages = 1) => makeCrawl({ status: "running", finished_at: null }, pages);

describe("following a crawl", () => {
  test("shows details, limits and live progress", async () => {
    const crawl = running(2);
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);

    expect(await screen.findByRole("heading", { name: crawl.detail.url })).toBeInTheDocument();
    expect(stat("Pages")).toHaveTextContent("2");
    expect(within(screen.getByLabelText("Limits")).getByText("1000")).toBeInTheDocument();

    fake().progress(crawl.detail.id, 9);

    await waitFor(() => expect(stat("Pages")).toHaveTextContent("9"));
    expect(stat("Status")).toHaveTextContent("running");
  });

  test("stops polling once the crawl has finished", async () => {
    const crawl = running();
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    fake().finish(crawl.detail.id);

    await waitFor(() => expect(stat("Status")).toHaveTextContent("completed"));
    expect(stat("Finished")).not.toHaveTextContent("-");
    const statusPath = `GET /api/crawls/${crawl.detail.id}/status`;
    await settle();
    const after = fake().count(statusPath);
    await settle();
    expect(fake().count(statusPath)).toBe(after);
  });

  test("a failed crawl shows its error", async () => {
    const crawl = makeCrawl({ status: "failed", error: "could not fetch base URL https://example.com/" });
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "could not fetch base URL https://example.com/",
    );
    expect(stat("Status")).toHaveTextContent("failed");
  });

  test("an unknown crawl says so and links back", async () => {
    renderWithClient(<CrawlView id="nope" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Crawl not found.");
    expect(screen.getByRole("link", { name: "Back to all crawls" })).toHaveAttribute("href", "/");
  });

  test("an unreachable crawler API is reported", async () => {
    fake().failWith = 502;
    renderWithClient(<CrawlView id="any" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/crawler API is unreachable/i);
  });
});

describe("browsing results", () => {
  test("moving to the next page of pages", async () => {
    const crawl = makeCrawl({}, 120);
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    expect(await screen.findByText("1-50 of 120")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("51-100 of 120")).toBeInTheDocument();
    await waitFor(() => {
      const list = screen.getByRole("list", { name: "Pages" });
      expect(list).toHaveAttribute("start", "51");
      expect(list.querySelector("summary")).toHaveTextContent(`${crawl.detail.url}50 (1 links)`);
    });
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  test("the links tab lists distinct links", async () => {
    const crawl = makeCrawl({}, 4); // 3 links besides the home page
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    await userEvent.click(screen.getByRole("tab", { name: "Links" }));

    expect(screen.getByRole("tab", { name: "Links" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("1-3 of 3")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Links" })).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  test("results refresh while the crawl runs", async () => {
    const crawl = running(1);
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    expect(await screen.findByText("1-1 of 1")).toBeInTheDocument();

    fake().progress(crawl.detail.id, 3);

    expect(await screen.findByText("1-3 of 3")).toBeInTheDocument();
  });
});

describe("cancelling", () => {
  test("cancel a running crawl", async () => {
    const crawl = running(3);
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByText("1-3 of 3");

    await userEvent.click(screen.getByRole("button", { name: "Cancel crawl" }));

    await waitFor(() => expect(stat("Status")).toHaveTextContent("cancelled"));
    expect(screen.queryByRole("button", { name: "Cancel crawl" })).not.toBeInTheDocument();
    expect(screen.getByText("1-3 of 3")).toBeInTheDocument();
    const statusPath = `GET /api/crawls/${crawl.detail.id}/status`;
    await settle();
    const after = fake().count(statusPath);
    await settle();
    expect(fake().count(statusPath)).toBe(after);
  });

  test("a crawl that finishes before the cancel arrives shows its real status", async () => {
    const crawl = running(2);
    fake().add(crawl);
    fake().cancelLoses = "completed";
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    await userEvent.click(screen.getByRole("button", { name: "Cancel crawl" }));

    await waitFor(() => expect(stat("Status")).toHaveTextContent("completed"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  test("a finished crawl offers no cancel", async () => {
    const crawl = makeCrawl({}, 2);
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    expect(screen.queryByRole("button", { name: "Cancel crawl" })).not.toBeInTheDocument();
  });
});

describe("cross-domain limits", () => {
  const limitsOf = () => screen.getByLabelText("Limits");
  const limit = (label: string) =>
    within(limitsOf()).getByText(label, { selector: "dt" }).nextElementSibling as HTMLElement;

  test("the allowed hosts and per-host limit are shown", async () => {
    const crawl = makeCrawl({
      limits: {
        max_pages: 1000,
        max_depth: null,
        concurrency: 8,
        per_host_concurrency: 2,
        respect_robots: true,
        allowed_hosts: ["*.example.com", "docs.partner.io"],
      },
    });
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    expect(limit("Also follows")).toHaveTextContent("*.example.com, docs.partner.io");
    expect(limit("Per-host concurrency")).toHaveTextContent("2");
  });

  test("a crawl without allowed hosts follows the base host only", async () => {
    const crawl = makeCrawl();
    fake().add(crawl);
    renderWithClient(<CrawlView id={crawl.detail.id} />);
    await screen.findByRole("heading", { name: crawl.detail.url });

    expect(limit("Also follows")).toHaveTextContent("base host only");
    expect(limit("Per-host concurrency")).toHaveTextContent("no limit");
  });
});
