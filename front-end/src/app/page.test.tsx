import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { renderWithClient, serveFakeApi } from "@/test/render";

import Home from "./page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
serveFakeApi();

test("home page shows the start form and the crawl list", async () => {
  renderWithClient(<Home />);
  expect(screen.getByRole("heading", { level: 1, name: "Crawls" })).toBeInTheDocument();
  expect(screen.getByRole("form", { name: "Start a crawl" })).toBeInTheDocument();
  expect(await screen.findByText("No crawls have been started yet.")).toBeInTheDocument();
});
