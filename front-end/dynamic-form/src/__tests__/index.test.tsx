import "@testing-library/jest-dom";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Page from "../pages/index";
import { render } from "@/testing";
import { config } from "./__mocks__/mockConfig";

const pushSpy = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: pushSpy,
    prefetch: jest.fn(),
    query: {},
    asPath: "/",
    route: "/",
  }),
}));

describe("Index page", () => {
  beforeEach(() => {
    render(<Page formData={{ formName: "personal-detail", data: config }} />);
  });

  it("renders a complete form based on config", () => {
    expect(screen.getByLabelText("First name")).toBeInTheDocument();
    expect(screen.getByLabelText("Last name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: /choose the type of insurance/i })
    ).toBeInTheDocument();
  });

  it("has values provided by the config prefilled", async () => {
    expect(screen.getByLabelText("First name")).toHaveValue("Karim");
    expect(screen.getByLabelText("Last name")).toHaveValue("Hmaissi");
    expect(screen.getByLabelText("Email")).toHaveValue("karim@email.com");
  });

  it("allows user to edit inputs & pick a dropdown option", async () => {
    await userEvent.clear(screen.getByLabelText("First name"));
    await userEvent.type(screen.getByLabelText("First name"), "Alice");
    await userEvent.clear(screen.getByLabelText("Last name"));
    await userEvent.type(screen.getByLabelText("Last name"), "Jones");

    await userEvent.click(
      screen.getByRole("combobox", { name: /choose the type of insurance/i })
    );
    await userEvent.click(
      screen.getByRole("option", { name: /car insurance/i })
    );

    expect(screen.getByLabelText("First name")).toHaveValue("Alice");
    expect(screen.getByLabelText("Last name")).toHaveValue("Jones");
    expect(
      screen.getByRole("combobox", { name: /choose the type of insurance/i })
    ).toHaveTextContent("Car insurance");
  });
});
