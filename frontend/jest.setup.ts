import "@testing-library/jest-dom";
import { randomUUID } from "node:crypto";
import { TextDecoder, TextEncoder } from "node:util";

// jsdom doesn't implement TextEncoder/TextDecoder, needed to parse the
// NDJSON chat stream.
if (!globalThis.TextEncoder) {
  globalThis.TextEncoder = TextEncoder as typeof globalThis.TextEncoder;
}
if (!globalThis.TextDecoder) {
  globalThis.TextDecoder = TextDecoder as typeof globalThis.TextDecoder;
}

// jsdom's test environment doesn't implement crypto.randomUUID.
if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis, "crypto", {
    value: { ...globalThis.crypto, randomUUID },
    configurable: true,
  });
}

// jsdom doesn't implement Element.scrollTo.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = jest.fn();
}
