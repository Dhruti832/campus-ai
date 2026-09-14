import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as adminApi from "@/lib/adminApi";

import { AdminPanel } from "../AdminPanel";

jest.mock("@/lib/adminApi", () => ({
  ...jest.requireActual("@/lib/adminApi"),
  getCorpusStats: jest.fn(),
  setActiveCorpus: jest.fn(),
  triggerIngest: jest.fn(),
  createCorpus: jest.fn(),
  deleteCorpus: jest.fn(),
  getCorpusDetail: jest.fn(),
  updateCorpus: jest.fn(),
}));

const mockedGetStats = adminApi.getCorpusStats as jest.MockedFunction<
  typeof adminApi.getCorpusStats
>;
const mockedSetActive = adminApi.setActiveCorpus as jest.MockedFunction<
  typeof adminApi.setActiveCorpus
>;
const mockedIngest = adminApi.triggerIngest as jest.MockedFunction<typeof adminApi.triggerIngest>;
const mockedCreateCorpus = adminApi.createCorpus as jest.MockedFunction<
  typeof adminApi.createCorpus
>;
const mockedDeleteCorpus = adminApi.deleteCorpus as jest.MockedFunction<
  typeof adminApi.deleteCorpus
>;
const mockedGetDetail = adminApi.getCorpusDetail as jest.MockedFunction<
  typeof adminApi.getCorpusDetail
>;
const mockedUpdateCorpus = adminApi.updateCorpus as jest.MockedFunction<
  typeof adminApi.updateCorpus
>;

const STATS = [
  {
    name: "example-docs",
    sources: 7,
    chunks: 20,
    active: true,
    thumbs_up: 0,
    thumbs_down: 0,
    editable: false,
  },
  {
    name: "example-university",
    sources: 0,
    chunks: 0,
    active: false,
    thumbs_up: 0,
    thumbs_down: 0,
    editable: true,
  },
];

function unlock(key = "secret") {
  fireEvent.change(screen.getByLabelText("Admin key"), { target: { value: key } });
  fireEvent.click(screen.getByRole("button", { name: "Unlock" }));
}

