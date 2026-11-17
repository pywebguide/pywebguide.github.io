# Project instructions

## Review of large tasks by Fable

For large or complex tasks — changes across several files, structural or architectural changes, non-trivial logic, or a new page/section — before reporting the result to the user:

1. Run the `fable-reviewer` agent (`.claude/agents/fable-reviewer.md`, model `fable`). Pass it the user's original request, a short summary of what was done and the list of changed files.
2. Fix the findings that are real; for ones you disagree with, say why.
3. In the final report, briefly mention what the review found and what was fixed.

This standing instruction counts as the user's explicit request to use this subagent. Do not run it for small tasks (one-line fixes, typos, simple questions).
