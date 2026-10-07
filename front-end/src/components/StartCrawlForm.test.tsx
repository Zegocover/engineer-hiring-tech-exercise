import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { renderWithClient, serveFakeApi } from "@/test/render";

import { StartCrawlForm } from "./StartCrawlForm";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const fake = serveFakeApi();
beforeEach(() => push.mockReset());

const submit = () => userEvent.click(screen.getByRole("button", { name: "Start crawl" }));

describe("starting a crawl", () => {
  test("starts the crawl and opens its view", async () => {
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await submit();

    await waitFor(() => expect(push).toHaveBeenCalledOnce());
    const crawl = fake().crawls[0];
    expect(crawl.detail.url).toBe("https://example.com/");
    expect(push).toHaveBeenCalledWith(`/crawls/${crawl.detail.id}`);
  });

  test("sends only the URL and robots setting when limits are empty", async () => {
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await submit();

    await waitFor(() => expect(fake().started).toHaveLength(1));
    expect(fake().started[0]).toEqual({ url: "https://example.com/", respect_robots: true });
  });

  test("sends filled limits as numbers and the robots choice", async () => {
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await userEvent.type(screen.getByLabelText("Page budget"), "50");
    await userEvent.type(screen.getByLabelText("Max depth"), "2");
    await userEvent.click(screen.getByLabelText("Respect robots.txt"));
    await submit();

    await waitFor(() => expect(fake().started).toHaveLength(1));
    expect(fake().started[0]).toEqual({
      url: "https://example.com/",
      max_pages: 50,
      max_depth: 2,
      respect_robots: false,
    });
  });

  test("submit is disabled while the request is in flight", async () => {
    let release!: () => void;
    fake().holdStart = new Promise((resolve) => (release = resolve));
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await submit();

    expect(await screen.findByRole("button", { name: "Starting..." })).toBeDisabled();
    release();
    await waitFor(() => expect(push).toHaveBeenCalled());
  });

  test("submit is disabled until a URL is entered", () => {
    renderWithClient(<StartCrawlForm />);
    expect(screen.getByRole("button", { name: "Start crawl" })).toBeDisabled();
  });
});

describe("rejected requests", () => {
  test("a field error appears next to its field and values are kept", async () => {
    fake().rejectStart = [
      { loc: ["body", "max_depth"], msg: "Input should be greater than or equal to 0", type: "x" },
    ];
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await userEvent.type(screen.getByLabelText("Max depth"), "-1");
    await submit();

    const depth = screen.getByLabelText("Max depth");
    await waitFor(() => expect(depth).toHaveAttribute("aria-invalid", "true"));
    expect(depth).toHaveAccessibleDescription("Input should be greater than or equal to 0");
    expect(depth).toHaveValue(-1);
    expect(screen.getByLabelText("URL")).toHaveValue("https://example.com/");
    expect(push).not.toHaveBeenCalled();
  });

  test("an error not tied to a field appears at the top of the form", async () => {
    fake().rejectStart = [
      { loc: ["body"], msg: "base URL must be an absolute http(s) URL, got 'ftp://x/'", type: "value_error" },
    ];
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "ftp://x/");
    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "base URL must be an absolute http(s) URL, got 'ftp://x/'",
    );
    expect(screen.getByLabelText("URL")).toHaveValue("ftp://x/");
  });

  test("an unreachable crawler API is shown on the form", async () => {
    fake().failWith = 502;
    renderWithClient(<StartCrawlForm />);
    await userEvent.type(screen.getByLabelText("URL"), "https://example.com/");
    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent("Crawler API is unreachable");
  });
});
