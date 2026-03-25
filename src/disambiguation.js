// ============================================================
// Dyad Disambiguation Engine — Phase 3
// buildDisambiguation + toConfirmationPrompt
// ============================================================

import { MARKERS } from './taxonomy.js'

// ── 3.1 buildDisambiguation ─────────────────────────────────
// Returns a structured disambiguation object ready for Q&A
export function buildDisambiguation(analysis, originalText) {
  const { issues, score, grade, hasMarker } = analysis

  // Suggest a marker if missing
  let suggestedMarker = null
  if (!hasMarker) {
    // Heuristic: if any T1/T2 issue suggests action, default to EXECUTE; else DRAFT
    const hasAction = issues.some(i => i.tier === 1 || i.tier === 2)
    suggestedMarker = hasAction ? '[DRAFT]' : '[EXECUTE]'
  }

  // Build ambiguity entries
  const ambiguities = []

  for (const issue of issues) {
    if (issue.tier === 1) {
      ambiguities.push({
        tier: 1,
        span: issue.word,
        issue: issue.issue,
        options: issue.suggestions,
        position: { start: issue.index, end: issue.index + issue.length },
        matchText: issue.matchText,
      })
    } else if (issue.tier === 2) {
      // Split the fix into meaningful options + "specify my own"
      const opts = issue.suggestions && issue.suggestions.length
        ? issue.suggestions
        : splitFixIntoOptions(issue.fix)

      ambiguities.push({
        tier: 2,
        span: issue.word,
        issue: issue.issue,
        options: opts,
        position: { start: issue.index, end: issue.index + issue.length },
        matchText: issue.matchText,
      })
    } else if (issue.tier === 3) {
      // Tier 3: offer the 6 speech act markers with descriptions
      ambiguities.push({
        tier: 3,
        span: 'missing marker',
        issue: issue.issue,
        options: MARKERS.map(m => `${m.token} — ${m.description}`),
        position: { start: -1, end: -1 },
        matchText: null,
      })
    }
  }

  return {
    originalText,
    marker: {
      present: hasMarker,
      suggested: suggestedMarker,
    },
    ambiguities,
    score,
    grade: grade.label,
  }
}

// Helper: parse a fix string like "a; b; c" or "a, b, c" into option array
function splitFixIntoOptions(fix) {
  if (!fix) return ['specify my own']
  const parts = fix.split(/[;,]/).map(s => s.trim()).filter(Boolean)
  return [...parts.slice(0, 4), 'specify my own']
}

// ── 3.2 toConfirmationPrompt ────────────────────────────────
// Renders a human-readable disambiguation prompt string
export function toConfirmationPrompt(disambiguation) {
  const { originalText, marker, ambiguities, score, grade } = disambiguation
  const lines = []

  lines.push(`Your directive: "${originalText}"`)
  lines.push('')

  if (!marker.present && marker.suggested) {
    lines.push(`\u26a0 Missing speech act marker \u2192 Suggested: ${marker.suggested}`)
    lines.push('')
  }

  for (const amb of ambiguities) {
    if (amb.tier === 3) {
      lines.push(`\u26a0 No speech act marker detected. Which best describes your intent?`)
    } else {
      lines.push(`\u26a0 "${amb.span}" \u2014 ${describeAmbiguity(amb)}`)
    }

    for (let i = 0; i < amb.options.length; i++) {
      lines.push(`  (${i + 1}) ${amb.options[i]}`)
    }
    lines.push('')
  }

  lines.push('[Confirm as-is]  [Revise]')

  return lines.join('\n')
}

function describeAmbiguity(amb) {
  if (amb.tier === 1) return 'what operation do you mean?'
  if (amb.tier === 2) return amb.issue ? amb.issue.toLowerCase() : 'please clarify'
  return 'choose speech act'
}
