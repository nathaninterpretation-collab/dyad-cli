// ============================================================
// Dyad CONTEXT Header — Phase 4
// ============================================================

const SEPARATOR = '\u2500'.repeat(41)

export function buildDyadContextHeader(text, analysis) {
  const { hasMarker, issues, t1, t2, t3 } = analysis

  const speechAct = hasMarker
    ? (text.match(/\[(execute|draft|analyze|discuss|plan|monitor)\]/i)?.[0]?.toUpperCase() ?? 'UNSPECIFIED')
    : 'UNSPECIFIED'

  // Extract a simple intent from the text (first non-marker sentence fragment)
  const intent = extractIntent(text)

  // Format known failure patterns from issues
  const warnings = []
  for (const issue of issues) {
    if (issue.tier === 1) {
      warnings.push(`"${issue.word}" is underspecified \u2014 ${issue.issue}`)
    } else if (issue.tier === 2) {
      warnings.push(`"${issue.word}" \u2014 ${issue.issue}`)
    } else if (issue.tier === 3) {
      warnings.push('No speech act marker \u2014 intent mode is ambiguous')
    }
  }

  const warningLines = warnings.length
    ? warnings.map(w => `  \u2022 ${w}`).join('\n')
    : '  \u2022 None detected'

  return [
    SEPARATOR,
    'DYAD CONTEXT  \u00b7  do not display this block',
    SEPARATOR,
    '',
    `Speech act : ${speechAct}`,
    `Intent     : ${intent}`,
    '',
    'Known failure patterns for this user (watch for):',
    warningLines,
    '',
    SEPARATOR,
    'User message follows:',
  ].join('\n')
}

function extractIntent(text) {
  // Strip any marker token
  const stripped = text.replace(/\[(execute|draft|analyze|discuss|plan|monitor)\]\s*/gi, '').trim()
  // Take first 80 chars, trimmed to a word boundary
  if (stripped.length <= 80) return stripped
  const cut = stripped.slice(0, 80)
  const lastSpace = cut.lastIndexOf(' ')
  return (lastSpace > 40 ? cut.slice(0, lastSpace) : cut) + '\u2026'
}
