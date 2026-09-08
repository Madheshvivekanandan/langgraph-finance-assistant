---
name: git-commit-pr-workflow
description: Standard for making commits and opening pull requests. Load BEFORE running git commit, git push, git rebase, git tag, or gh pr create; before writing a commit message, PR description, CHANGELOG entry, or review comment; and before choosing a branch name, merge strategy, or release version. Covers atomic commits, Conventional Commits, trunk-based branching, PR scope and description, review etiquette, rebase vs merge, semantic versioning, tags, changelogs, pre-commit hooks, and the rules an AI agent must follow when acting on a user's git history.
---

# Git Commit and Pull Request Workflow

Opinionated synthesis of Pro Git's commit guidelines, Git's own `Documentation/SubmittingPatches`,
Conventional Commits 1.0.0, Semantic Versioning 2.0.0, Keep a Changelog 1.1.0, Google's
Engineering Practices for code review, DORA's trunk-based-development capability, and GitHub's
pull request documentation. These are the git rules other skills should defer to rather than
restate: point a language skill's git section at this document instead of duplicating it. When this
document conflicts with an existing in-repo convention, follow the repo and say so.

## 1. Philosophy

- **A commit is a unit of review, revert, and bisect.** If it cannot be reverted alone, it is the wrong size.
- **The diff says what. Only the message can say why.** Write the why down or it is lost.
- **History is a record for humans**, not a keystroke log. Clean it before you share it; never after.
- **Integrate early and often.** Long-lived branches turn many small merges into one large risky one.
- **Small changes get real reviews.** Large changes get skimmed and rubber-stamped.
- **Never rewrite what you have shared.** Local history is yours; published history belongs to everyone.
- **Gates are binding, not advisory.** A red check is information, never an obstacle to route around.
- **A commit carries a human's name as its author.** Making one is an act taken in someone's identity.

## 2. The Canonical Rules

The rules other skills defer to. They apply to every language and repo.

1. **One logical change per commit.** Each commit is a single logically separate changeset that builds and passes tests on its own.
2. **Keep changes minimal and focused.** Change what the task requires and nothing else.
3. **No drive-by refactors.** A rename, move, or reformat travels in its own commit and its own PR, never alongside a behaviour change.
4. **No unrelated formatting churn.** Reformatting untouched code buries the real diff and destroys `git blame`.
5. **Imperative subject line**, 50 characters or fewer where practical and never above your linter's `header-max-length`, no trailing period.
6. **Stage deliberately.** Explicit paths, never `git add .` or `git add -A`.
7. **Read the staged diff before committing.** `git diff --staged`, every time.
8. **No commits unless the user asked.** Same for push, tag, force-push, and opening a PR.

## 3. Atomic Commits

| Rule | Do | Do not |
|---|---|---|
| Scope | One issue, one commit | Five unrelated fixes in one commit |
| Splitting | `git add --patch` to separate unrelated hunks in the same file (interactive: humans only — an agent with no TTY stages whole files instead, see section 14 rule 8) | Commit the whole working tree and call it indivisible |
| Buildability | Every commit builds and its tests pass | "Broken midway, fixed in the next commit" |
| Whitespace | `git diff --check` clean before every commit | Trailing-whitespace noise inflating the diff |
| Tests | Test ships in the same commit as the code it covers | Tests bolted on in a follow-up |
| Refactors | Separate commit, separate PR | Rename smuggled into a bug fix |

The branch tip is byte-identical whether you make one commit or five, so splitting costs nothing and
buys reviewability, `git bisect`, and clean `git revert`. **Verify a test actually fails against the
broken code** before committing it — a test that passes either way certifies nothing.

## 4. Commit Message Format

```
Short imperative summary, 50 chars or fewer

State the problem in the present tense: "the webhook sender retries
forever on a 400". Then why this approach, what alternatives were
rejected, and any known shortcoming. Wrap at about 72 columns. The diff
shows what changed; this is for whoever changes it again in two years.

Refs: #482
```

