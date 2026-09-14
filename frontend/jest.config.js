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

module.exports = async () => {
  const nextJestConfig = await createJestConfig(customJestConfig)();
  return {
    ...nextJestConfig,
    // react-markdown/remark-gfm and their unified/mdast-* dependency chain
    // ship as pure ESM with no CJS build. next/jest hardcodes its own
    // transformIgnorePatterns and overwrites any value passed into
    // createJestConfig() above, so it has to be set here instead, after
    // next/jest has already produced its config. The SWC transform next/jest
    // wires up handles ESM syntax fine — it just needs to actually run over
    // these packages instead of skipping all of node_modules.
    transformIgnorePatterns: [],
  };
};
