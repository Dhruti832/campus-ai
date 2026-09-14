import { render, screen } from "@testing-library/react";

import AdminPage from "../page";

describe("Admin page", () => {
  it("renders the heading and the key form", () => {
    render(<AdminPage />);
    expect(screen.getByRole("heading", { name: "CampusAI Admin" })).toBeInTheDocument();
    expect(screen.getByLabelText("Admin key")).toBeInTheDocument();
  });

  it("renders the site header with a link back to chat and a theme toggle", () => {
    render(<AdminPage />);
    expect(screen.getByRole("link", { name: /campusai/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("button", { name: "Toggle theme" })).toBeInTheDocument();
  });
});
