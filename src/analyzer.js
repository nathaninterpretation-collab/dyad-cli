// ============================================================
// Dyad Ambiguity Analyzer — Phase 1+2 rewrite
// Huang (2026) three-tier taxonomy
// ============================================================

import {
  TIER1, TIER2, MARKERS, MARKER_REGEX, SEVERITY_MULTIPLIER,
  NEGATION_TOKENS, COMPLETION_TOKENS, CONDITIONAL_TOKENS,
} from './taxonomy.js'

// ── Helpers ─────────────────────────────────────────────────

// Tokenize: split text into an array of lowercase word strings
function tokenize(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean)
}

// Extract a 3-token window preceding the match position (by character offset)
function getPrecedingTokens(text, matchIndex, count = 3) {
  const before = text.slice(0, matchIndex).trim()
  const tokens = before.toLowerCase().split(/\s+/).filter(Boolean)
  return tokens.slice(-count)
}

// Check preceding window for negation / completion / conditional
// Returns: 'negation' | 'completion' | 'conditional' | null
function classifyContext(precedingTokens) {
  // Check multi-word negation phrases first
  const joined = precedingTokens.join(' ')
  if (/\bno need to\b/.test(joined)) return 'negation'

  for (const tok of precedingTokens) {
    if (NEGATION_TOKENS.includes(tok))   return 'negation'
    if (COMPLETION_TOKENS.includes(tok)) return 'completion'
    if (CONDITIONAL_TOKENS.includes(tok)) return 'conditional'
  }
  return null
}

// ── Position-weighted scoring ────────────────────────────────
// positionFactor = 1.0 - (matchIndex / textLength) * 0.4
// If matchIndex === 0 AND it's the first word → ×1.25 multiplier
// Otherwise apply positionFactor to adjustedPenalty
function computePositionMultiplier(matchIndex, textLength, isFirstWord) {
  if (matchIndex === 0 && isFirstWord) return 1.25
  const positionFactor = 1.0 - (matchIndex / Math.max(textLength, 1)) * 0.4
  return positionFactor
}

// ── Main export ──────────────────────────────────────────────
export function analyzeDirective(text) {
  const lower = text.toLowerCase()
  const textLength = text.length
  const issues = []

  // ── Tier 2 pass (must run before Tier 1 to enable double-count suppression)
  // Fix 1.2: use global regex to find ALL match positions (not indexOf first-only)
  for (const pattern of TIER2) {
    const escaped = pattern.phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(escaped, 'gi')
    const matches = [...lower.matchAll(re)]
    for (const m of matches) {
      issues.push({
        tier: 2,
        word: pattern.phrase,
        matchText: text.substring(m.index, m.index + pattern.phrase.length),
        index: m.index,
        length: pattern.phrase.length,
        issue: pattern.issue,
        fix: pattern.fix,
        suggestions: pattern.options || [],
        adjustedPenalty: 12,
      })
    }
  }

  // Build a set of [index, index+length) ranges covered by Tier 2 matches
  // (used to suppress overlapping Tier 1 matches — Fix 1.1)
  const tier2Ranges = issues.map(i => ({ start: i.index, end: i.index + i.length }))

  function isCoveredByTier2(idx) {
    return tier2Ranges.some(r => idx >= r.start && idx < r.end)
  }

  // ── Tier 1 pass
  for (const pattern of TIER1) {
    const severityMult = SEVERITY_MULTIPLIER[pattern.severity] ?? 1.0
    const basePenalty = 8

    for (const word of pattern.words) {
      const re = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
      const matches = [...text.matchAll(re)]

      for (const m of matches) {
        const idx = m.index

        // Fix 1.1: suppress if Tier 2 covers this position
        if (isCoveredByTier2(idx)) continue

        // Fix 1.3: check 3-token preceding window for negation/completion/conditional
        const preceding = getPrecedingTokens(text, idx)
        const ctx = classifyContext(preceding)

        if (ctx === 'negation' || ctx === 'completion') continue  // suppress

        // Compute penalty
        let adjustedPenalty = basePenalty * severityMult

        if (ctx === 'conditional') {
          adjustedPenalty = 3  // downgrade
        }

        // Phase 2.1: position weighting
        const firstWord = tokenize(text)[0]
        const isFirstWord = (idx === 0) && (firstWord === m[0].toLowerCase())
        const posMult = computePositionMultiplier(idx, textLength, isFirstWord)
        adjustedPenalty = adjustedPenalty * posMult

        if (!issues.find(i => i.tier === 1 && i.word === word && i.index === idx)) {
          issues.push({
            tier: 1,
            word,
            matchText: m[0],
            index: idx,
            length: m[0].length,
            issue: `"${word}" distributes across: ${pattern.suggestions.slice(0, 3).join(', ')}, and more`,
            suggestions: pattern.suggestions,
            fix: null,
            adjustedPenalty,
            severity: pattern.severity,
          })
        }
      }
    }
  }

  // ── Tier 3
  const hasMarker = MARKER_REGEX.test(text)
  if (!hasMarker) {
    issues.push({
      tier: 3,
      word: 'No speech act marker',
      matchText: null,
      index: -1,
      length: 0,
      issue: 'Agent must guess between EXECUTE / DRAFT / ANALYZE / DISCUSS / PLAN / MONITOR — identical surface forms.',
      fix: 'Prepend one of: ' + MARKERS.map(m => m.token).join('  '),
      suggestions: MARKERS.map(m => `${m.token} — ${m.description}`),
      adjustedPenalty: 18,
    })
  }

  // ── Score
  let score = 100
  for (const issue of issues) {
    score -= issue.adjustedPenalty
  }
  if (hasMarker) score += 8
  score = Math.max(0, Math.min(100, score))

  const t1 = issues.filter(i => i.tier === 1)
  const t2 = issues.filter(i => i.tier === 2)
  const t3 = issues.filter(i => i.tier === 3)

  return {
    score,
    grade: gradeLabel(score),
    issues,
    t1, t2, t3,
    hasMarker,
    wordCount: text.trim().split(/\s+/).filter(Boolean).length,
    rewrite: buildRewrite(text, issues, hasMarker),
  }
}

function gradeLabel(score) {
  if (score >= 90) return { label: 'Excellent',        ansi: '\x1b[32m' }
  if (score >= 75) return { label: 'Good',             ansi: '\x1b[32m' }
  if (score >= 60) return { label: 'Needs Work',       ansi: '\x1b[33m' }
  if (score >= 40) return { label: 'High Ambiguity',   ansi: '\x1b[31m' }
  return               { label: 'Critical Ambiguity', ansi: '\x1b[31m' }
}

function buildRewrite(text, issues, hasMarker) {
  let out = text
  if (!hasMarker) out = '[DRAFT] ' + out
  const t2 = issues.filter(i => i.tier === 2 && i.fix)
  for (const issue of t2) {
    out = out.replace(
      new RegExp(issue.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'),
      issue.fix,
    )
  }
  const t1 = issues.filter(i => i.tier === 1)
  if (t1.length > 0) {
    const hints = t1.slice(0, 2)
      .map(i => `"${i.word}" = [specify: ${i.suggestions.slice(0, 2).join(' or ')}]`)
      .join(' · ')
    out += `\n\n// Scope clarifications needed: ${hints}`
  }
  return out
}
