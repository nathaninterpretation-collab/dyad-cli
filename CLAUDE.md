# Dyad CLI — Claude Code Context

## What this project is
Dyad is a pre-send directive analyzer for Claude Code. It analyzes user directives for lexical, idiomatic, and structural ambiguity using the Huang (2026) three-tier taxonomy, then runs an interactive multiple-choice Q&A to help the user resolve ambiguities before sending to Claude.

## Architecture

```
dyad-cli/
├── src/
│   ├── taxonomy.js       — Pattern definitions (TIER1, TIER2, MARKERS) with severity
│   ├── analyzer.js       — Core analyzeDirective() function (Phase 1+2)
│   ├── disambiguation.js — buildDisambiguation() + toConfirmationPrompt() (Phase 3)
│   ├── filter.js         — filterDirective() pre-send filter (Phase 4)
│   ├── header.js         — buildDyadContextHeader() DYAD CONTEXT block (Phase 4)
│   └── display.js        — ANSI rendering helpers
├── bin/
│   └── dyad.js           — Multiple-choice interactive CLI
├── hooks/
│   └── dyad-hook.js      — Claude Code PreToolUse hook
├── test/
│   ├── analyzer.test.js  — Phase 1+2 unit tests
│   ├── filter.test.js    — Phase 4 filter tests
│   └── corpus.test.js    — Regression corpus
└── config/
    └── default.json      — Scoring and filter configuration
```

## Key design decisions

### Interaction model
The CLI presents **multiple-choice disambiguation questions**, NOT text rewrites. When a directive has ambiguity, the user picks from options; their answers are used to build the resolved directive.

### Tier system (Huang 2026)
- **Tier 1** — Lexically vague verbs (fix, handle, manage, send…) with severity weighting
- **Tier 2** — Idiomatic vague phrases ("make it better", "clean this up"…)
- **Tier 3** — Missing speech act marker ([EXECUTE], [DRAFT], [ANALYZE], [DISCUSS], [PLAN], [MONITOR])

### Scoring (Phase 1+2)
- Base penalty: T1=−8×severity, T2=−12, T3=−18, marker bonus=+8
- Position weighting: `positionFactor = 1.0 − (matchIndex / textLength) × 0.4`
- Imperative opening (position 0, first word): ×1.25 multiplier
- Negation context: suppress T1 issue
- Completion context: suppress T1 issue
- Conditional context: downgrade T1 penalty to −3

### Filter thresholds (Phase 4)
- score < 40 → block (require resolve or `//!force`)
- score 40–75 → annotate (prepend DYAD CONTEXT header)
- score > 75 → pass

## Running tests
```
node --test test/analyzer.test.js test/filter.test.js test/corpus.test.js
```

## CLI usage
```
dyad "fix my auth and make it better"         # interactive Q&A
dyad --filter "text"                           # filter mode
dyad --json "text"                             # JSON output
dyad --quiet "text"                            # resolved text only
echo "text" | dyad                             # stdin pipe
```
