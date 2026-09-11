import "@testing-library/jest-dom";
import { randomUUID } from "node:crypto";

// jsdom's test environment doesn't implement crypto.randomUUID.
if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis, "crypto", {
    value: { ...globalThis.crypto, randomUUID },
    configurable: true,
  });
}
