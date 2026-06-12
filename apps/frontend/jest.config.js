const nextJest = require('next/jest.js')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    // Handle module aliases (this will be automatically configured for you based on your tsconfig.json paths)
    '^@/(.*)$': '<rootDir>/$1',
    // @heroui/react publishes an `import`-only exports map Jest cannot resolve.
    '^@heroui/react$': '<rootDir>/node_modules/@heroui/react/dist/index.js',
  },
  testEnvironment: 'jest-environment-jsdom',
  testPathIgnorePatterns: ['<rootDir>/tests/e2e/'],
  // @heroui/react and the react-aria stack ship ESM-only; transpile them.
  transformIgnorePatterns: [
    '/node_modules/(?!(@heroui|react-aria|react-stately|@react-aria|@react-stately|@react-types|@internationalized|tailwind-variants|tailwind-merge|clsx)/)',
    '^.+\\.module\\.(css|sass|scss)$',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)