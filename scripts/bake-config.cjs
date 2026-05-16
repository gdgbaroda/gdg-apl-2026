#!/usr/bin/env node
// Writes electron/build-config.json from env vars at build time, so the
// packaged app has the values baked in (env vars are not available at runtime
// of a packaged Electron app launched from the user's dock).
const fs = require('fs');
const path = require('path');

const secret = process.env.APL_HOST_SECRET || '';
const apiBase = process.env.APL_API_BASE || 'https://apl-api.gdgbaroda.com';

if (!secret) {
  console.error('APL_HOST_SECRET is required to bake build config.');
  process.exit(1);
}

const out = path.join(__dirname, '..', 'electron', 'build-config.json');
fs.writeFileSync(out, JSON.stringify({ apiBase, hostSecret: secret }, null, 2) + '\n');
console.log('Baked', out);
