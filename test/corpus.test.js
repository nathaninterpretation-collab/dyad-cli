// ============================================================
// Dyad Corpus Regression Tests — node:test
// ============================================================
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { analyzeDirective } from '../src/analyzer.js'

// ── Regression corpus
// Each entry: { text, expectation }
// Expectations based on Huang (2026) taxonomy

const corpus = [
  {
    text: 'clean this up',
    desc: 'T2 phrase fires, T1 "clean" suppressed — T1 count 0',
    check: r => r.t1.length === 0 && r.t2.length === 1,
  },
  {
    text: "don't fix the formatting",
    desc: 'Negation suppresses "fix" — 0 T1 fix issues',
    check: r => r.t1.filter(i => i.word === 'fix').length === 0,
  },
  {
    text: 'I already fixed it',
    desc: 'Completion suppresses "fixed" — 0 T1 fix issues',
    check: r => r.t1.filter(i => i.word === 'fixed').length === 0,
  },
  {
    text: 'if we fix this',
    desc: 'Conditional downgrades "fix" — penalty < 5',
    check: r => {
      const f = r.t1.find(i => i.word === 'fix')
      return f && f.adjustedPenalty < 5
    },
  },
  {
    text: 'make it better and make it better again',
    desc: '2 occurrences of "make it better" found (global scan)',
    check: r => r.t2.filter(i => i.word === 'make it better').length === 2,
  },
  {
    text: '[EXECUTE] fix the bug',
    desc: 'hasMarker true; T1 still flags "fix"',
    check: r => r.hasMarker === true && r.t1.filter(i => i.word === 'fix').length === 1,
  },
  {
    text: 'fix the report',
    desc: 'Imperative "fix" at position 0 → penalty > mid-sentence',
    check: r => {
      const fix = r.t1.find(i => i.word === 'fix')
      // position 0, first word → ×1.25 → 8 * 1.0 * 1.25 = 10
      return fix && fix.adjustedPenalty >= 9.5
    },
  },
  {
    text: 'handle the case',
    desc: 'high severity "handle" > low severity "send"',
    check: r => {
      const h = r.t1.find(i => i.word === 'handle')
      // baseline for comparison: send has severity low (0.5)
      // handle has severity high (1.0) → at pos 0: 10 vs 5
      return h && h.adjustedPenalty > 7
    },
  },
  {
    text: 'send the file',
    desc: 'low severity "send" — penalty < 7',
    check: r => {
      const s = r.t1.find(i => i.word === 'send')
      return s && s.adjustedPenalty < 7
    },
  },
  {
    text: 'take care of it and deal with this',
    desc: '2 T2 issues (global scan catches both phrases)',
    check: r => r.t2.length >= 2,
  },
  {
    text: 'look into this',
    desc: 'T2 "look into this" fires',
    check: r => r.t2.some(i => i.word === 'look into this'),
  },
  {
    text: 'do something about it',
    desc: 'T2 "do something about" fires',
    check: r => r.t2.some(i => i.word === 'do something about'),
  },
  {
    text: '[DRAFT] Write the executive summary',
    desc: 'Clear directive with marker — high score, no T3',
    check: r => r.hasMarker === true && r.t3.length === 0 && r.score >= 80,
  },
  {
    text: 'never fix the old tests',
    desc: 'Negation "never" suppresses "fix"',
    check: r => r.t1.filter(i => i.word === 'fix').length === 0,
  },
  {
    text: 'stop sending emails',
    desc: 'Negation "stop" suppresses "sending"',
    check: r => r.t1.filter(i => i.word === 'sending').length === 0,
  },
  {
    text: 'we already finished reviewing the doc',
    desc: 'Completion "already" suppresses "reviewing"',
    check: r => r.t1.filter(i => i.word === 'reviewing').length === 0,
  },
  {
    text: 'could you fix the bug',
    desc: 'Conditional "could" downgrades "fix" to penalty ≈ 3',
    check: r => {
      const f = r.t1.find(i => i.word === 'fix')
      return f && f.adjustedPenalty < 5
    },
  },
  {
    text: 'No speech act marker directive here',
    desc: 'Missing marker → T3 fires',
    check: r => r.t3.length === 1,
  },
]

for (const tc of corpus) {
  test(`Corpus: ${tc.desc}`, () => {
    const result = analyzeDirective(tc.text)
    assert.ok(
      tc.check(result),
      `Failed: "${tc.text}"\n  Score: ${result.score}, T1: ${result.t1.length}, T2: ${result.t2.length}, T3: ${result.t3.length}\n  T1 issues: ${JSON.stringify(result.t1.map(i => ({ word: i.word, penalty: i.adjustedPenalty })))}`,
    )
  })
}
