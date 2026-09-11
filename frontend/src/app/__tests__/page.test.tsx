import { render, screen } from "@testing-library/react";

import Home from "../page";

describe("Home page", () => {
  it("renders the title and the chat window", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "DocuChat" })).toBeInTheDocument();
    expect(screen.getByLabelText("Send a message")).toBeInTheDocument();
  });
});
