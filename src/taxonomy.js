// ============================================================
// Dyad Taxonomy — Pattern definitions with severity
// Huang (2026) three-tier model
// ============================================================

// ── Tier 1: Lexically vague verbs ──────────────────────────
// severity: 'high' (×1.0), 'medium' (×0.7), 'low' (×0.5)
// Applied as multiplier to base −8 penalty.
export const TIER1 = [
  {
    words: ['fix', 'fixes', 'fixing', 'fixed'],
    severity: 'high',
    suggestions: ['debug / find and fix errors', 'repair formatting or structure', 'restructure / rewrite content', 'correct logic', 'specify my own'],
  },
  {
    words: ['handle', 'handles', 'handling'],
    severity: 'high',
    suggestions: ['process the request', 'forward to stakeholder', 'delegate to team', 'resolve and close', 'escalate for review'],
  },
  {
    words: ['process', 'processes', 'processing'],
    severity: 'high',
    suggestions: ['parse the input', 'execute the pipeline', 'transform the data', 'route to destination', 'archive the record'],
  },
  {
    words: ['manage', 'manages', 'managing'],
    severity: 'high',
    suggestions: ['oversee the workflow', 'execute directly', 'delegate to team', 'track progress', 'approve and sign off'],
  },
  {
    words: ['deal', 'deals', 'dealing'],
    severity: 'high',
    suggestions: ['respond to the issue', 'resolve and close', 'escalate to manager', 'archive / dismiss', 'ignore and defer'],
  },
  {
    words: ['update', 'updates', 'updating'],
    severity: 'medium',
    suggestions: ['revise the content', 'notify stakeholders', 'upgrade the version', 'refresh the data', 'specify my own'],
  },
  {
    words: ['review', 'reviews', 'reviewing'],
    severity: 'medium',
    suggestions: ['read and summarize', 'evaluate against criteria', 'approve or reject', 'edit / markup', 'audit for compliance'],
  },
  {
    words: ['check', 'checks', 'checking'],
    severity: 'medium',
    suggestions: ['verify correctness', 'validate format', 'proofread text', 'test functionality', 'audit logs'],
  },
  {
    words: ['prepare', 'prepares', 'preparing'],
    severity: 'medium',
    suggestions: ['draft the document', 'compile source material', 'format for delivery', 'assemble the package', 'specify my own'],
  },
  {
    words: ['sort', 'sorts', 'sorting'],
    severity: 'medium',
    suggestions: ['alphabetize items', 'prioritize by urgency', 'categorize by type', 'filter by criteria', 'delete duplicates'],
  },
  {
    words: ['look into', 'looked into'],
    severity: 'medium',
    suggestions: ['research the topic', 'investigate the issue', 'verify the claim', 'audit the logs', 'specify my own'],
  },
  {
    words: ['improve', 'improves', 'improving'],
    severity: 'medium',
    suggestions: ['edit for clarity', 'restructure the argument', 'expand with detail', 'condense for brevity', 'specify my own'],
  },
  {
    words: ['send', 'sends', 'sending'],
    severity: 'low',
    suggestions: ['email as attachment', 'share Drive link', 'post in channel', 'forward the thread', 'upload to portal'],
  },
  {
    words: ['organize', 'organizes', 'organizing'],
    severity: 'low',
    suggestions: ['sort into folders', 'categorize by label', 'restructure the hierarchy', 'prioritize by date', 'specify my own'],
  },
  {
    words: ['clean', 'cleans', 'cleaning', 'cleanup'],
    severity: 'low',
    suggestions: ['delete duplicates', 'rename consistently', 'reorganize folder structure', 'simplify content', 'specify my own'],
  },
]

// ── Severity multipliers ────────────────────────────────────
export const SEVERITY_MULTIPLIER = {
  high:   1.0,
  medium: 0.7,
  low:    0.5,
}

