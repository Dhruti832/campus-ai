const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const customJestConfig = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  collectCoverageFrom: ["src/**/*.{js,jsx,ts,tsx}", "!src/app/layout.tsx"],
  coverageThreshold: {
    global: {
      lines: 90,
      statements: 90,
      branches: 80,
      functions: 90,
    },
  },
};

module.exports = createJestConfig(customJestConfig);
