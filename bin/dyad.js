#!/usr/bin/env node
// ============================================================
// Dyad CLI — Multiple-choice interactive directive analyzer
// Usage:
//   dyad "fix my auth and make it better"
//   dyad --filter "text"          ← block/annotate/pass + header
//   dyad --json "text"            ← JSON output for piping
//   dyad --quiet "text"           ← resolved text only
//   echo "text" | dyad            ← stdin pipe
// ============================================================

import { createInterface } from 'readline'
import { execSync } from 'child_process'
import { analyzeDirective } from '../src/analyzer.js'
import { buildDisambiguation } from '../src/disambiguation.js'
import { filterDirective, FILTER_CONFIG } from '../src/filter.js'
import { renderAnalysis } from '../src/display.js'

// ── ANSI helpers ────────────────────────────────────────────
const R    = '\x1b[0m'
const BOLD = '\x1b[1m'
const DIM  = '\x1b[2m'
const GRN  = '\x1b[32m'
const YEL  = '\x1b[33m'
const RED  = '\x1b[31m'
const CYN  = '\x1b[36m'

// ── Get input ───────────────────────────────────────────────
async function getInput(flags) {
  // 1. From CLI args (non-flag)
  const args = process.argv.slice(2).filter(a => !a.startsWith('--'))
  if (args.length > 0) return args.join(' ')

  // 2. From stdin pipe
  if (!process.stdin.isTTY) {
    return new Promise(resolve => {
      let data = ''
      process.stdin.setEncoding('utf8')
      process.stdin.on('data', chunk => { data += chunk })
      process.stdin.on('end', () => resolve(data.trim()))
    })
  }

  // 3. Interactive prompt
  const rl = createInterface({ input: process.stdin, output: process.stdout })
  return new Promise(resolve => {
    process.stdout.write(`\n  ${BOLD}Dyad${R}  ${DIM}Paste your directive (press Enter twice to analyze):${R}\n\n  ${DIM}\u203a${R} `)
    let text = '', lastEmpty = false
    rl.on('line', line => {
      if (line === '' && lastEmpty) { rl.close(); resolve(text.trim()); return }
      lastEmpty = line === ''
      text += (text ? '\n' : '') + line
    })
  })
}

// ── Clipboard ───────────────────────────────────────────────
function copyToClipboard(text) {
  try {
    const p = process.platform
    if (p === 'win32')        execSync('clip',                      { input: text, stdio: ['pipe','ignore','ignore'] })
    else if (p === 'darwin')  execSync('pbcopy',                    { input: text, stdio: ['pipe','ignore','ignore'] })
    else                      execSync('xclip -selection clipboard', { input: text, stdio: ['pipe','ignore','ignore'] })
    return true
  } catch { return false }
}

// ── Score bar ───────────────────────────────────────────────
function scoreBar(score) {
  const filled = Math.round(score / 100 * 20)
  const bar = '\u2588'.repeat(filled) + '\u2591'.repeat(20 - filled)
  const color = score >= 75 ? GRN : score >= 50 ? YEL : RED
  return `${color}${bar}${R} ${BOLD}${score}/100${R}`
}

// ── Tier tag ────────────────────────────────────────────────
function tierTag(tier) {
  if (tier === 1) return `${YEL}${BOLD}[T1] Lexical${R}`
  if (tier === 2) return `${RED}${BOLD}[T2] Idiomatic${R}`
  if (tier === 3) return `${CYN}${BOLD}[T3] Missing Marker${R}`
  return ''
}

// ── Ask a single numbered-choice question ───────────────────
function askChoice(question, options) {
  return new Promise(resolve => {
    const rl = createInterface({ input: process.stdin, output: process.stdout })

    let prompt = `\n  ${BOLD}${question}${R}\n\n`
    options.forEach((opt, i) => {
      prompt += `    ${BOLD}(${i + 1})${R} ${opt}\n`
    })
    prompt += `\n  ${DIM}\u203a${R} `

    process.stdout.write(prompt)

    rl.once('line', answer => {
      rl.close()
      const n = parseInt(answer.trim(), 10)
      if (n >= 1 && n <= options.length) {
        resolve({ index: n - 1, value: options[n - 1] })
      } else {
        // Default to first option on invalid input
        resolve({ index: 0, value: options[0] })
      }
    })
  })
}

