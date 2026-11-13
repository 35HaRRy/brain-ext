import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createAdapter } from './index.js'

function harness(invoke) {
  const hooks = {}, tools = {}, sessions = new Map([
    ['s', { id: 's', location: { directory: 'C:/code/alpha' } }],
    ['other', { id: 'other', location: { directory: 'C:/other' } }],
  ])
  let disposed = 0, permissions = 0
  const ctx = {
    options: {}, location: { directory: 'C:/code/alpha' },
    session: {
      get: async ({ sessionID }) => sessions.get(sessionID),
      hook: async (kind, fn) => {
        hooks[kind] = fn
        return { dispose: async () => { disposed++ } }
      },
    },
    permission: { assert: async () => { permissions++ } },
    tool: { transform: async fn => {
      fn({ add: tool => { tools[tool.name] = tool } })
      return { dispose: async () => { disposed++ } }
    } },
  }
  return { ctx, hooks, tools, sessions, setup: () => createAdapter(ctx, { invoke }),
    disposed: () => disposed, permissions: () => permissions }
}

function result(mapping = 'unknown', project = null) {
  return { version: 1, status: 'ok', mode: project ? 'project' : 'general', project,
    records: [], context: project === 'beta' ? 'B_ONLY' : project ? 'A_ONLY' : 'GENERAL_ONLY', warnings: [],
    result: { mapping: { status: mapping, revision: 0, root: 'C:/code/alpha' } } }
}

const context = () => ({ sessionID: 's', system: [], messages: [], tools: {} })
const prompt = (text = 'hello') => ({ sessionID: 's', prompt: { text } })

test('first prompt queues onboarding once, continuations do not repeat it', async () => {
  const h = harness(async () => result())
  await h.setup()
  await h.hooks.prompt(prompt())
  const first = context()
  await h.hooks.context(first)
  assert.match(JSON.stringify(first.system), /Yeni proje/)
  const second = context()
  await h.hooks.context(second)
  assert.doesNotMatch(JSON.stringify(second.system), /Yeni proje/)
  assert.match(JSON.stringify(second.system), /GENERAL_ONLY/)
})

test('known project loads scoped context; helper never receives model-supplied session', async () => {
  const requests = []
  const h = harness(async r => { requests.push(r); return result('mapped', 'alpha') })
  await h.setup()
  await h.hooks.prompt(prompt())
  const event = context()
  await h.hooks.context(event)
  assert.match(JSON.stringify(event.system), /A_ONLY/)
  assert.doesNotMatch(JSON.stringify(event.system), /Yeni proje/)
  await h.tools.shared_memory.execute({ action: 'search', payload: {
    query: 'routing', session: { directory: 'C:/other' }, project: 'alpha',
  } }, { sessionID: 's', agent: 'build' })
  assert.equal(requests.at(-1).session.directory, 'C:/code/alpha')
})

test('skip lasts for this session, ignore survives through helper mapping', async () => {
  let ignored = false
  const h = harness(async r => {
    if (r.action === 'ignore') ignored = true
    return result(ignored ? 'ignored' : 'unknown')
  })
  await h.setup()
  await h.hooks.prompt(prompt())
  await h.tools.shared_memory.execute({ action: 'skip', payload: {} }, { sessionID: 's' })
  const event = context()
  await h.hooks.context(event)
  assert.doesNotMatch(JSON.stringify(event.system), /Yeni proje/)
  assert.match(JSON.stringify(event.system), /GENERAL_ONLY/)
  await h.tools.shared_memory.execute({ action: 'ignore', payload: { confirmed: true } },
    { sessionID: 's' })
  assert.equal(h.permissions(), 1)
  const fresh = harness(async () => result('ignored'))
  await fresh.setup()
  await fresh.hooks.prompt(prompt())
  const next = context()
  await fresh.hooks.context(next)
  assert.doesNotMatch(JSON.stringify(next.system), /Yeni proje/)
})

