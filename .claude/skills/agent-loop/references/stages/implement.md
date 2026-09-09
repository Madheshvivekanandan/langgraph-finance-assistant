# Stage: implement

**Reads:** `profile.md`, `task.md`, and — when the tier produced them — `analysis.md`, `plan.md`
**Writes:** `implementation.md` (template: `templates/implementation.md`) plus the code changes
**Restrictions:** none. This is the only stage that may modify source code (the debug stage
inherits the same permission).
**Reasoning demand:** moderate. With a good plan and named exemplars, most of the difficulty has
already been removed upstream.

These artifacts are your entire context. You do not see any earlier stage's reasoning, and that is
by design.

## Job

- Follow `plan.md` step by step when it exists; deviate only when the code forces you to, and
  record every deviation.
- Imitate the exemplar files named in `analysis.md` — match the codebase's existing patterns,
  naming, and idioms rather than inventing your own.
- Reuse what analysis found. Do not build something listed under **Found**.
- Keep the diff minimal: no drive-by refactors, no changes outside the plan's scope.

## Verification is part of implementation

Before you finish, run the plan's **Runnable check** yourself (for tier-S tasks with no plan, run
the project's test command from `profile.md`). Fix what it surfaces.

Evidence means actual command output, not a claim that it passed. The verify stage will run the
same check independently, so a claim you cannot back will simply become a FAIL one stage later.


## The environment is not scratch space

You are running on a real machine with real state. Before you touch it:

- The development database holds data someone cares about. Tests have their own; use it. If you
  must seed rows to check something by hand, delete them afterwards and say in your artifact what
  you created and removed.
- Rebuilding or restarting a running stack is a side effect. Do it when the task needs it, and say
  that you did — a later stage may otherwise judge a stale build and reach the wrong verdict.
- Leave the working tree the way the next stage expects it: changes in place, nothing committed,
  nothing pushed.

## Output

1. **What changed** — files and a one-line summary each.
2. **Deviations from plan** — each with the reason (or "none").
3. **Evidence** — the check command you ran and its actual output, trimmed to the relevant tail.

## Return

At most 10 lines: what changed, check result, and the path to `implementation.md`. Do not paste the
diff or full logs into your reply.