| Rule | Good | Bad |
|---|---|---|
| Mood | `Fix parser dropping trailing spaces` | `Fixed…`, `Fixes…`, `Fixing…`, `[This patch] makes…` |
| Subject length | 50 chars or fewer as a target; the enforced ceiling is your linter's `header-max-length` (100 in `config-conventional`) | A 140-char subject truncated in every log view |
| Terminal punctuation | `Add retry to webhook sender` | `Add retry to webhook sender.` |
| Separator | Exactly one blank line between subject and body | Subject and body run together |
| Content | States the problem and the reason | Restates the diff line by line |
| Substance | `Drop FizzBuzz RPC; no callers since 3.2` | `Fix bug`, `Fix build`, `WIP`, `updates`, `Add patch`, `Moving code from A to B` |

- Git treats everything up to the first blank line as the commit **title** and reuses it in
  `git log --oneline`, `format-patch`, and every UI; omitting that blank line makes tooling misparse
  the whole message as a title. The 50-character summary is Git's own guidance and explicitly soft —
  git-commit(1) says "Though not required, it's a good idea to begin the commit message with a single
  short (no more than 50 characters) line summarizing the change"; the 72-column body wrap is the Pro
  Git template convention.
  Neither is enforced by Git — the hard ceiling comes from your linter (section 5).
- Never claim in a message something you did not verify. "Fixes the flake" and "improves throughput
  20%" are factual assertions that outlive you.

## 5. Conventional Commits

Adopt Conventional Commits **1.0.0** when the project derives releases or changelogs from history.
Header form: `<type>[optional scope]: <description>` — the colon and space are required, the type is
a noun (lowercase by convention, though the spec treats it case-insensitively), and the scope, when
present, is a noun in parentheses.

| Type | Use for | Release effect (`feat`/`fix`/breaking per the 1.0.0 spec, whose FAQ gives other types "no implicit effect in Semantic Versioning"; tooling defaults may still bump) |
|---|---|---|
| `feat` | A new feature, and nothing else | MINOR |
| `fix` | A bug fix, and nothing else | PATCH |
| `refactor` | Behaviour-preserving restructuring | none |
| `perf` | A change made for performance | none per spec; PATCH under common tooling defaults |
| `docs` | Documentation only | none |
| `test` | Tests only | none |
| `build` | Build system or dependencies | none |
| `ci` | CI configuration and scripts | none |
| `style` | Formatting with no code meaning | none |
| `chore` | Housekeeping with no src/test impact | none |
| `revert` | Reverting a previous commit | none per spec; PATCH under semantic-release only when the commit also carries a `This reverts commit <sha>.` body |

**Attribution matters.** The 1.0.0 spec normatively requires only `feat` and `fix`, sets no character
limits, and binds only those two to a version bump; the 11-type list above is
`@commitlint/config-conventional`'s, not "the Conventional Commits list". Pick one list, encode it in
your linter, and read your release tool's own rules — see References for Angular's narrower 8 types and
semantic-release's defaults. Labelling a dependency bump or a refactor as `feat` publishes a false
minor release either way.

- Breaking changes: `!` immediately before the colon, or an uppercase `BREAKING CHANGE: <desc>`
  footer, or both. Never as prose in the body — release tooling cannot see it, and the break ships
  as a patch. Every other element is case-insensitive; `BREAKING CHANGE` is the one token that must
  be uppercase (`BREAKING-CHANGE` is an accepted synonym in footers).
- Footers are **git trailers**: one blank line after the body, then `Token: value` or `Token #value`,
  with hyphens replacing spaces in the token (`Reviewed-by`, `Refs`). `BREAKING CHANGE` is the only
  space-bearing exception.
- A `type(scope)!:` prefix eats roughly 10-20 characters of the 50-character budget before the
  description starts (`feat(orders)!: ` alone is 15), so Conventional Commit descriptions run short.
  Tighten the description rather than pushing the header past your linter's ceiling.

```
feat(orders)!: require tenant_id on create

Orders created without a tenant were being attributed to the default
tenant, which leaked line items across customers.

BREAKING CHANGE: POST /orders now returns 400 when tenant_id is absent.
Refs: #1183
```

