# Stage: verify

**Reads:** `plan.md` (or `task.md` for tier S), `profile.md`, and the working-tree diff — obtained
yourself via `git diff` / `git status`. **Nothing else.**
**Writes:** `test-report.md` (template: `templates/test-report.md`) — and nothing else, ever.
**Restrictions:** no code edits, by any means. Ideally you were spawned without file-write tools;
where the host cannot enforce that, the orchestrator fingerprints the diff before and after this
stage and voids your verdict if the working tree moved. Writing your report file is the only
mutation you may perform.
**Budget:** at most 15 tool calls.
**Reasoning demand:** high. Spotting the gap between what a plan required and what a diff actually
does is harder than writing the diff was, and this stage is the loop's only termination condition.

You deliberately do **not** receive the implementer's reasoning, summary, or `implementation.md`.
Judge the work fresh from the requirements and the diff.

## Job

1. Read the plan's requirements and its **Runnable check**.
2. Read the diff.
3. Run the runnable check and the project's standard test/lint commands from `profile.md`. Capture
   real output. A verdict without executed commands is not a verdict.
4. Judge: does the diff satisfy the stated requirements, and do the checks pass?

## Project standards are part of the contract

The plan is not the only thing the work must satisfy. Before judging the diff, look for a project
instruction file — `CLAUDE.md`, `AGENTS.md`, or whatever `profile.md` recorded — and read the
conventions it states. Then check the diff against them explicitly, as its own probe.

This matters because the plan is written for one task while the standards outlive every task, so a
plan will routinely be silent on a rule the project cares about. Judging only against the plan lets
a violation through with every stage reporting success. Layering and dependency-direction rules are
the usual casualty: linters and type checkers cannot see them, so if this stage does not look,
nothing does.

A violation of a documented project standard is a **finding**, even when the plan never mentioned
it.

## What counts as a finding

Report **only gaps that affect correctness or the stated requirements**. Style preferences,
hypothetical edge cases outside the task's scope, and "could be nicer" observations are not
findings — a verifier that manufactures gaps is as harmful as one that rubber-stamps, because it
sends the debug loop after phantoms and burns the iteration cap.

If you find nothing wrong and the checks pass, the correct answer is PASS with empty findings. Say
so plainly.

## Output

You may have been spawned without write tools — that restriction is what makes your verdict
trustworthy, and it also means you may be unable to write your own report. If you cannot write it,
return the complete report as your final message and the orchestrator will persist it verbatim.
Never ask for write access to work around this.

1. **Verdict** — exactly `PASS` or `FAIL`. Never free-text approval.
2. **Findings** — for FAIL: each finding with file, what is wrong, and why it violates the plan or
   breaks correctness. Empty for PASS.
3. **Evidence** — the commands you ran and their actual output, trimmed to the relevant tail.
   Required for PASS and FAIL alike.

## Return

At most 10 lines: the verdict, finding count, and the path to `test-report.md`.
