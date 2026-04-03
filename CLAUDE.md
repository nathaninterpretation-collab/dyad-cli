# Dyad CLI — Claude Code Context

## What this project is
Dyad is a pre-send directive analyzer for Claude Code. It analyzes user directives for lexical, idiomatic, and structural ambiguity using the Huang (2026) three-tier taxonomy, then runs an interactive multiple-choice Q&A to help the user resolve ambiguities before sending to Claude.

- **Zero dependencies** — pure Node.js (>=18), no npm packages
- **ESM only** — all files use `import`/`export` (package.json `"type": "module"`)
- **Version**: 0.2.0, MIT license

## Architecture

```
dyad-cli/
├── src/
│   ├── taxonomy.js       — Pattern definitions (TIER1, TIER2, MARKERS) with severity
│   ├── analyzer.js       — Core analyzeDirective() function (Phase 1+2)
│   ├── disambiguation.js — buildDisambiguation() + toConfirmationPrompt() (Phase 3)
│   ├── filter.js         — filterDirective() pre-send filter (Phase 4)
│   ├── header.js         — buildDyadContextHeader() DYAD CONTEXT block (Phase 4)
│   └── display.js        — ANSI rendering helpers (renderAnalysis, renderMenu, renderHookWarning)
├── bin/
│   └── dyad.js           — Multiple-choice interactive CLI entry point
├── hooks/
│   └── dyad-hook.js      — Claude Code PreToolUse hook (reads stdin JSON, writes XML to stdout)
├── test/
│   ├── analyzer.test.js  — Phase 1+2 unit tests (8 tests)
│   ├── filter.test.js    — Phase 4 filter tests (4 tests)
│   └── corpus.test.js    — Regression corpus (18 test cases)
├── config/
│   └── default.json      — Scoring and filter configuration (reference only, not loaded at runtime)
├── install.js            — Setup script: npm link + injects hook into ~/.claude/settings.json
├── package.json
├── .gitignore
└── .npmignore            — Excludes test/ and .claude/ from npm publish
```

## Key design decisions

### Interaction model
The CLI presents **multiple-choice disambiguation questions**, NOT text rewrites. When a directive has ambiguity, the user picks from numbered options; their answers are used to build the resolved directive. The resolved text is automatically copied to clipboard.

### Tier system (Huang 2026)
- **Tier 1** — Lexically vague verbs (fix, handle, manage, send, etc.) with severity weighting (high/medium/low)
- **Tier 2** — Idiomatic vague phrases ("make it better", "clean this up", "take care of it", etc.)
- **Tier 3** — Missing speech act marker ([EXECUTE], [DRAFT], [ANALYZE], [DISCUSS], [PLAN], [MONITOR])