**Enforce it, do not merely agree to it.** Wire `commitlint` (or equivalent) as a `commit-msg` hook.
Its rule shape is `[level, applicable, value]` — level `0` disables, `1` warns, `2` errors;
`applicable` is `always` or `never`. Use level `2` for anything that breaks release tooling
(`type-enum`, `type-empty`, `subject-empty`, `subject-full-stop`), level `1` for cosmetics. That
config ships `header-max-length` 100 and body/footer max line length 100, so writing to the
stricter 50/72 style above keeps you compliant with both the linter and Git convention.

## 6. Branching

Default to **trunk-based development**: everyone integrates into one trunk (the default branch),
via short-lived branches that exist only to carry review and CI.

| Target | Number | Source |
|---|---|---|
| Active branches in the repository | 3 or fewer | DORA |
| Branch lifetime | hours, not days | DORA |
| Integration to trunk | at least once per day | DORA |

- **Resist long-lived development branches.** Hide incomplete work behind a feature flag or
  branch-by-abstraction instead of parking it on a branch for three weeks. No code freezes, no
  separate integration phase — trunk stays releasable.
- Cut release branches from trunk **just in time**, or release from trunk and fix forward. Fix release
  bugs on trunk first — with a test, verified by CI — then cherry-pick the fix to the release branch.
  Never fix on the release branch intending to port it back, and never merge a release branch into
  trunk; delete it once the release is out of production.
- Branch naming (house default, no standard governs this): `<type>/<short-slug>`, matching the
  commit type where it applies — `fix/webhook-retry-loop`, `feat/tenant-scoped-orders`,
  `chore/bump-ruff`. Include the ticket id if your tracker needs it: `fix/1183-webhook-retry`.
- Delete the branch on merge; a stale merged branch is one of your three. Audit branch count and age
  once (section 12), record that baseline, and drive your own number down rather than adopting
  another repo's.

## 7. Pull Request Scope

| Metric | Target | Signal to act |
|---|---|---|
| Changed lines | ~100 | ~1000 is too large; expect rejection on size alone |
| Logical changes | 1, self-contained | 2 or more means split |
| Refactoring mixed with behaviour | 0 | any means split |
| Reviewer response time | within 1 business day | longer means escalate, not wait |

A reviewer may legitimately decline to review an oversized PR and ask you to split it. Splitting
strategies, in order of preference:

| Strategy | Use when |
|---|---|
| Stacked PRs | Pieces are strictly dependent; stack so later work is unblocked during review |
| Vertical slice | One narrow feature end to end, shippable behind a flag |
| Horizontal layer | Schema, then repository, then API, then UI |
| By file or reviewer | Independent files with independent owners |

**The system must work after each PR lands, not only after the last one.** If piece 2 leaves trunk
broken, it is not a valid split. The only size exceptions are whole-file or whole-directory
deletions and purely mechanical tool-generated refactors — both reviewable in far less time per
line. Say in the description which one applies.

## 8. Pull Request Description

The PR title is a standalone imperative summary; the body carries what changed and why. On
squash-merge GitHub builds the commit message from the PR title plus, depending on the repository's
squash-message setting and the commit count, either the commit messages or the PR description — with a
single-commit PR it reuses that commit's message. Check your repo's setting; where the description is
the source, treat it as history rather than chat.

```markdown
## What
Scope order queries to the caller's tenant in the repository layer.

## Why
Orders were filtered by role only, so any authenticated user could read
another tenant's orders by id.

## Approach
Applied in OrderRepository, not per route, so a new endpoint cannot
forget it. Rejected middleware filtering: it cannot see the query.

## Known shortcomings
Legacy admin export still runs unscoped; tracked in #1190.

## Verification
`pytest -q` green; a manual cross-tenant read now returns 404.

Fixes #1183
```

- **Link issues with a real closing keyword**: `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`, or
  `resolve`/`resolves`/`resolved`. Repeat the full keyword per issue — `Resolves #10, resolves #123`.
  A bare `#123` links but never closes; `Fixes #1, #2` closes only `#1`. Cross-repo form is
  `KEYWORD OWNER/REPO#123`. Keywords only fire on merge **into the default branch**.
