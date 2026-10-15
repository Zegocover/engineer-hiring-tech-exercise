import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ApiError } from "@/lib/client";

import { ApiErrorNotice } from "./ApiErrorNotice";
import { Paginator } from "./Paginator";
import { StatusBadge } from "./StatusBadge";

test("StatusBadge shows the status", () => {
  render(<StatusBadge status="running" />);
  expect(screen.getByText("running")).toBeInTheDocument();
});

describe("Paginator", () => {
  test("middle page: range and both controls enabled", async () => {
    const onChange = vi.fn();
    render(<Paginator offset={50} limit={50} total={120} onChange={onChange} label="pages" />);

    expect(screen.getByText("51-100 of 120")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onChange.mock.calls).toEqual([[100], [0]]);
  });

  test("first page: previous disabled", () => {
    render(<Paginator offset={0} limit={50} total={120} onChange={() => {}} label="pages" />);
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  test("last page: next disabled, range clipped to total", () => {
    render(<Paginator offset={100} limit={50} total={120} onChange={() => {}} label="pages" />);
    expect(screen.getByText("101-120 of 120")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  test("empty: 0-0 of 0, both disabled", () => {
    render(<Paginator offset={0} limit={50} total={0} onChange={() => {}} label="links" />);
    expect(screen.getByText("0-0 of 0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });
});

describe("ApiErrorNotice", () => {
  test("unreachable crawler API", () => {
    render(<ApiErrorNotice error={new ApiError(502, "Crawler API is unreachable")} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/crawler API is unreachable/i);
  });

  test("not found links back to the list", () => {
    render(<ApiErrorNotice error={new ApiError(404, "crawl x not found")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Crawl not found.");
    expect(screen.getByRole("link", { name: "Back to all crawls" })).toHaveAttribute("href", "/");
  });

  test("other errors show their message", () => {
    render(<ApiErrorNotice error={new ApiError(409, "crawl x is already completed")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("crawl x is already completed");
  });
});
