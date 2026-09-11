const { sum } = require("../src/lib/example");

test("bootstrap smoke test — proves jest + coverage + CI are wired up correctly", () => {
  expect(sum(2, 3)).toBe(5);
});
