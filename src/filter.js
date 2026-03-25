// ============================================================
// Dyad Pre-Send Filter — Phase 4
// filterDirective(text, config, context) → { action, payload, analysis }
// ============================================================

import { analyzeDirective } from './analyzer.js'
import { buildDyadContextHeader } from './header.js'

export const FILTER_CONFIG = {
  strictThreshold: 40,
  advisoryThreshold: 75,
  allowForceOverride: true,
  forceOverrideToken: '//!force',
  logAll: true,
}

/**
 * filterDirective(text, config?, context?)
 *
 * Returns:
 *   { action: 'block'|'annotate'|'pass', payload: string, analysis: object }
 *
 * Rules:
 *   score < strictThreshold  → 'block'   (show disambiguation, require resolve or //!force)
 *   score 40–75              → 'annotate' (prepend DYAD CONTEXT header)
 *   score > 75               → 'pass'
 *
 *   //!force present → strip token, log, pass regardless of score, no header
 */
export function filterDirective(text, config = FILTER_CONFIG, context = {}) {
  const cfg = { ...FILTER_CONFIG, ...config }

  // ── Force-override check
  if (cfg.allowForceOverride && text.includes(cfg.forceOverrideToken)) {
    const stripped = text.replace(cfg.forceOverrideToken, '').replace(/\s{2,}/g, ' ').trim()
    const analysis = analyzeDirective(stripped)

    if (cfg.logAll) {
      logEntry({ action: 'force-pass', score: analysis.score, text: stripped, context })
    }

    return {
      action: 'pass',
      payload: stripped,
      analysis,
      forced: true,
    }
  }

  // ── Normal analysis
  const analysis = analyzeDirective(text)
  const { score } = analysis

  if (cfg.logAll) {
    logEntry({ action: score < cfg.strictThreshold ? 'block' : score <= cfg.advisoryThreshold ? 'annotate' : 'pass', score, text, context })
  }

  if (score < cfg.strictThreshold) {
    // Block — caller should show disambiguation and ask user to resolve
    return {
      action: 'block',
      payload: text,
      analysis,
    }
  }

  if (score <= cfg.advisoryThreshold) {
    // Annotate — prepend DYAD CONTEXT header
    const header = buildDyadContextHeader(text, analysis)
    const payload = header + '\n\n' + text

    return {
      action: 'annotate',
      payload,
      analysis,
    }
  }

  // Pass
  return {
    action: 'pass',
    payload: text,
    analysis,
  }
}

// Simple in-process log (could be swapped for file logging)
const filterLog = []

function logEntry(entry) {
  filterLog.push({ ...entry, ts: new Date().toISOString() })
}

export function getFilterLog() {
  return [...filterLog]
}
