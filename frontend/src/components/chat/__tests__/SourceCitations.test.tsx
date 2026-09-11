import { render, screen } from "@testing-library/react";

import { SourceCitations } from "../SourceCitations";

describe("SourceCitations", () => {
  it("renders nothing when there are no sources", () => {
    const { container } = render(<SourceCitations sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a link and category for each source", () => {
    render(
      <SourceCitations
        sources={[
          { url: "https://x/a", title: "Fees Page", category: "Fees" },
          { url: "https://x/b", title: "Housing Page", category: "Housing" },
        ]}
      />
    );

    const feesLink = screen.getByRole("link", { name: "Fees Page" });
    expect(feesLink).toHaveAttribute("href", "https://x/a");
    expect(screen.getByText("Fees")).toBeInTheDocument();

    const housingLink = screen.getByRole("link", { name: "Housing Page" });
    expect(housingLink).toHaveAttribute("href", "https://x/b");
    expect(screen.getByText("Housing")).toBeInTheDocument();
  });
});
