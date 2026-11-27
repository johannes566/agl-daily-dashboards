/** 16:45 (South Africa) weekday scheduler. Switched on with ENABLE_SCHEDULE=true. RUN_ON_START=true does one test run at boot. */
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const STATE_DIR = join(process.env.TOKEN_DIR || '/tmp', 'state');
const LAST = join(STATE_DIR, 'last_run.json');

function sast() {
  const p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Africa/Johannesburg', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short', hour12: false }).formatToParts(new Date());
  const g = (t) => p.find((x) => x.type === t).value;
  return { date: `${g('year')}-${g('month')}-${g('day')}`, minutes: Number(g('hour')) * 60 + Number(g('minute')), weekday: g('weekday') };
}

function run(testOnly) {
  const child = spawn('python3', ['reports/run_daily.py'], { env: { ...process.env, TEST_ONLY: testOnly ? 'true' : 'false' } });
  child.stdout.on('data', (d) => process.stdout.write(`[report] ${d}`));
  child.stderr.on('data', (d) => process.stdout.write(`[report!] ${d}`));
  child.on('close', (c) => console.log(`[report] finished with code ${c}`));
}

export function startScheduler() {
  mkdirSync(STATE_DIR, { recursive: true });
  if (process.env.RUN_ON_START === 'true') {
    console.log('RUN_ON_START: one test run to the first recipient only');
    setTimeout(() => run(true), 15000);
  }
  if (process.env.ENABLE_SCHEDULE !== 'true') { console.log('schedule: OFF (set ENABLE_SCHEDULE=true to switch on)'); return; }
  console.log('schedule: ON, weekdays 16:45 South Africa time');
  setInterval(() => {
    const n = sast();
    if (['Sat', 'Sun'].includes(n.weekday) || n.minutes < 16 * 60 + 45 || n.minutes > 17 * 60 + 30) return;
    let last = {};
    try { if (existsSync(LAST)) last = JSON.parse(readFileSync(LAST, 'utf8')); } catch {}
    if (last.date === n.date) return;
    writeFileSync(LAST, JSON.stringify({ date: n.date, started: new Date().toISOString() }));
    console.log(`schedule: starting run for ${n.date}`);
    run(process.env.TEST_ONLY === 'true');
  }, 30000);
}