describe("AdminPanel", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    jest.clearAllMocks();
  });

  it("shows the key form initially", () => {
    render(<AdminPanel />);
    expect(screen.getByLabelText("Admin key")).toBeInTheDocument();
  });

  it("loads and displays corpus stats after unlocking with a valid key", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    render(<AdminPanel />);

    unlock();

    await waitFor(() => {
      expect(screen.getByText("example-docs")).toBeInTheDocument();
    });
    expect(screen.getByText("example-university")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(mockedGetStats).toHaveBeenCalledWith("secret");
  });

  it("shows thumbs up/down counts only when feedback exists for a corpus", async () => {
    mockedGetStats.mockResolvedValue([
      {
        name: "example-docs",
        sources: 7,
        chunks: 20,
        active: true,
        thumbs_up: 3,
        thumbs_down: 1,
        editable: false,
      },
      {
        name: "example-university",
        sources: 0,
        chunks: 0,
        active: false,
        thumbs_up: 0,
        thumbs_down: 0,
        editable: true,
      },
    ]);
    render(<AdminPanel />);

    unlock();

    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());
    expect(screen.getByText(/👍 3/)).toBeInTheDocument();
    expect(screen.getByText(/👎 1/)).toBeInTheDocument();
  });

  it("shows an error and stays on the key form for an invalid key", async () => {
    mockedGetStats.mockRejectedValue(new adminApi.AdminApiError("Invalid admin key.", 403));
    render(<AdminPanel />);

    unlock("wrong");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid admin key.");
    });
    expect(screen.getByLabelText("Admin key")).toBeInTheDocument();
  });

  it("remembers the key across remounts via sessionStorage", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    const { unmount } = render(<AdminPanel />);
    unlock();
    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());
    unmount();

    mockedGetStats.mockClear();
    mockedGetStats.mockResolvedValue(STATS);
    render(<AdminPanel />);

    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());
    expect(mockedGetStats).toHaveBeenCalledWith("secret");
  });

  it("sets a corpus active and reloads stats", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    mockedSetActive.mockResolvedValue({ active_corpus: "example-university" });
    render(<AdminPanel />);
    unlock();
    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

    const setActiveButtons = screen.getAllByRole("button", { name: "Set active" });
    fireEvent.click(setActiveButtons[1]); // the non-active row

    await waitFor(() => {
      expect(mockedSetActive).toHaveBeenCalledWith("secret", "example-university");
    });
    expect(mockedGetStats).toHaveBeenCalledTimes(2);
  });

  it("triggers ingestion and reloads stats", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    mockedIngest.mockResolvedValue({ sources_ingested: 7, chunks_ingested: 20 });
    render(<AdminPanel />);
    unlock();
    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

    fireEvent.click(screen.getAllByRole("button", { name: "Re-ingest" })[0]);

    await waitFor(() => {
      expect(mockedIngest).toHaveBeenCalledWith("secret", "example-docs");
    });
    expect(mockedGetStats).toHaveBeenCalledTimes(2);
  });

  it("disables the 'Set active' button for the already-active corpus", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    render(<AdminPanel />);
    unlock();
    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

    const setActiveButtons = screen.getAllByRole("button", { name: "Set active" });
    expect(setActiveButtons[0]).toBeDisabled();
    expect(setActiveButtons[1]).not.toBeDisabled();
  });

  describe("adding a website", () => {
    it("creates the corpus, reloads stats, and kicks off ingestion", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedCreateCorpus.mockResolvedValue({ name: "acme-docs" });
      mockedIngest.mockResolvedValue({ sources_ingested: 0, chunks_ingested: 0 });
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /add website/i }));
      fireEvent.change(screen.getByLabelText("Corpus name"), {
        target: { value: "acme-docs" },
      });
      fireEvent.change(screen.getByLabelText("Website URL"), {
        target: { value: "https://docs.acme.com" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Add and crawl" }));

      await waitFor(() => {
        expect(mockedCreateCorpus).toHaveBeenCalledWith("secret", {
          name: "acme-docs",
          websiteUrl: "https://docs.acme.com",
          persona: "",
          maxPages: 100,
        });
      });
      await waitFor(() => expect(mockedIngest).toHaveBeenCalledWith("secret", "acme-docs"));
      // Form closes and resets after a successful create.
      expect(screen.queryByLabelText("Corpus name")).not.toBeInTheDocument();
    });

    it("shows an error and keeps the form open when creation fails", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedCreateCorpus.mockRejectedValue(
        new adminApi.AdminApiError("Corpus already exists: 'acme-docs'", 400)
      );
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /add website/i }));
      fireEvent.change(screen.getByLabelText("Corpus name"), {
        target: { value: "acme-docs" },
      });
      fireEvent.change(screen.getByLabelText("Website URL"), {
        target: { value: "https://docs.acme.com" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Add and crawl" }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("Corpus already exists");
      });
      expect(screen.getByLabelText("Corpus name")).toBeInTheDocument();
      expect(mockedIngest).not.toHaveBeenCalled();
    });

    it("passes the persona and max pages fields through when filled in", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedCreateCorpus.mockResolvedValue({ name: "acme-docs" });
      mockedIngest.mockResolvedValue({ sources_ingested: 0, chunks_ingested: 0 });
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /add website/i }));
      fireEvent.change(screen.getByLabelText("Corpus name"), {
        target: { value: "acme-docs" },
      });
      fireEvent.change(screen.getByLabelText("Website URL"), {
        target: { value: "https://docs.acme.com" },
      });
      fireEvent.change(screen.getByLabelText("Persona (optional)"), {
        target: { value: "You are Acme's support bot." },
      });
      fireEvent.change(screen.getByLabelText("Max pages"), { target: { value: "250" } });
      fireEvent.click(screen.getByRole("button", { name: "Add and crawl" }));

      await waitFor(() => {
        expect(mockedCreateCorpus).toHaveBeenCalledWith("secret", {
          name: "acme-docs",
          websiteUrl: "https://docs.acme.com",
          persona: "You are Acme's support bot.",
          maxPages: 250,
        });
      });
    });

    it("closes the form on cancel without creating anything", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: /add website/i }));
      expect(screen.getByLabelText("Corpus name")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      expect(screen.queryByLabelText("Corpus name")).not.toBeInTheDocument();
      expect(mockedCreateCorpus).not.toHaveBeenCalled();
    });
  });

  describe("editing a corpus", () => {
    it("only shows an edit button for editable (admin-created) corpora", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      expect(screen.queryByRole("button", { name: "Edit example-docs" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Edit example-university" })).toBeInTheDocument();
    });

    it("loads and pre-fills the current settings when opened", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedGetDetail.mockResolvedValue({
        name: "example-university",
        website_url: "https://dal.ca",
        persona: "You are Dal's assistant.",
        max_pages: 400,
      });
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Edit example-university" }));

      await waitFor(() => {
        expect(screen.getByLabelText("Website URL")).toHaveValue("https://dal.ca");
      });
      expect(screen.getByLabelText("Persona")).toHaveValue("You are Dal's assistant.");
      expect(screen.getByLabelText("Max pages")).toHaveValue(400);
      expect(mockedGetDetail).toHaveBeenCalledWith("secret", "example-university");
    });

    it("saves the edited fields and reloads stats", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedGetDetail.mockResolvedValue({
        name: "example-university",
        website_url: "https://dal.ca",
        persona: "You are Dal's assistant.",
        max_pages: 400,
      });
      mockedUpdateCorpus.mockResolvedValue({ name: "example-university" });
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Edit example-university" }));
      await waitFor(() => expect(screen.getByLabelText("Website URL")).toHaveValue("https://dal.ca"));

      fireEvent.change(screen.getByLabelText("Max pages"), { target: { value: "500" } });
      fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

      await waitFor(() => {
        expect(mockedUpdateCorpus).toHaveBeenCalledWith("secret", "example-university", {
          websiteUrl: "https://dal.ca",
          persona: "You are Dal's assistant.",
          maxPages: 500,
        });
      });
      expect(mockedGetStats).toHaveBeenCalledTimes(2);
      expect(screen.queryByLabelText("Website URL")).not.toBeInTheDocument();
    });

    it("closes the form on cancel without saving", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedGetDetail.mockResolvedValue({
        name: "example-university",
        website_url: "https://dal.ca",
        persona: "p",
        max_pages: 400,
      });
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Edit example-university" }));
      await waitFor(() => expect(screen.getByLabelText("Website URL")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      expect(screen.queryByLabelText("Website URL")).not.toBeInTheDocument();
      expect(mockedUpdateCorpus).not.toHaveBeenCalled();
    });

    it("shows an error when saving fails", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedGetDetail.mockResolvedValue({
        name: "example-university",
        website_url: "https://dal.ca",
        persona: "p",
        max_pages: 400,
      });
      mockedUpdateCorpus.mockRejectedValue(new adminApi.AdminApiError("Bad request.", 400));
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Edit example-university" }));
      await waitFor(() => expect(screen.getByLabelText("Website URL")).toBeInTheDocument());
      fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

      await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Bad request."));
    });
  });

  describe("deleting a corpus", () => {
    it("asks for confirmation, then deletes and reloads stats", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedDeleteCorpus.mockResolvedValue({ deleted: "example-university" });
      const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Delete example-university" }));

      expect(confirmSpy).toHaveBeenCalled();
      await waitFor(() => {
        expect(mockedDeleteCorpus).toHaveBeenCalledWith("secret", "example-university");
      });
      expect(mockedGetStats).toHaveBeenCalledTimes(2);
      confirmSpy.mockRestore();
    });

    it("does not delete when the confirmation is declined", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(false);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Delete example-university" }));

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockedDeleteCorpus).not.toHaveBeenCalled();
      confirmSpy.mockRestore();
    });

    it("disables the delete button for the active corpus", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      expect(screen.getByRole("button", { name: "Delete example-docs" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Delete example-university" })).not.toBeDisabled();
    });

    it("shows an error when deletion fails", async () => {
      mockedGetStats.mockResolvedValue(STATS);
      mockedDeleteCorpus.mockRejectedValue(new adminApi.AdminApiError("No such corpus.", 404));
      const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
      render(<AdminPanel />);
      unlock();
      await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

      fireEvent.click(screen.getByRole("button", { name: "Delete example-university" }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("No such corpus.");
      });
      confirmSpy.mockRestore();
    });
  });

  it("re-fetches stats when Refresh is clicked", async () => {
    mockedGetStats.mockResolvedValue(STATS);
    render(<AdminPanel />);
    unlock();
    await waitFor(() => expect(screen.getByText("example-docs")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => expect(mockedGetStats).toHaveBeenCalledTimes(2));
  });
});
