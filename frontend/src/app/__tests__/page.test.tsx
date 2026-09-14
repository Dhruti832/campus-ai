import { render, screen } from "@testing-library/react";

import Home from "../page";

describe("Home page", () => {
  it("renders the header brand, the page heading, and the chat window", () => {
    render(<Home />);
    expect(screen.getByText("CampusAI")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /chat with any site's docs/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Send a message")).toBeInTheDocument();
  });

  it("renders a theme toggle", () => {
    render(<Home />);
    expect(screen.getByRole("button", { name: "Toggle theme" })).toBeInTheDocument();
  });
});