### Scoring (Phase 1+2) — `src/analyzer.js`
- Base penalty: T1=−8×severity, T2=−12, T3=−18, marker bonus=+8
- Severity multipliers: high=1.0, medium=0.7, low=0.5
- Position weighting: `positionFactor = 1.0 − (matchIndex / textLength) × 0.4`
- Imperative opening (position 0, first word): ×1.25 multiplier
- Negation context (don't, never, stop, etc.): suppress T1 issue entirely
- Completion context (already, finished, done, etc.): suppress T1 issue entirely
- Conditional context (if, whether, might, could): downgrade T1 penalty to −3
- T2 suppresses overlapping T1: if a T1 word falls inside a T2 phrase span, the T1 is not emitted
- T2 uses global regex to catch all occurrences of a phrase (not just first)
- Score is clamped to [0, 100]

### Grade labels
- >= 90: Excellent (green)
- >= 75: Good (green)
- >= 60: Needs Work (yellow)
- >= 40: High Ambiguity (red)
- < 40: Critical Ambiguity (red)

### Filter thresholds (Phase 4) — `src/filter.js`
- score < 40 → **block** (require resolve or `//!force`)
- score 40–75 → **annotate** (prepend DYAD CONTEXT header)
- score > 75 → **pass**
- `//!force` token → strip token, pass regardless of score, mark `forced: true`

### Claude Code Hook — `hooks/dyad-hook.js`
- Registered as a **PreToolUse** hook via `install.js`
- Reads JSON payload from stdin (`session_id`, `transcript_path`, `tool_name`)
- Extracts last user message from JSONL transcript
- Only warns once per session (uses temp file flag)
- Only fires when directive score < 75
- Outputs structured XML (`<dyad_analysis>`) to stdout for Claude to surface

## Data flow

```
User directive
  → analyzeDirective(text)        [Phase 1+2: scoring + issue detection]
  → buildDisambiguation(analysis) [Phase 3: structure Q&A options]
  → Interactive Q&A               [CLI: numbered choices]
  → Resolved directive            [substitutions applied, marker prepended]
```

Filter mode:
```
User directive
  → filterDirective(text)         [Phase 4: block/annotate/pass]
  → buildDyadContextHeader()      [if annotate: prepend DYAD CONTEXT block]
```

## Module exports

| Module | Key exports |
|--------|------------|
| `src/taxonomy.js` | `TIER1`, `TIER2`, `MARKERS`, `MARKER_TOKENS`, `MARKER_REGEX`, `SEVERITY_MULTIPLIER`, `NEGATION_TOKENS`, `COMPLETION_TOKENS`, `CONDITIONAL_TOKENS` |
| `src/analyzer.js` | `analyzeDirective(text)` → `{ score, grade, issues, t1, t2, t3, hasMarker, wordCount, rewrite }` |
| `src/disambiguation.js` | `buildDisambiguation(analysis, originalText)`, `toConfirmationPrompt(disambiguation)` |
| `src/filter.js` | `filterDirective(text, config?, context?)`, `FILTER_CONFIG`, `getFilterLog()` |
| `src/header.js` | `buildDyadContextHeader(text, analysis)` |
| `src/display.js` | `renderAnalysis(text, result)`, `renderMenu(hasRewrite)`, `renderHookWarning(text, result)` |

## Running tests
```bash
npm test
# or directly:
node --test test/analyzer.test.js test/filter.test.js test/corpus.test.js
```

Tests use **`node:test`** and **`node:assert/strict`** — no test framework dependencies. All tests are synchronous. The corpus test file drives a data table of 18 regression cases.

## CLI usage
```bash
dyad "fix my auth and make it better"         # interactive Q&A
dyad --filter "text"                           # filter mode (block/annotate/pass)
dyad --json "text"                             # JSON output for piping
dyad --quiet "text"                            # resolved text only
echo "text" | dyad                             # stdin pipe
dyad                                           # interactive prompt (press Enter twice)
```

Exit codes: `--json` exits 1 if score < 60; `--filter` exits 1 if blocked; otherwise 0.

## Installation
```bash
npm run setup    # runs install.js: npm link + injects hook into ~/.claude/settings.json
```

The installer writes a PreToolUse hook entry to `~/.claude/settings.json` with matcher `".*"` (fires on every tool call). It prefers the globally-linked `dyad-hook` command, falling back to `node <absolute-path>/hooks/dyad-hook.js`.

## Conventions for contributors

- **No external dependencies** — keep the project zero-dep
- **ESM imports only** — no `require()`
- **ANSI colors** are defined inline with escape codes, not via a color library
- **Config values** in `config/default.json` are reference documentation; actual defaults are hardcoded in `src/filter.js` (`FILTER_CONFIG`) and `src/taxonomy.js` (`SEVERITY_MULTIPLIER`)
- **Test naming**: tests follow the pattern `description → expected outcome`
- Add regression cases to `test/corpus.test.js` when fixing scoring bugs
- The `bin/` entry points have `#!/usr/bin/env node` shebangs
- Terminal width is read from `process.stdout.columns` with fallback to 72
