#!/usr/bin/env node
// ============================================================
// Dyad Claude Code Hook — PreToolUse
// Fires before Claude uses any tool.
// Reads the transcript, finds the last user message,
// analyzes it for ambiguity, and warns the user if score < 70.
//
// Install: added to ~/.claude/settings.json automatically
//          by running: node install.js (from dyad-cli/)
// ============================================================

import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'fs'
import { tmpdir, homedir } from 'os'
import { join } from 'path'
import { analyzeDirective } from '../src/analyzer.js'
import { renderHookWarning } from '../src/display.js'

// ── Read hook payload from stdin ───────────────────────────
async function readStdin() {
  return new Promise(resolve => {
    let data = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', c => { data += c })
    process.stdin.on('end', () => {
      try { resolve(JSON.parse(data)) }
      catch { resolve({}) }
    })
  })
}

// ── Session guard — only warn once per session ─────────────
function alreadyWarned(sessionId) {
  const flagFile = join(tmpdir(), `dyad-session-${sessionId}`)
  if (existsSync(flagFile)) return true
  writeFileSync(flagFile, '1')
  return false
}

// ── Extract last user message from JSONL transcript ────────
function getLastUserMessage(transcriptPath) {
  if (!transcriptPath || !existsSync(transcriptPath)) return null
  try {
    const lines = readFileSync(transcriptPath, 'utf8')
      .split('\n')
      .filter(Boolean)
      .map(l => { try { return JSON.parse(l) } catch { return null } })
      .filter(Boolean)

    // Walk backwards to find the last user message
    for (let i = lines.length - 1; i >= 0; i--) {
      const entry = lines[i]
      // Claude Code transcript format: { type: 'user', message: { content: [...] } }
      if (entry.type === 'user' && entry.message?.content) {
        const content = entry.message.content
        if (typeof content === 'string') return content
        if (Array.isArray(content)) {
          const text = content.filter(c => c.type === 'text').map(c => c.text).join(' ')
          if (text.trim()) return text.trim()
        }
      }
      // Also handle simpler format
      if (entry.role === 'user') {
        if (typeof entry.content === 'string') return entry.content
        if (Array.isArray(entry.content)) {
          return entry.content.filter(c => c.type === 'text').map(c => c.text).join(' ')
        }
      }
    }
  } catch { return null }
  return null
}

// ── Main ───────────────────────────────────────────────────
async function main() {
  const payload = await readStdin()
  const { session_id, transcript_path, tool_name } = payload

  // Only fire once per session (avoid spamming on every tool call)
  if (session_id && alreadyWarned(session_id)) {
    process.exit(0)
  }

  // Get the user's directive
  const userText = getLastUserMessage(transcript_path)
  if (!userText || userText.length < 8) {
    process.exit(0)
  }

  // Analyze
  const result = analyzeDirective(userText)

  // Only warn if directive quality needs improvement
  if (result.score >= 75) {
    process.exit(0)
  }

  // Print warning to stderr — Claude Code shows this to the user
  const warning = renderHookWarning(userText, result)
  process.stderr.write(warning)

  // Exit 0 = allow the tool use to proceed
  // Exit 2 = block + show message (we don't block, just inform)
  process.exit(0)
}

main().catch(() => process.exit(0))
