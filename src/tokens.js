/**
 * Token storage.
 *
 * Tokens live OUTSIDE the git repository, in ~/.agl-xero-bridge/, with
 * permissions that allow only the owning user account to read them.
 *
 * Two failure modes are guarded against explicitly:
 *
 *  1. Lost rotation. Xero refresh tokens are SINGLE USE - every refresh
 *     returns a new one and kills the old. If we obtained a new token and
 *     crashed before saving it, the user would be locked out and forced to
 *     re-authorise. Writes are therefore atomic (temp file + rename), so a
 *     crash can never leave a truncated or half-written token file.
 *
 *  2. Concurrent refresh. Two refreshes at once can invalidate each other.
 *     A lock directory (mkdir is atomic on POSIX) ensures only one refresh
 *     runs at a time.
 */
import { mkdirSync, readFileSync, writeFileSync, renameSync, existsSync, rmSync, chmodSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { currentCompany } from './company.js';

// Tokens live on the persistent volume (TOKEN_DIR, e.g. /data on Railway), one folder per company.
const BASE_DIR = process.env.TOKEN_DIR || join(homedir(), '.agl-cloud-reports');
const storeDir = () => join(BASE_DIR, currentCompany());
const storeFile = () => join(storeDir(), 'tokens.json');
const lockDir = () => join(storeDir(), 'refresh.lock');

export const tokenStorePath = () => storeFile();

function ensureStoreDir() {
  // 0o700 = only this user may enter/read/write the directory.
  mkdirSync(storeDir(), { recursive: true, mode: 0o700 });
  try {
    chmodSync(storeDir(), 0o700);
  } catch {
    /* best effort on unusual filesystems */
  }
}

export function hasTokens() {
  return existsSync(storeFile());
}

export function readTokens() {
  if (!existsSync(storeFile())) return null;
  try {
    return JSON.parse(readFileSync(storeFile(), 'utf8'));
  } catch (err) {
    throw new Error(
      `Token file is unreadable or corrupt: ${storeFile()}\n` +
        `Fix: delete that file and run "npm run auth" again.\n` +
        `(Underlying problem: ${err.message})`
    );
  }
}

/**
 * Write tokens atomically with 0600 permissions (owner read/write only).
 * The temp file is created with restrictive permissions BEFORE any secret
 * is written into it, so the data is never briefly world-readable.
 */
export function writeTokens(tokens) {
  ensureStoreDir();
  const tmp = `${storeFile()}.tmp.${process.pid}`;
  writeFileSync(tmp, JSON.stringify(tokens, null, 2), { mode: 0o600 });
  chmodSync(tmp, 0o600);
  renameSync(tmp, storeFile()); // atomic on the same filesystem
  chmodSync(storeFile(), 0o600);
}

/** Run `fn` while holding an exclusive lock, so refreshes cannot overlap. */
export async function withRefreshLock(fn, { timeoutMs = 20000 } = {}) {
  ensureStoreDir();
  const deadline = Date.now() + timeoutMs;

  for (;;) {
    try {
      mkdirSync(lockDir()); // atomic: fails if it already exists
      break;
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      if (Date.now() > deadline) {
        // A previous run probably crashed mid-refresh and left the lock behind.
        rmSync(lockDir(), { recursive: true, force: true });
        mkdirSync(lockDir());
        break;
      }
      await new Promise((r) => setTimeout(r, 150));
    }
  }

  try {
    return await fn();
  } finally {
    rmSync(lockDir(), { recursive: true, force: true });
  }
}
