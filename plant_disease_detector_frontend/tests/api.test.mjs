import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/api.ts', import.meta.url), 'utf8');
let moduleId = 0;
let storage;

beforeEach(() => {
  storage = new Map();
  globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
  };
  globalThis.window = new EventTarget();
  window.setTimeout = setTimeout;
});
async function client() {
  const code = ts.transpileModule(source.replace('import.meta.env.VITE_API_BASE_URL', '""'), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64') + '#' + (++moduleId));
}
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

test('public sign-in does not send an expired access token', async () => {
  const api = await client();
  api.saveTokens('expired-access', 'refresh');
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/users/login/');
    assert.equal(options.headers.get('Authorization'), null);
    return json({ ok: true });
  };
  assert.deepEqual(await api.api('/api/users/login/', { auth: false, method: 'POST', body: '{}' }), { ok: true });
});

test('concurrent expired requests share a refresh and retry with the new token', async () => {
  const api = await client();
  api.saveTokens('old', 'refresh');
  let renewals = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith('/refresh/')) {
      renewals += 1;
      await new Promise(resolve => setImmediate(resolve));
      return json({ access: 'renewed' });
    }
    return options.headers.get('Authorization') === 'Bearer renewed' ? json({ ok: true }) : json({}, 401);
  };
  const results = await Promise.all([api.api('/api/one/'), api.api('/api/two/')]);
  assert.equal(renewals, 1);
  assert.deepEqual(results, [{ ok: true }, { ok: true }]);
});

test('an old request cannot be replayed under a different signed-in account', async () => {
  const api = await client();
  api.saveTokens('first-user', 'first-refresh');
  let finish;
  let calls = 0;
  globalThis.fetch = () => { calls += 1; return new Promise(resolve => { finish = resolve; }); };
  const pending = api.api('/api/plant_doctor_ai/analyze/', { method: 'POST' });
  api.clearSession();
  api.saveTokens('second-user', 'second-refresh');
  finish(json({}, 401));
  await assert.rejects(pending, error => error.status === 401);
  assert.equal(calls, 1);
  assert.equal(storage.get('access_token'), 'second-user');
});

test('a stale refresh cannot overwrite a new account session', async () => {
  const api = await client();
  api.saveTokens('first-user', 'first-refresh');
  let finish;
  let calls = 0;
  globalThis.fetch = url => {
    calls += 1;
    if (url.endsWith('/refresh/')) return new Promise(resolve => { finish = resolve; });
    return Promise.resolve(json({}, 401));
  };
  const pending = api.api('/api/private/');
  await new Promise(resolve => setImmediate(resolve));
  api.clearSession();
  api.saveTokens('second-user', 'second-refresh');
  finish(json({ access: 'stale-renewed' }));
  await assert.rejects(pending, error => error.status === 401);
  assert.equal(storage.get('access_token'), 'second-user');
  assert.equal(calls, 2);
});

test('validation messages from Django are shown to the user', async () => {
  const api = await client();
  globalThis.fetch = async () => json({ password: ['Use at least eight characters.'] }, 400);
  await assert.rejects(api.api('/api/users/register/', { auth: false, method: 'POST' }),
    error => error.message === 'Use at least eight characters.' && error.status === 400);
});

test('temporary refresh failure preserves credentials for retry', async () => {
  const api = await client();
  api.saveTokens('old', 'refresh');
  globalThis.fetch = async url => url.endsWith('/refresh/') ? json({}, 503) : json({}, 401);
  await assert.rejects(api.api('/api/private/'), error => error.status === 503);
  assert.equal(storage.get('refresh_token'), 'refresh');
});

test('invalid refresh clears the expired session', async () => {
  const api = await client();
  api.saveTokens('old', 'invalid-refresh');
  let loggedOut = false;
  window.addEventListener('plantdoc:logout', () => { loggedOut = true; });
  globalThis.fetch = async () => json({}, 401);
  await assert.rejects(api.api('/api/private/'));
  assert.equal(storage.get('access_token'), undefined);
  assert.equal(loggedOut, true);
});
