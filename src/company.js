/** Per-company context, so BCS and BPOS each use their own tokens in one process. */
import { AsyncLocalStorage } from 'node:async_hooks';
const als = new AsyncLocalStorage();
export const COMPANIES = ['bcs', 'bpos'];
export function withCompany(name, fn) {
  if (!COMPANIES.includes(name)) throw new Error(`Unknown company: ${name}`);
  return als.run(name, fn);
}
export function currentCompany() {
  return als.getStore() || 'bcs';
}