test('moved session drops old context and warns about retained transcript', async () => {
  const h = harness(async r => result('mapped', r.session.directory.endsWith('alpha') ? 'alpha' : 'beta'))
  await h.setup()
  await h.hooks.prompt(prompt())
  const event = context()
  await h.hooks.context(event)
  h.sessions.get('s').location.directory = 'C:/code/beta'
  h.ctx.location.directory = 'C:/code/beta'
  await h.hooks.context(event)
  const text = JSON.stringify(event.system)
  assert.doesNotMatch(text, /Proje: alpha/)
  assert.doesNotMatch(text, /A_ONLY/)
  assert.match(text, /Proje: beta/)
  assert.match(text, /yeni oturum/)
})

test('unrelated session events do not invoke helper', async () => {
  let calls = 0
  const h = harness(async () => { calls++; return result() })
  await h.setup()
  await h.hooks.prompt({ ...prompt(), sessionID: 'other' })
  await h.hooks.context({ ...context(), sessionID: 'other' })
  assert.equal(calls, 0)
})

test('child sessions do not receive registration question', async () => {
  const h = harness(async () => result())
  h.sessions.get('s').parentID = 'parent'
  h.sessions.set('parent', { id: 'parent', location: { directory: 'C:/code/alpha' } })
  await h.setup()
  await h.hooks.prompt(prompt())
  const event = context()
  await h.hooks.context(event)
  assert.doesNotMatch(JSON.stringify(event.system), /Yeni proje/)
})

test('timeout or malformed helper output clears previous context, without leaking errors', async () => {
  let fail = false
  const h = harness(async () => {
    if (fail) throw new Error('SECRET_DO_NOT_LOG')
    return result('mapped', 'alpha')
  })
  await h.setup()
  await h.hooks.prompt(prompt())
  const event = context()
  await h.hooks.context(event)
  fail = true
  await h.hooks.prompt(prompt('next'))
  await h.hooks.context(event)
  const text = JSON.stringify(event.system)
  assert.doesNotMatch(text, /A_ONLY|SECRET_DO_NOT_LOG/)
  assert.match(text, /kullanılamıyor/)
})

test('no-memory request suppresses helper and context for the turn', async () => {
  let calls = 0
  const h = harness(async () => { calls++; return result() })
  await h.setup()
  await h.hooks.prompt(prompt('no-memory: explain this code'))
  const event = context()
  await h.hooks.context(event)
  assert.equal(calls, 0)
  assert.equal(event.system.length, 0)
})

test('successful registration refreshes scope without waiting for another prompt', async () => {
  let mapped = false
  const h = harness(async r => {
    if (r.action === 'register') mapped = true
    return result(mapped ? 'mapped' : 'unknown', mapped ? 'alpha' : null)
  })
  await h.setup()
  await h.hooks.prompt(prompt())
  await h.tools.shared_memory.execute({ action: 'register', payload: { confirmed: true } },
    { sessionID: 's' })
  const event = context()
  await h.hooks.context(event)
  assert.match(JSON.stringify(event.system), /Proje: alpha/)
})

test('cleanup disposes registrations', async () => {
  const h = harness(async () => result())
  const cleanup = await h.setup()
  await cleanup()
  assert.ok(h.disposed() >= 3)
})

test('malformed or oversized helper output is never injected', async () => {
  for (const value of [{}, { ...result(), context: 'x'.repeat(25000) }]) {
    const h = harness(async () => value)
    await h.setup()
    await h.hooks.prompt(prompt())
    const event = context()
    await h.hooks.context(event)
    assert.match(JSON.stringify(event.system), /kullanılamıyor/)
    assert.ok(JSON.stringify(event.system).length < 20000)
  }
})

test('source freshness is rechecked on tool continuations without resyncing', async () => {
  let fresh = true
  const refreshes = []
  const h = harness(async request => {
    refreshes.push(request.payload.refresh)
    return { ...result('mapped', 'alpha'), context: fresh ? 'A_ONLY' : '' }
  })
  await h.setup()
  await h.hooks.prompt(prompt())
  const event = context()
  await h.hooks.context(event)
  fresh = false
  await h.hooks.context(event)
  assert.doesNotMatch(JSON.stringify(event.system), /A_ONLY/)
  assert.deepEqual(refreshes, [true, false])
})
