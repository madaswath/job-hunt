// @ts-check
/**
 * Load root .env before any other module reads process.env.
 */
import { config } from 'dotenv';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '../..');
const ENV_PATH = join(REPO_ROOT, '.env');

if (existsSync(ENV_PATH)) {
  config({ path: ENV_PATH, quiet: true });
}

export { REPO_ROOT, ENV_PATH };
