#!/usr/bin/env node
// ============================================================
// Dyad CLI Installer
// 1. npm link (makes `dyad` command available globally)
// 2. Injects PreToolUse hook into ~/.claude/settings.json
// ============================================================

import { readFileSync, writeFileSync, existsSync, mkdirSync, chmodSync } from 'fs'
import { execSync } from 'child_process'
import { homedir } from 'os'
import { join, resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dir = dirname(fileURLToPath(import.meta.url))
const hookPath = resolve(join(__dir, 'hooks', 'dyad-hook.js'))

// ── ANSI helpers ───────────────────────────────────────────
const G = s => `\x1b[32m${s}\x1b[0m`
const Y = s => `\x1b[33m${s}\x1b[0m`
const B = s => `\x1b[1m${s}\x1b[0m`
const D = s => `\x1b[2m${s}\x1b[0m`

console.log(`\n${B('  Dyad CLI Installer')}\n`)

// ── Step 1: npm link ───────────────────────────────────────
console.log(`  ${D('Step 1:')} Linking dyad command globally...`)
try {
  execSync('npm link', { cwd: __dir, stdio: 'inherit' })
  console.log(`  ${G('✓')} dyad command available globally\n`)
} catch (err) {
  console.log(`  ${Y('!')} npm link failed — try: sudo npm link\n`)
}

// ── Step 2: Hook into Claude Code settings.json ───────────
console.log(`  ${D('Step 2:')} Installing Claude Code PreToolUse hook...`)

const claudeDir = join(homedir(), '.claude')
const settingsPath = join(claudeDir, 'settings.json')

if (!existsSync(claudeDir)) {
  mkdirSync(claudeDir, { recursive: true })
}

let settings = {}
if (existsSync(settingsPath)) {
  try {
    settings = JSON.parse(readFileSync(settingsPath, 'utf8'))
    console.log(`  ${D('Found existing settings.json')}`)
  } catch {
    console.log(`  ${Y('!')} Could not parse settings.json — creating fresh`)
  }
}

// Use globally installed `dyad-hook` command if available, else fall back to local path
let hookCommand
try {
  execSync('dyad-hook --version', { stdio: 'ignore' })
  hookCommand = 'dyad-hook'
} catch {
  hookCommand = `node "${hookPath}"`
}

const hookEntry = {
  matcher: '.*',
  hooks: [{ type: 'command', command: hookCommand }]
}

// Inject into PreToolUse
if (!settings.hooks) settings.hooks = {}
if (!settings.hooks.PreToolUse) settings.hooks.PreToolUse = []

// Check if already installed
const alreadyInstalled = settings.hooks.PreToolUse.some(
  h => h.hooks?.some(hh => hh.command?.includes('dyad-hook') || hh.command?.includes('dyad-hook.js'))
)

if (alreadyInstalled) {
  console.log(`  ${G('✓')} Hook already installed — updating path`)
  settings.hooks.PreToolUse = settings.hooks.PreToolUse.filter(
    h => !h.hooks?.some(hh => hh.command?.includes('dyad-hook.js'))
  )
}

settings.hooks.PreToolUse.push(hookEntry)

writeFileSync(settingsPath, JSON.stringify(settings, null, 2))
console.log(`  ${G('✓')} Hook installed → ${settingsPath}`)
console.log(`  ${D('Hook path:')} ${hookPath}\n`)

// ── Done ───────────────────────────────────────────────────
console.log(`  ${B('Setup complete!')}`)
console.log(``)
console.log(`  ${B('Usage:')}`)
console.log(`    ${G('dyad')} "fix my auth and make it better"   ${D('# analyze a directive')}`)
console.log(`    ${G('dyad')}                                     ${D('# interactive mode')}`)
console.log(`    echo "fix my code" | ${G('dyad')}               ${D('# pipe mode')}`)
console.log(`    ${G('dyad')} --json "fix my auth"               ${D('# JSON output')}`)
console.log(``)
console.log(`  ${B('Claude Code hook:')}`)
console.log(`    Fires automatically before each tool use.`)
console.log(`    Warns when your directive scores below 75/100.`)
console.log(`    Only warns once per session.`)
console.log(``)