// ── Ask for custom text ─────────────────────────────────────
function askFreeText(prompt) {
  return new Promise(resolve => {
    const rl = createInterface({ input: process.stdin, output: process.stdout })
    process.stdout.write(`  ${DIM}${prompt}${R} `)
    rl.once('line', line => { rl.close(); resolve(line.trim()) })
  })
}

// ── Run multiple-choice disambiguation Q&A ──────────────────
async function runDisambiguationQA(text, analysis) {
  const disambiguation = buildDisambiguation(analysis, text)
  const { ambiguities, score, grade } = disambiguation

  if (ambiguities.length === 0) {
    process.stdout.write(`\n  ${GRN}\u2713 Directive is clear. Proceed as-is.${R}\n\n`)
    return text
  }

  // ── Header banner
  const W = Math.min(process.stdout.columns || 72, 72)
  const innerW = W - 4
  process.stdout.write('\n')
  process.stdout.write(`  ${BOLD}${CYN}\u2554${'═'.repeat(innerW)}\u2557${R}\n`)
  process.stdout.write(`  ${BOLD}${CYN}\u2551${R}${BOLD}  DYAD  \u00b7  Directive Analysis${' '.repeat(innerW - 30)}${CYN}\u2551${R}\n`)
  process.stdout.write(`  ${BOLD}${CYN}\u255a${'═'.repeat(innerW)}\u255d${R}\n`)
  process.stdout.write('\n')

  process.stdout.write(`  Score   ${scoreBar(score)}\n`)
  process.stdout.write(`  Grade   ${analysis.grade.ansi}${BOLD}${grade}${R}\n`)
  process.stdout.write('\n')
  process.stdout.write(`  ${BOLD}${ambiguities.length} ambiguit${ambiguities.length === 1 ? 'y' : 'ies'} detected. Let\u2019s resolve them.${R}\n`)
  process.stdout.write(`  ${'─'.repeat(innerW)}\n`)

  // Build a mutable copy of the text for substitutions
  let resolvedText = text
  const substitutions = []  // { original, replacement, position }

  for (let qi = 0; qi < ambiguities.length; qi++) {
    const amb = ambiguities[qi]
    process.stdout.write('\n')
    process.stdout.write(`  ${DIM}Question ${qi + 1} of ${ambiguities.length}  \u00b7  ${tierTag(amb.tier)}${R}\n`)
    process.stdout.write(`  ${'─'.repeat(innerW)}\n`)

    let question
    if (amb.tier === 3) {
      question = 'What speech act best describes your intent?'
    } else {
      question = `You said "${amb.span}" — what operation do you mean?`
    }

    const options = [...amb.options]

    // Add "skip — it's clear from context" for T1 if not present
    if (amb.tier === 1 && !options.some(o => /skip/i.test(o))) {
      options.push("skip — it's clear from context")
    }

    const { index: choiceIdx, value: choiceVal } = await askChoice(question, options)

    // Handle "specify my own" or "skip"
    let resolution = choiceVal
    if (/specify my own/i.test(choiceVal)) {
      resolution = await askFreeText('Type your clarification:')
    } else if (/skip/i.test(choiceVal)) {
      resolution = null  // no substitution
    }

    if (resolution !== null && amb.tier !== 3) {
      substitutions.push({
        span: amb.span,
        replacement: resolution,
        position: amb.position,
      })
    }

    if (amb.tier === 3 && resolution !== null) {
      // Extract marker token like [DRAFT] from "token — description"
      const markerMatch = resolution.match(/\[([A-Z]+)\]/)
      if (markerMatch) {
        resolvedText = `${markerMatch[0]} ${resolvedText}`
      }
    }

    process.stdout.write(`  ${GRN}\u2713 Got it: ${resolution ?? 'skipped'}${R}\n`)
  }

  // Apply substitutions (longest-span-first to avoid offset drift)
  substitutions.sort((a, b) => b.span.length - a.span.length)
  for (const sub of substitutions) {
    const escaped = sub.span.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    resolvedText = resolvedText.replace(new RegExp(escaped, 'gi'), sub.replacement)
  }

  return resolvedText
}