- **Open unfinished work as a draft.** Draft PRs cannot be merged and do not auto-request code
  owners; converting to ready-for-review is what requests them.
- **Re-read and update the description immediately before merging.** PRs change during review, and a
  stale description permanently misdescribes the commit it becomes.
- Never let `gh pr create --fill` write the body from an unreviewed `WIP` commit message.

## 9. Review Etiquette

**As reviewer:**

- **Approve once the change definitely improves the overall code health of the system, even if it is
  not perfect.** There is no perfect code, only better code. Withholding approval for perfection
  stalls delivery and trains authors to batch work into larger, worse changes.
- Review in priority order: design, functionality, complexity, tests, naming, comments, style,
  consistency, documentation, then every line. "Too complex" means *a reader cannot understand it
  quickly*; flag speculative generality built for a future that has not arrived.
- **Label severity on every non-blocking comment.** Unlabelled comments read as merge blockers.

| Prefix | Meaning |
|---|---|
| `Nit:` | Trivial, non-blocking, author may ignore |
| `Optional:` / `Consider:` | Worth thinking about, not required |
| `FYI:` | Information for next time, no action now |
| *(unprefixed)* | Blocking; must be addressed |

**Default: the prefixes above.** The alternative is Conventional Comments' `<label> [decorations]:
<subject>` form — primary labels `praise`, `nitpick`, `suggestion`, `issue`, `todo`, `question`,
`thought`, `chore`, `note`, with `(non-blocking)`, `(blocking)`, `(if-minor)` decorations. If your team
uses it, label *every* comment and drop the unprefixed-means-blocking rule: there, blocking-ness is the
`(blocking)` decoration, not the absence of a prefix. Never mix the two schemes in one repo — a
reviewer who does leaves blocking comments that read as optional.

- **Comment on the code, never on the developer**, and always give the reasoning. An unexplained
  request is an arbitrary gate that teaches nothing. Call out genuinely good work too.
- Do not interrupt focused work for a review; do it at your next break point, and within one
  business day at the latest. Use "LGTM with comments" when you trust the author to finish the rest.

**As author:**

- **If a reviewer misread your code, change the code or add a code comment.** Explanations that live
  only in the review thread do not help the next reader, who will misread it the same way.
- Never reply in anger. Step away, then respond to the technical content.
- Resolve disagreement on technical facts and data, not preference. The style guide is the authority
  on style; on a genuine wash the author's preference stands; a deadlock goes to a lead rather than
  leaving the PR to sit.

## 10. Rebase, Merge, and History

**The golden rule: never rebase commits that exist outside your repository and that people may have
based work on.** Rewriting published history forces everyone downstream to repair their branches by
hand and produces duplicate commits with identical author, date, and message.

| Operation | Unpushed local commits | Pushed branch, only you use it | Shared or default branch |
|---|---|---|---|
| `commit --amend` | Yes | Yes, then `git push --force-with-lease` | Never |
| `rebase` / `rebase -i` | Yes | Yes, then `git push --force-with-lease` | Never |
| `reset --hard` | Yes | Yes, then `git push --force-with-lease` | Never |
| `push --force` | n/a | Never — use `--force-with-lease` | Never |
| `revert` | Yes | Yes | Yes — this is the correct tool here |

- `--force-with-lease` updates the remote only if its ref still matches the value you last observed,
  so it refuses to delete a collaborator's pushed commit; bare `--force` does not check. Add
  `--force-if-includes` for a stronger guarantee; anything running `git fetch` in the background (an
  IDE, a shell prompt) weakens the lease. It is a **`git push`** option only — there is no
  `git rebase --force-with-lease`.
- Fold review fixups into their target commit: `git commit --fixup=<commit>` (or `--squash=`) then
  `git rebase -i --autosquash origin/main` — or, with no TTY,
  `GIT_SEQUENCE_EDITOR=: git rebase --autosquash origin/main` (section 14 rule 8). That bare
  non-interactive form **requires Git 2.44 or newer**, whose release notes announce that
  "`git rebase --autosquash` is now enabled for non-interactive rebase"; before 2.44 the flag only
  rewrote `rebase -i`'s todo list, so without `-i` it was silently ignored and every `fixup!` survived
  to ship. Check `git --version` first, and on older Git use
  `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/main`, which folds fixups on every version.
  `--autosquash` is incompatible with the apply backend either way. Never append "address review
  comments" commits; they make `bisect` and `revert` useless later.
- **Resolving a conflict is an edit, not a merge decision.** Never take `--ours`/`--theirs` wholesale;
  it silently discards one side's work. Re-run the tests before `git rebase --continue`. A conflict
  resolved inside a rebase never shows up in the final diff, which makes it the least-reviewed code
  on the branch.
- Clean up before you push, or while the pushed branch is still yours alone. Once anyone else may
  have based work on it, the only safe correction is a new commit. A human should run
  `git config pull.rebase true` and `git config rebase.autoSquash true` once during onboarding so this
  is the default; an agent must not change git config (section 14 rule 21).

**Merge strategy — pick one per repository and encode it in settings.** Mixing them ad hoc makes
history unreadable and `git log` filters unreliable.

| Strategy | What it does | Choose when |
|---|---|---|
| Squash and merge | Collapses the PR into one commit on the base; the generated message depends on the repo's squash-message setting and the number of commits | **Default.** The PR is one logical change with messy intermediate commits |
| Merge commit | Preserves every commit and adds an explicit merge (`--no-ff`) | Each commit is individually meaningful and worth bisecting |
| Rebase and merge | Replays each commit onto the base with new SHAs and updated committer info, no merge commit | Commits are already clean and linear history is required |

- **Do not squash-merge a long-running branch that other branches were cut from.** After the squash,
  later PRs still carry the pre-squash commits and you get cascading conflicts.
- Squash-merge can make the PR description permanent. See section 8.

## 11. Releases: Versions, Tags, Changelogs

Follow **Semantic Versioning 2.0.0**: `MAJOR.MINOR.PATCH`.

| Bump | For | Derived from |
|---|---|---|
| MAJOR | Incompatible API change | `!` marker or `BREAKING CHANGE` footer |
| MINOR | Backward-compatible functionality | any `feat` in the range |
| PATCH | Backward-compatible bug fix | any `fix` in the range |

- The `Derived from` column is the **spec's** mapping. Your release tool may bump PATCH for further
  types (section 5), so read its rules rather than hand-computing the version from this table.
- **A released version's contents must never be modified** — any change requires a new version.
  Retagging a shipped release breaks caches, lockfiles, and mirrors.
- `0.y.z` is initial development: anything may change at any time and nothing is stable. `1.0.0` is
  where you declare the public API.
- Pre-releases are `1.0.0-alpha.1` and have **lower** precedence than `1.0.0`. Build metadata after
  `+` is **ignored for precedence** — never encode a meaningful difference there, or two versions
  compare as equal.

**Tags:**

| Rule | Command |
|---|---|
| Use annotated tags for releases, never lightweight | `git tag -a v1.4.0 -m "Release 1.4.0"` |
| Sign them where the project requires provenance | `git tag -s v1.4.0 -m "Release 1.4.0"` |
| Verify a signature | `git tag -v v1.4.0` |
| Push explicitly — `git push` does **not** send tags | `git push origin v1.4.0` or `git push --follow-tags` |

Annotated tags are checksummed objects carrying tagger, date, message, and optional signature; a
lightweight tag is a bare pointer with no provenance. Assuming `git push` sends tags is how a release
lands untagged and its CI never fires.

**Changelog — follow Keep a Changelog** (the site serves the current spec at `/en/1.1.0/`; its own changelog runs to 1.1.2, 2024-09-27).

```markdown
## [Unreleased]

