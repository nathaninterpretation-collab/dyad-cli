// ============================================================
// Dyad Terminal Display — ANSI, zero dependencies
// ============================================================

const R = '\x1b[0m'       // reset
const BOLD = '\x1b[1m'
const DIM = '\x1b[2m'
const RED = '\x1b[31m'
const YEL = '\x1b[33m'
const GRN = '\x1b[32m'
const BLU = '\x1b[34m'
const CYN = '\x1b[36m'
const WHT = '\x1b[37m'
const BG_DARK = '\x1b[40m'

const W = process.stdout.columns || 72

function line(char = '─') { return char.repeat(W) }
function pad(str, width) { return str + ' '.repeat(Math.max(0, width - stripAnsi(str).length)) }

function stripAnsi(str) {
  return str.replace(/\x1b\[[0-9;]*m/g, '')
}

function scoreBar(score) {
  const filled = Math.round(score / 100 * 20)
  const bar = '█'.repeat(filled) + '░'.repeat(20 - filled)
  const color = score >= 75 ? GRN : score >= 50 ? YEL : RED
  return `${color}${bar}${R} ${BOLD}${score}/100${R}`
}

function tierTag(tier) {
  if (tier === 1) return `${YEL}${BOLD}[T1]${R}`
  if (tier === 2) return `${RED}${BOLD}[T2]${R}`
  if (tier === 3) return `${BLU}${BOLD}[T3]${R}`
  return ''
}

export function renderAnalysis(text, result) {
  const lines = []

  lines.push('')
  lines.push(`${BOLD}${CYN}  ╔${'═'.repeat(W - 4)}╗${R}`)
  lines.push(`${BOLD}${CYN}  ║${R}${BOLD}  DYAD  ·  Directive Analysis${' '.repeat(W - 34)}${CYN}║${R}`)
  lines.push(`${BOLD}${CYN}  ╚${'═'.repeat(W - 4)}╝${R}`)
  lines.push('')

  // Score
  const { score, grade } = result
  lines.push(`  Score   ${scoreBar(score)}`)
  lines.push(`  Grade   ${grade.ansi}${BOLD}${grade.label}${R}`)
  lines.push('')

  // Original
  lines.push(`  ${DIM}Your directive:${R}`)
  lines.push(`  ${DIM}"${text}"${R}`)
  lines.push('')

  // Issues
  if (result.issues.length === 0) {
    lines.push(`  ${GRN}✓ No ambiguity issues detected.${R}`)
  } else {
    lines.push(`  ${BOLD}Issues Found  (${result.t1.length} T1 · ${result.t2.length} T2 · ${result.t3.length} T3)${R}`)
    lines.push(`  ${DIM}${'─'.repeat(W - 4)}${R}`)
    for (const issue of result.issues) {
      lines.push('')
      lines.push(`  ${tierTag(issue.tier)}  ${BOLD}"${issue.word}"${R}`)
      lines.push(`         ${issue.issue}`)
      if (issue.fix) {
        lines.push(`         ${GRN}→ Fix:${R} ${issue.fix}`)
      } else if (issue.suggestions?.length) {
        lines.push(`         ${GRN}→ Specify:${R} ${issue.suggestions.slice(0,3).join(' · ')}`)
      }
    }
  }

  lines.push('')
  lines.push(`  ${DIM}${'─'.repeat(W - 4)}${R}`)

  // Rewrite
  if (result.score < 90) {
    lines.push('')
    lines.push(`  ${BOLD}Suggested Rewrite${R}  ${DIM}(estimated score: ~${Math.min(100, result.score + 30)})${R}`)
    lines.push(`  ${DIM}${'─'.repeat(W - 4)}${R}`)
    const rewriteLines = result.rewrite.split('\n')
    for (const l of rewriteLines) {
      lines.push(`  ${GRN}${l}${R}`)
    }
    lines.push(`  ${DIM}${'─'.repeat(W - 4)}${R}`)
  }

  lines.push('')
  return lines.join('\n')
}

export function renderMenu(hasRewrite) {
  const opts = hasRewrite
    ? `  ${BOLD}(1)${R} Use rewrite   ${BOLD}(2)${R} Send original   ${BOLD}(3)${R} Copy rewrite to clipboard   ${BOLD}(4)${R} Quit`
    : `  ${BOLD}(1)${R} Send original   ${BOLD}(2)${R} Copy to clipboard   ${BOLD}(3)${R} Quit`
  return `\n${opts}\n\n  ${DIM}›${R} `
}

export function renderHookWarning(text, result) {
  const lines = []
  lines.push('')
  lines.push(`┌─ DYAD ─────────────────────────────────────────────────────`)
  lines.push(`│  Directive score: ${result.score}/100  ·  ${result.grade.label}`)
  if (result.t1.length) lines.push(`│  T1 vague verbs : ${result.t1.map(i => `"${i.word}"`).join(', ')}`)
  if (result.t2.length) lines.push(`│  T2 phrases     : ${result.t2.map(i => `"${i.word}"`).join(', ')}`)
  if (result.t3.length) lines.push(`│  T3             : Missing speech act marker`)
  lines.push(`│`)
  lines.push(`│  Rewrite suggestion:`)
  lines.push(`│  ${result.rewrite.split('\n')[0]}`)
  lines.push(`└────────────────────────────────────────────────────────────`)
  lines.push('')
  return lines.join('\n')
}