// ── Filter mode display ─────────────────────────────────────
function showFilterResult(result, originalText) {
  const { action, payload, analysis } = result

  if (action === 'block') {
    process.stdout.write(`\n  ${RED}${BOLD}\u26d4 BLOCKED${R}  Score ${analysis.score}/100 is below threshold (${FILTER_CONFIG.strictThreshold})\n`)
    process.stdout.write(`\n  ${DIM}Resolve ambiguities or append ${BOLD}//!force${R}${DIM} to override.${R}\n\n`)
    process.stdout.write(renderAnalysis(originalText, analysis))
  } else if (action === 'annotate') {
    process.stdout.write(`\n  ${YEL}${BOLD}\u26a0 ANNOTATED${R}  Score ${analysis.score}/100 — DYAD CONTEXT header prepended\n\n`)
    process.stdout.write(`${DIM}${payload}${R}\n`)
  } else {
    process.stdout.write(`\n  ${GRN}${BOLD}\u2713 PASS${R}  Score ${analysis.score}/100\n\n`)
    if (result.forced) {
      process.stdout.write(`  ${DIM}Force override applied. Token stripped.${R}\n`)
    }
    process.stdout.write(`  ${payload}\n`)
  }
}

// ── Main ────────────────────────────────────────────────────
async function main() {
  const flags = process.argv.slice(2)
  const jsonMode   = flags.includes('--json')
  const quietMode  = flags.includes('--quiet')
  const filterMode = flags.includes('--filter')

  const text = await getInput(flags)

  if (!text) {
    console.error('No directive provided.')
    process.exit(1)
  }

  // ── JSON mode
  if (jsonMode) {
    const result = analyzeDirective(text)
    console.log(JSON.stringify({
      score:  result.score,
      grade:  result.grade.label,
      issues: result.issues.length,
      t1:     result.t1.length,
      t2:     result.t2.length,
      t3:     result.t3.length,
      hasMarker: result.hasMarker,
      rewrite: result.rewrite,
    }))
    process.exit(result.score < 60 ? 1 : 0)
  }

  // ── Quiet mode
  if (quietMode) {
    const result = analyzeDirective(text)
    if (result.score < 75) {
      console.log(result.rewrite)
    } else {
      console.log(text)
    }
    process.exit(0)
  }

  // ── Filter mode
  if (filterMode) {
    const result = filterDirective(text, FILTER_CONFIG, {})
    showFilterResult(result, text)
    process.exit(result.action === 'block' ? 1 : 0)
  }

  // ── Full interactive mode (multiple-choice Q&A)
  const analysis = analyzeDirective(text)

  // If directive is excellent, just confirm and exit
  if (analysis.score >= 90) {
    process.stdout.write(renderAnalysis(text, analysis))
    process.stdout.write(`  ${GRN}\u2713 Directive is clear. Proceed as-is.${R}\n\n`)
    process.exit(0)
  }

  // Run disambiguation Q&A
  const resolved = await runDisambiguationQA(text, analysis)

  // Show the resolved directive
  process.stdout.write('\n')
  process.stdout.write(`  ${'─'.repeat(44)}\n`)
  process.stdout.write(`  ${BOLD}Resolved directive:${R}\n\n`)
  process.stdout.write(`  ${GRN}${resolved}${R}\n`)
  process.stdout.write(`  ${'─'.repeat(44)}\n\n`)

  // Copy to clipboard automatically
  const copied = copyToClipboard(resolved)
  if (copied) {
    process.stdout.write(`  ${GRN}\u2713 Copied to clipboard automatically.${R}\n`)
  } else {
    process.stdout.write(`  ${DIM}(clipboard unavailable)${R}\n`)
  }
  process.stdout.write('\n')

  process.exit(0)
}

main().catch(err => {
  console.error('Dyad error:', err.message)
  process.exit(1)
})