## [1.4.0] - 2026-03-04
### Added
- Tenant-scoped order listing endpoint.
### Fixed
- Webhook sender no longer retries indefinitely on a 4xx response.
### Security
- Order queries are now scoped to the caller's tenant.
```

- Six change types only: **Added, Changed, Deprecated, Removed, Fixed, Security.**
- Newest version first, an `Unreleased` section at the top, every version dated in ISO 8601
  `YYYY-MM-DD` (never `03/04/2026`), every section linkable.
- **Changelogs are written for humans.** Never paste `git log` output — it is full of merge commits
  and obscure titles. Never omit deprecations; a silent deprecation is how you break a consumer.

## 12. Gates

Local hooks are per-clone and advisory. **Re-run the same hooks in CI**, or an unhooked machine
bypasses every check.

```bash
# Once per clone, part of onboarding
pre-commit install --install-hooks && pre-commit install --hook-type commit-msg

# Resolve the trunk once, then use it everywhere; never hardcode origin/main
git fetch origin --prune                      # stale refs make every gate below measure the wrong base
TRUNK=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || echo origin/main)  # if unset: git remote set-head origin -a
# Not `git rev-parse --abbrev-ref origin/HEAD`: with origin/HEAD unset it prints "origin/HEAD" AND exits 128, so `|| echo` keeps both lines

