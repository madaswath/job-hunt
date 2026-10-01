#!/usr/bin/env node
/**
 * Apply supabase/migrations/*.sql in order via node-postgres.
 *
 * Connection (first match wins):
 *   SUPABASE_DATABASE_URL or DATABASE_URL
 *   or SUPABASE_DB_PASSWORD + SUPABASE_URL (builds direct Postgres URI)
 */
import pg from 'pg';
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from 'dotenv';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
config({ path: join(root, '.env'), quiet: true });

/** @param {string} supabaseUrl */
function projectRefFromUrl(supabaseUrl) {
  try {
    const m = new URL(supabaseUrl).hostname.match(/^([a-z0-9]+)\.supabase\.co$/i);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function resolveDatabaseUrl() {
  const direct = process.env.SUPABASE_DATABASE_URL || process.env.DATABASE_URL;
  if (direct?.includes('postgresql://')) return direct;

  const password = process.env.SUPABASE_DB_PASSWORD;
  const ref =
    process.env.SUPABASE_PROJECT_REF ||
    projectRefFromUrl(process.env.SUPABASE_URL || '') ||
    'btinlwtseqtnznublasj';

  if (password) {
    const encoded = encodeURIComponent(password);
    return `postgresql://postgres:${encoded}@db.${ref}.supabase.co:5432/postgres`;
  }
  return null;
}

const dbUrl = resolveDatabaseUrl();

if (!dbUrl) {
  console.error(`
Cannot connect to Postgres — add ONE of these to root .env:

  SUPABASE_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.btinlwtseqtnznublasj.supabase.co:5432/postgres

  — or —

  SUPABASE_DB_PASSWORD=your_database_password

(Database password: Supabase Dashboard → Project Settings → Database)

Percent-encode special characters in the full URL if using SUPABASE_DATABASE_URL.
`);
  process.exit(1);
}

const migrationsDir = join(root, 'supabase', 'migrations');
const files = readdirSync(migrationsDir)
  .filter((f) => f.endsWith('.sql'))
  .sort();

const client = new pg.Client({
  connectionString: dbUrl,
  ssl: { rejectUnauthorized: false },
});

console.log(`Applying ${files.length} migrations…\n`);

try {
  await client.connect();
  for (const file of files) {
    const path = join(migrationsDir, file);
    const sql = readFileSync(path, 'utf8');
    console.log(`→ ${file}`);
    await client.query(sql);
  }
  console.log('\nDone.');
} catch (err) {
  console.error('\nMigration failed:', err.message);
  process.exit(1);
} finally {
  await client.end().catch(() => {});
}