// ── Tier 2: Idiomatic vague phrases ────────────────────────
export const TIER2 = [
  {
    phrase: 'respond appropriately',
    issue: 'No response standard specified',
    fix: 'respond in formal register, under 150 words, no contractions',
    options: ['formal register, under 150 words', 'informal tone, direct answer', 'match sender\'s register', 'specify my own'],
  },
  {
    phrase: 'make it better',
    issue: 'No improvement dimension specified',
    fix: 'improve sentence clarity; preserve technical terms and argument structure',
    options: ['improve sentence clarity', 'fix grammar and spelling', 'restructure argument', 'condense for brevity', 'specify my own'],
  },
  {
    phrase: 'make it good',
    issue: 'No quality standard specified',
    fix: 'specify: grammar, clarity, tone, length, or structure',
    options: ['correct grammar and spelling', 'improve clarity', 'adjust tone', 'fix structure', 'specify my own'],
  },
  {
    phrase: 'keep it simple',
    issue: 'Simple relative to what audience?',
    fix: 'use vocabulary accessible to non-specialist; define jargon',
    options: ['non-specialist vocabulary', 'one idea per sentence', 'remove jargon', 'bullet points instead of prose', 'specify my own'],
  },
  {
    phrase: 'take care of it',
    issue: 'No action type specified',
    fix: 'draft response, flag for review, do not send',
    options: ['draft a response', 'flag for human review', 'resolve autonomously', 'escalate to manager', 'specify my own'],
  },
  {
    phrase: 'be professional',
    issue: 'No professional convention specified',
    fix: 'formal register, title + last name salutation, no humor',
    options: ['formal register, no contractions', 'title + last name salutation', 'no humor or idioms', 'follow AP style', 'specify my own'],
  },
  {
    phrase: 'sound professional',
    issue: 'No professional convention specified',
    fix: 'formal register, title + last name, no contractions',
    options: ['formal register, no contractions', 'title + last name salutation', 'match corporate tone', 'specify my own'],
  },
  {
    phrase: 'as soon as possible',
    issue: 'No concrete deadline specified',
    fix: 'by [specific date/time]',
    options: ['within 1 hour', 'by end of today', 'by end of week', 'specify exact date', 'specify my own'],
  },
  {
    phrase: 'asap',
    issue: 'No concrete deadline specified',
    fix: 'by [specific date/time]',
    options: ['within 1 hour', 'by end of today', 'by end of week', 'specify exact date', 'specify my own'],
  },
  {
    phrase: 'when you get a chance',
    issue: 'No priority or deadline specified',
    fix: 'low priority; complete by end of week',
    options: ['low priority, end of week', 'when workload allows', 'next available slot', 'specify deadline', 'specify my own'],
  },
  {
    phrase: 'at your earliest',
    issue: 'No concrete deadline',
    fix: 'by [specific date/time]',
    options: ['within 1 hour', 'by end of today', 'by end of week', 'specify exact date', 'specify my own'],
  },
  {
    phrase: 'look into this',
    issue: 'No scope or output format specified',
    fix: 'research [topic], summarize findings in [format]',
    options: ['research and summarize in bullets', 'investigate and write report', 'verify claim and confirm', 'audit and flag issues', 'specify my own'],
  },
  {
    phrase: 'deal with this',
    issue: 'No action type specified',
    fix: 'specify: respond / archive / escalate / draft',
    options: ['respond directly', 'archive / close', 'escalate to team', 'draft a reply for review', 'specify my own'],
  },
  {
    phrase: 'sort this out',
    issue: 'No resolution criteria specified',
    fix: 'resolve by [criteria], deadline [date]',
    options: ['identify root cause', 'fix and verify', 'escalate with context', 'document and defer', 'specify my own'],
  },
  {
    phrase: 'clean this up',
    issue: 'No cleanup scope specified',
    fix: 'specify: delete / reformat / reorganize / simplify',
    options: ['delete duplicates', 'reformat consistently', 'reorganize structure', 'simplify language', 'specify my own'],
  },
  {
    phrase: 'make sense of',
    issue: 'No output format for "sense-making"',
    fix: 'summarize in [format]; highlight [specific aspects]',
    options: ['summarize in bullet points', 'write executive summary', 'extract key decisions', 'flag unclear parts', 'specify my own'],
  },
  {
    phrase: 'figure out',
    issue: 'No deliverable or method specified',
    fix: 'determine [specific question]; output: [format]',
    options: ['determine the answer and explain', 'research and present options', 'calculate and show work', 'investigate and report', 'specify my own'],
  },
  {
    phrase: 'do something about',
    issue: 'Action type completely unspecified',
    fix: 'specify the action: draft / respond / escalate / archive',
    options: ['draft a response', 'respond directly', 'escalate to manager', 'archive and close', 'specify my own'],
  },
  {
    phrase: 'in a good way',
    issue: 'No standard for "good"',
    fix: 'specify the dimension: clarity / tone / brevity / structure',
    options: ['improve clarity', 'improve tone', 'improve brevity', 'improve structure', 'specify my own'],
  },
  {
    phrase: 'make it flow',
    issue: 'No flow standard specified',
    fix: 'improve paragraph transitions; vary sentence length',
    options: ['smooth paragraph transitions', 'vary sentence length', 'add connective phrases', 'restructure for narrative arc', 'specify my own'],
  },
  {
    phrase: 'feels off',
    issue: 'Subjective diagnostic, no action',
    fix: 'identify and correct: tone / structure / word choice [specify]',
    options: ['fix the tone', 'fix the structure', 'fix the word choice', 'identify what feels wrong first', 'specify my own'],
  },
]

// ── Tier 3: Speech act markers ─────────────────────────────
// Canonical set with descriptions
export const MARKERS = [
  { token: '[EXECUTE]', description: 'Perform the action directly — produce output, run code, make changes' },
  { token: '[DRAFT]',   description: 'Produce a draft for human review before any action is taken' },
  { token: '[ANALYZE]', description: 'Examine, evaluate, and explain — no changes, just analysis' },
  { token: '[DISCUSS]', description: 'Explore options, trade-offs, or ideas in conversation' },
  { token: '[PLAN]',    description: 'Create a step-by-step plan or roadmap without executing it' },
  { token: '[MONITOR]', description: 'Track, watch, or check on an ongoing process or metric' },
]

export const MARKER_TOKENS = MARKERS.map(m => m.token)
export const MARKER_REGEX = /\[(execute|draft|analyze|discuss|plan|monitor)\]/i

// ── Negation / completion / conditional token sets ──────────
export const NEGATION_TOKENS = [
  "don't", "do not", "doesn't", "no need to", "stop", "never", "skip"
]
export const COMPLETION_TOKENS = [
  "already", "finished", "done", "completed"
]
export const CONDITIONAL_TOKENS = [
  "if", "whether", "might", "could"
]