# Before every commit
git status --porcelain                        # then stage explicit paths
git diff --staged                             # read what you are about to commit
git diff --check                              # whitespace errors
pre-commit run gitleaks                       # secret scan (gitleaks' own hook; or detect-secrets)

# Before the first push / requesting review (unpushed branch)
git --version                                 # non-interactive --autosquash needs git >= 2.44
# Next line rewrites history: only while unpushed. If already pushed, fold fixups only on explicit instruction, then git push --force-with-lease
GIT_SEQUENCE_EDITOR=: git rebase --autosquash "$TRUNK"   # fold fixup!/squash! commits; needs git >= 2.44, else add -i
npx commitlint --from="$TRUNK" --to=HEAD --verbose
git diff --stat "$TRUNK"...HEAD | tail -1     # >1000 changed lines: split
git log --oneline "$TRUNK"..HEAD              # no wip/fixup/squash subjects left
git branch -r --sort=-committerdate | head    # active-branch audit

# In CI (binding), and before merging
pre-commit run --all-files                    # or --from-ref "$TRUNK" --to-ref HEAD
gh pr view --json isDraft,reviewDecision,statusCheckRollup,body

# At release
git describe --tags --exact-match HEAD        # the release commit is actually tagged
# Assertions, not bare greps: `grep -v` exits 1 when every tag is valid, failing a healthy repo in CI
! git tag -l | grep -qvE '^v?[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$' || { echo 'non-semver tag'; exit 1; }
! git for-each-ref --format='%(refname:short) %(objecttype)' refs/tags | grep -qv ' tag$' || { echo 'lightweight tag'; exit 1; }
```

- Commit `.pre-commit-config.yaml` to the repository and **pin every `rev`** — an unpinned hook
  changes behaviour under the team with no commit recording it. Run `pre-commit autoupdate` on a schedule, as a `chore:`
  commit, so the change is auditable.
- Record your project's own baselines the first time you run these (active branch count, typical PR
  size). Those numbers are yours to improve; do not adopt another repo's.
- `git commit --no-verify` bypasses **both** the `pre-commit` and `commit-msg` hooks. Reserve it for a
  genuine emergency, say so in the PR, and never wire it into a script or alias.

## 13. Emergencies

| Is an emergency | Is not an emergency |
|---|---|
| A blocked major launch | A soft deadline |
| A significant user-facing production bug | Wanting the change in today |
| An urgent legal issue | The reviewer being in another timezone |
| A critical security hole | Friday afternoon, or manager pressure |
| A rollback that stops a live production outage | Rolling back a change that only breaks tests or the build |

An emergency change must be **minimal and scoped strictly to resolving the crisis**, and must be
reviewed thoroughly again afterwards. The fast path exists because the change is small enough to verify
quickly; spending it on soft deadlines means the discount is gone when it matters.

## 14. AI Agent Rules

When operating on a repository, the agent **must**:

1. **Never run `git commit` unless the user asked for a commit in this session.** The default deliverable is working code plus a proposed message. "The work looks finished" is not consent.
2. **Never run `git push` unless the user asked to push.** Committing is not permission to publish.
3. **Never `git tag`, create a release, or open a PR unless asked.** Each is a separate authorisation.
4. **Never merge, approve, or close a pull request, and never merge into the default branch, unless the user asked for that specific action.** No `gh pr merge` — and never `--admin`, which bypasses branch protection — no `gh pr review --approve`, no `git merge` into trunk, no `gh pr close`. Approving your own or another agent's work is not review. Leaving a review comment on someone else's PR is a separate authorisation again: draft the comment for the user unless you were asked to post it.
5. **Do not commit directly to the default branch unless that is demonstrably the repo's convention.** Resolve the default branch with `git symbolic-ref --quiet --short refs/remotes/origin/HEAD` and strip the `origin/` prefix; if it is unset, run `git remote set-head origin -a` or ask. Get the current branch separately with `git branch --show-current` (empty output means detached HEAD — stop and ask), then compare the two bare names. If they match, read `git log --oneline -20`: history made of PR merges means create and switch to a topic branch first; history of direct commits to trunk means say so and confirm before committing.
6. **Never amend, rebase, `reset`, force-push, or otherwise rewrite any commit that has been pushed or shared** — and never rebase a branch you did not create in this session — without an explicit instruction naming that operation. Published history is not yours to edit. To undo a shared commit, use `git revert`.
7. **When force-pushing your own session branch after an instruction to do so, use `--force-with-lease`.** Never bare `--force`.
8. **Never use interactive git flags in a non-interactive session** — `rebase -i` without a no-op sequence editor, `add -i`, `add -p`, `commit` without `-m`, or anything that opens an editor or a pager. Where the workflow wants an interactive step, either avoid it (stage whole files rather than hunks), run it non-interactively by forcing a no-op sequence editor (`GIT_SEQUENCE_EDITOR=: git rebase --autosquash <trunk>`, or `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash <trunk>` on Git older than 2.44 — section 10), or hand that step to the user.
9. **Never bypass a hook or a check to force something green.** No `--no-verify`, no `SKIP=`, no `[skip ci]`, no disabling a rule, no marking a test skipped to get a pass. If a gate fails, report the failure and the actual output, and stop.
10. **Report what hooks and CI actually did.** Never state that tests pass, lint is clean, or a build is green unless you ran it in this session and read the output. Quote the real result.
11. **Stage deliberately** (section 2 rule 6) — `git add -A` and `git add .` sweep in unrelated local edits, build artifacts, and untracked credential files.
12. **Read `git status` and `git diff --staged` before every commit.** Blind-adding is how secrets ship.
13. **Never commit or push secrets, tokens, `.env` files, private keys, credentials, or large binaries.** If the staged diff contains anything that looks like one, stop and ask. A pushed secret is public, and removing it means rewriting published history — the hardest operation to undo.
14. **Never include unrelated formatting churn.** No reformatting untouched files, no drive-by renames, no reordering imports outside the change. Real defects hide behind mechanical noise.
15. **Follow the canonical rules in section 2** (one logical change, imperative subject within `header-max-length`, blank line, body stating the problem and the reason), and match the repo's existing message style (check `git log --oneline -20` first) over this document's.
16. **Describe only changes you actually made**, verified against the diff. No claimed benchmarks, no "fixes #N" for an issue you did not read, no invented rationale.
17. **Never add `Signed-off-by` for a human, and never use `git commit -s`/`--signoff` on their behalf.** That trailer is a legal certification under the Developer's Certificate of Origin that the signer wrote the change or has the right to submit it. Only the named person can assert it.
18. **Never set or override commit authorship.** No `--author`, no `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_*` overrides, no `--date`. Commit under whatever identity the clone is already configured with; if it is wrong or unset, stop and ask.
19. **Disclose machine authorship where the project's policy permits it** — a `Co-authored-by: Name <email@example.com>` trailer after a blank line — and **check that policy first.** Some projects reject AI-generated contributions outright; Git itself states it will "reject anything that looks AI generated … or that senders don't understand or cannot explain."
20. **Before deleting or overwriting anything, look at the target first.** Read the file, the branch, or the tag you are about to replace. `git checkout --`, `git clean`, `git reset --hard`, and branch deletion destroy uncommitted work irreversibly.
21. **Never change git config, hooks, remotes, or branch protection** as a side effect of a task.
22. **Never enable, disable, or configure commit signing on the user's behalf** — no `commit.gpgsign`, no `-S`, no SSH signing key. If the branch requires signed commits, stage the work, say that signing is required, and hand the commit to the user.
23. **When something is ambiguous — which branch, which merge strategy, whether to commit — ask.** Guessing here is expensive and, for history rewrites, unrecoverable.

## 15. Review Checklist

For an AI reviewer. Flag only real defects; cite `file:line` and state the failure scenario.

**Commit structure** — is each commit one logical change? Does every commit build and pass its own tests? Are refactors, renames, and reformats separated from behaviour changes? Any `wip`/`fixup!`/`squash!`/"address review comments" commits left unsquashed? Any whitespace-only churn in otherwise untouched files?

**Commit messages** — imperative subject per section 2, no trailing period? Blank line before the body? Does the body state the problem and why this approach, rather than restating the diff? Any placeholder message (`fix bug`, `updates`, `WIP`)? If the repo uses Conventional Commits: valid type from the project's enum, correct scope, `feat`/`fix` used only for features and fixes? Is a breaking change marked with `!` or an uppercase `BREAKING CHANGE:` footer rather than buried in prose? Are footers formatted as git trailers?

**PR scope** — one self-contained change? Changed-line count near 100 and well under 1000, or an explicit justification (whole-file deletion, mechanical refactor)? Does trunk still work if only this PR lands? Should this have been split, and along which axis?

**PR description** — title a standalone imperative summary? Body covering what, why, approach, known shortcomings, and how it was verified? Issue linked with an actual closing keyword, repeated per issue? Description still accurate after review changes? Is the PR still marked draft even though it is being offered for review, or ready-for-review while still unfinished?

**Tests** — does a test ship with the change? Does it fail when the production code is broken? Are error paths and edge cases covered, not just the happy path?

**History safety** — does this branch force-push over shared commits? Any amend or rebase of published history? Is `--force` used where `--force-with-lease` belongs? Is a long-running branch about to be squash-merged with other branches cut from it? Is the repository's single merge strategy being followed? Was any conflict resolved mid-rebase taken wholesale from one side, and were the tests re-run before `--continue`? Was the PR merged, approved, or closed without an explicit request, or merged with `--admin` over a failing check?

**Branching** — branch cut from current trunk? Short-lived, or has it been open for days? Is incomplete work behind a flag rather than parked on a branch? Are merged branches deleted?

**Secrets and artifacts** — any `.env`, key, token, credential, or connection string in the diff? Any generated files, lockfile churn, or large binaries that should be ignored? Is `.gitignore` updated for anything new that is generated?

**Gates** — did the hooks and CI actually run and pass, with output shown? Any `--no-verify`, `SKIP=`, `[skip ci]`, disabled rule, or skipped test used to force green? Are `.pre-commit-config.yaml` revs pinned? Do CI hooks match the local ones? Was any `--autosquash` rebase run on a Git old enough (before 2.44) to ignore the flag without `-i`?

**Release** — version bump consistent with the commit types in the range under the project's own release rules? Is the release commit annotated-tagged and the tag pushed? Is a released version being modified or retagged? Changelog updated under the right Added/Changed/Deprecated/Removed/Fixed/Security heading, newest first, ISO 8601 date? Anything deprecated but unlisted?

**Attribution and review conduct** — is a `Signed-off-by` present for someone who did not sign it? Is the author, committer, or date overridden (`--author`, `GIT_AUTHOR_*`/`GIT_COMMITTER_*`, `--date`) instead of the clone's configured identity? Is machine authorship disclosed per project policy with a correctly formatted `Co-authored-by` trailer? Is every non-blocking review comment labelled under the repo's single scheme — `Nit:`/`Optional:`/`FYI:`, or Conventional Comments labels with `(non-blocking)` — with no mixing of the two, aimed at the code rather than the author, and reasoned? Is approval being withheld for perfection rather than for code health?

## References

Sources for every rule above are documented in the upstream repo:
https://github.com/Madheshvivekanandan/ai-engineering-skills (skills/git-commit-pr-workflow/references/sources.md).
