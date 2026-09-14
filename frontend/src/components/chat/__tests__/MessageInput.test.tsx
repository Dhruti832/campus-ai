import { act, fireEvent, render, screen } from "@testing-library/react";

import { MessageInput } from "../MessageInput";

describe("MessageInput", () => {
  it("calls onSend with the trimmed value and clears the input", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} />);

    const input = screen.getByLabelText("Message") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "  hello there  " } });
    fireEvent.submit(screen.getByLabelText("Send a message"));

    expect(onSend).toHaveBeenCalledWith("hello there");
    expect(input.value).toBe("");
  });

  it("does not call onSend for an empty or whitespace-only value", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "   " } });
    fireEvent.submit(screen.getByLabelText("Send a message"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not call onSend when disabled", () => {
    const onSend = jest.fn();
    render(<MessageInput onSend={onSend} disabled />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "hello" } });
    fireEvent.submit(screen.getByLabelText("Send a message"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables the input and button when disabled prop is true", () => {
    render(<MessageInput onSend={jest.fn()} disabled />);

    expect(screen.getByLabelText("Message")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("does not render a voice input button when the browser has no SpeechRecognition support", () => {
    render(<MessageInput onSend={jest.fn()} />);
    expect(screen.queryByRole("button", { name: /voice input/i })).not.toBeInTheDocument();
  });

  describe("voice input", () => {
    class MockSpeechRecognition implements Partial<SpeechRecognition> {
      lang = "";
      continuous = false;
      interimResults = false;
      onresult: ((event: SpeechRecognitionEvent) => void) | null = null;
      onerror: ((event: SpeechRecognitionErrorEvent) => void) | null = null;
      onend: (() => void) | null = null;
      start = jest.fn();
      stop = jest.fn(() => {
        this.onend?.();
      });
    }

    let lastInstance: MockSpeechRecognition;

    beforeEach(() => {
      window.SpeechRecognition = jest.fn(() => {
        lastInstance = new MockSpeechRecognition();
        return lastInstance;
      }) as unknown as new () => SpeechRecognition;
    });

    afterEach(() => {
      delete (window as { SpeechRecognition?: unknown }).SpeechRecognition;
    });

    function fakeResultEvent(transcript: string): SpeechRecognitionEvent {
      return {
        resultIndex: 0,
        results: { 0: { 0: { transcript, confidence: 1 }, length: 1, isFinal: true }, length: 1 },
      } as unknown as SpeechRecognitionEvent;
    }

    it("renders a mic button when the browser supports SpeechRecognition", () => {
      render(<MessageInput onSend={jest.fn()} />);
      expect(screen.getByRole("button", { name: "Start voice input" })).toBeInTheDocument();
    });

    it("starts listening when the mic button is clicked", () => {
      render(<MessageInput onSend={jest.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: "Start voice input" }));

      expect(lastInstance.start).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Stop voice input" })).toHaveAttribute(
        "aria-pressed",
        "true"
      );
    });

    it("fills the input with the transcript as speech is recognized", () => {
      render(<MessageInput onSend={jest.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: "Start voice input" }));

      act(() => {
        lastInstance.onresult?.(fakeResultEvent("how do I deploy this"));
      });

      expect((screen.getByLabelText("Message") as HTMLInputElement).value).toBe(
        "how do I deploy this"
      );
    });

    it("stops listening when the mic button is clicked again", () => {
      render(<MessageInput onSend={jest.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: "Start voice input" }));
      fireEvent.click(screen.getByRole("button", { name: "Stop voice input" }));

      expect(lastInstance.stop).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Start voice input" })).toHaveAttribute(
        "aria-pressed",
        "false"
      );
    });

    it("stops listening when recognition reports an error", () => {
      render(<MessageInput onSend={jest.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: "Start voice input" }));

      act(() => {
        lastInstance.onerror?.({ error: "no-speech" } as SpeechRecognitionErrorEvent);
      });

      expect(screen.getByRole("button", { name: "Start voice input" })).toBeInTheDocument();
    });
  });
});
