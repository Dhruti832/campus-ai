/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: "node",
  collectCoverageFrom: ["src/**/*.{js,jsx,ts,tsx}"],
  coverageThreshold: {
    global: {
      lines: 90,
      statements: 90,
      branches: 80,
      functions: 90,
    },
  },
};
