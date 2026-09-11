import { fireEvent, render, screen } from "@testing-library/react";

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
});
