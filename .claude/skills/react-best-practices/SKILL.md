---
name: react-best-practices
description: React/TypeScript engineering standard for Vite + React 18 SPAs built with Refine, MUI, react-hook-form, and react-router v6. Load BEFORE writing, modifying, or reviewing any React code in such an app — anything under src/ (pages/, components/, providers/, hooks) or any .tsx/.ts component, hook, data fetch, form, MUI DataGrid, or theme change. Covers component architecture, naming, state management, TypeScript, error handling, forms, testing, security, accessibility, performance (waterfalls, bundle size, re-renders), tooling gates, and a review checklist.
license: MIT
metadata:
  perf-rules-adapted-from: vercel-labs/agent-skills — skills/react-best-practices (MIT, v1.0.0)
  stack: vite + react 18 + typescript + refine + mui
---

# React Best Practices (Vite + Refine + MUI SPA)

Correctness and clarity first, then performance. Performance rule IDs
(`async-parallel`, `rerender-memo`, …) come from **Vercel Engineering's
react-best-practices** (MIT, `metadata.json` version 1.0.0) and stay traceable upstream:
`https://github.com/vercel-labs/agent-skills/tree/dc8367e6f91c/skills/react-best-practices/rules`

Every rule ID named in this document was checked against that directory on **2026-08-20** and
exists there as `rules/<id>.md`; none is invented. What is *not* inherited is the justification —
several upstream rules are written for Next.js/RSC or for React 19 APIs, and where this document
keeps such an ID it says so at the rule (§0, §8, §9). Upstream publishes no git tags or releases
and `main` is still moving, so the link above pins the last commit that touched the skill directory
(`dc8367e6f91c`, 2026-04-14) rather than `main`. MIT is stated in upstream's root `README.md` and
skill frontmatter; the repository has no `LICENSE` file, so there is no upstream copyright line to
reproduce. Full provenance in §15.

## 0. Target Stack & What Does Not Apply

This skill targets a **Vite + React 18 SPA** (TypeScript 5.4, `strict: true`), not Next.js:

```
src/
  pages/<feature>/          # route screens
    components/             #   feature-local components
  components/common/, components/layout/
  providers/                # Refine data/auth providers (dataProvider.ts, authProvider)
  interfaces/               # shared domain types
  config/, theme/, utils/
```

- Stack: `@refinedev/core` + `@refinedev/mui`, MUI 5 (`@mui/material`, `@mui/x-data-grid`,
  `@mui/x-date-pickers`), `react-hook-form`, `react-router-dom` v6, `axios`, `dayjs`.
- Import alias `@/*` → `src/*` is configured — prefer it over deep `../../..` chains.
- Money is **INR**. Use a shared formatter (`Intl.NumberFormat("en-IN", {currency:"INR"})`);
  never hand-concatenate a symbol, never float-accumulate currency.

**Next.js / RSC / React-19 concepts that DO NOT apply here — never suggest them.** Some rows name
a real upstream rule ID; others name a framework API upstream never wrote a rule for.

| Not applicable | Why |
|---|---|
| RSC / Server Components, `"use client"` | No RSC; everything is a client component. |
| `next/dynamic`, `next/script` (and Next's image/font components, which upstream has no rule for) | No Next.js. Use `React.lazy` + `<Suspense>`; plain `defer`/`async` on scripts in `index.html`. |
| Server actions, `server-auth-actions`, `after()` | No server runtime; this is a pure client SPA calling a separate backend API. |
| `server-cache-react` (`React.cache()`), RSC prop serialization | Server-only APIs. |
| SSR hydration rules (`rendering-hydration-*`) | SPA — no SSR/hydration step. |
| SWR (`client-swr-dedup`) | Refine wraps TanStack Query, which already dedupes/caches. Don't add SWR. |
| `rendering-activity` (`<Activity>`) | React 19.2 API — not available on React 18. See §8 for the React 18 alternative. |
| `rendering-resource-hints` (`preload`/`preconnect` from `react-dom`) | React 19 APIs, and upstream frames them as server-component guidance. Use plain `<link rel="preconnect">`/`<link rel="preload">` in `index.html`. |
| `advanced-effect-event-deps` (`useEffectEvent`) | React 19.2 API. Use `advanced-use-latest`/`advanced-event-handler-refs` instead (§9). |

**React 18 pins the behaviour here; react.dev now documents 19.2**, so a page you land on may
describe an API this app does not have. React-19-only features that look applicable but are not:
async functions in `startTransition` (Actions), `useActionState`, `useOptimistic`,
`useDeferredValue(value, initialValue)`, `use`, `ref` as a prop, ref cleanup functions, and — new
in 19.2 — `<Activity>` and `useEffectEvent`. For React 18 behaviour read `https://18.react.dev`.

## 1. Philosophy

- **Readability over cleverness**; the next reader is the maintainer.
- **Correctness and clarity before optimization.** Only optimize with a measurement.
- **Colocate, then extract.** Keep code near its use; extract when a second caller appears.
- **One responsibility per component.** Data-shaping, side effects and markup want separating.
- **Make invalid states unrepresentable** with types, rather than defending against them at runtime.
- **Never leave the user staring at a blank screen** — every async path has loading and error states.

## 2. Component Architecture & Naming

**Size limits (enforced in review).** Extract past these:

| Unit | Limit |
|---|---|
| Component file | **≤ 250 lines** |
| Component function body | ≤ 120 lines / ≤ 5 hooks doing unrelated work |
| JSX nesting depth | ≤ 4 |
| Props on one component | ≤ 8 (past that, group into an object or split) |

> Most codebases have files that already exceed these limits. Find this project's before you
> start: `find src -name '*.ts*' -exec wc -l {} + | awk '$1 > 250 && $2 != "total"' | sort -rn`.
> **Never grow a file that is already over the limit** — when editing one, extract the part you
> touch into `pages/<feature>/components/`. Don't refactor wholesale unless asked.

- **Split by responsibility:** a page composes; child components render sections; **custom hooks
  own data + logic**. If a component both fetches/derives and renders 200 lines of JSX, the
  fetch/derive half becomes `use<Feature>()` in the feature folder.
- **New feature** → `pages/<feature>/` with a `<Feature>Page.tsx` + `components/`.
  Reusable across features → `components/common/`. Shared types → `interfaces/`.
- **Composition over prop-drilling and over configuration flags.** Prefer `children`/slots to a
  `variant`-plus-ten-booleans API. Past 2 levels of drilling, use context or restructure.
- **No inline component definitions** — see `rerender-no-inline-components` (§8).

**Naming**

| Kind | Convention | Good | Bad |
|---|---|---|---|
| Component file + fn | `PascalCase`, matching | `CreditProfileCard.tsx` | `card2.tsx`, `index.tsx` everywhere |
| Hook | `use` + noun/verb | `useTicketFilters()` | `ticketStuff()` |
| Event handler (internal) | `handle*` | `handleSubmit` | `onSubmitClick2`, `doIt` |
| Event prop (external) | `on*` | `onApprove` | `approveCb` |
| Boolean prop/state | `is/has/can/should*` | `isCreditBlocked` | `flag`, `status2` |
| Constant | `UPPER_SNAKE` module scope | `MAX_LINE_ITEMS` | inline `50` |
| Type / interface | `PascalCase`, no `I` prefix | `Ticket`, `CreditProfile` | `ITicket`, `TicketType2` |
| Units in the name | always | `timeoutMs`, `amountInr` | `timeout`, `amount` |

- Name for the **domain**, not the mechanism: `unpaidInvoices`, not `data2`/`filteredList`.
- Never `data`, `item`, `tmp`, `res`, `x` as a meaningful identifier.

## 3. State Management — Pick the Right Location

Choosing wrong here causes most React bugs. In priority order:

1. **Server state → Refine hooks** (`useList`, `useOne`, `useCustom`, `useUpdate`).
   Never mirror fetched data into `useState`; that's a stale-copy bug. Never hand-roll
   `useEffect` + `axios` + `setState` — you lose dedup, caching, and cancellation.
2. **URL state → `useSearchParams`** (react-router v6). **Filters, pagination, sort, active tab,
   and selected-row id belong in the URL**, not `useState`. Makes views shareable and
   refresh-survivable. This is the most-missed rule in table-heavy screens
   (tickets, receivables, payables).
3. **Local UI state → `useState`/`useReducer`** in the *nearest* owner: open/closed, hover, draft
   input. `useReducer` once state updates get complex enough to cause bugs — as a local bright
   line, 3+ fields changing together or transitions with rules. That threshold is this document's
   convention, not React's: react.dev treats `useState`-vs-`useReducer` as partly preference, and
   the reducer's real payoff is a pure function you can unit-test in isolation.
4. **Cross-cutting → context**, sparingly (auth/user, theme, notifications). Split providers by
   concern and keep values memoized — one god-context re-renders the whole app on any change.

- **Derive, don't duplicate.** Compute during render from the source of truth; no `useEffect` to
  sync two pieces of state (see `rerender-derived-state-no-effect`).
- **Single source of truth.** If two states can disagree, one must be derived.
- Reset child state on identity change with a `key`, not an effect.

## 4. TypeScript

- `strict: true` is on — keep it. **`tsc` gates `npm run build`.**
- **No `any`.** Use `unknown` + narrowing, a real interface, or a generic. If unavoidable, a
  comment must justify it. *(If the project carries pre-existing `any`s, measure that count first,
  then add none and remove the ones in files you touch.)*
- **Type API responses at the boundary** (`interfaces/`) and use those types inward. Don't let
  `any` from `axios`/`dataProvider` leak into components.
- **Discriminated unions over optional-flag soup** — model states as
  `{status:"loading"} | {status:"error"; error:E} | {status:"ok"; data:D}`, so impossible
  combinations don't typecheck.
- Prefer `type` for unions/aliases, `interface` for object shapes that may be extended.
  No `I` prefix. `satisfies` to keep literal inference while checking a shape.
- `import type { … }` for type-only imports (lint enforces).
- Type props explicitly; avoid `React.FC` — it can't express a generic component signature, forces
  the return type, and has known `defaultProps` problems. (Don't cite children as the reason:
  `@types/react` 18 — the version this stack pins — removed the implicit `children` prop, so
  declare `children: React.ReactNode` when you accept it.) Use `ComponentProps<typeof X>` to extend
  MUI component props rather than restating them; reach for `ComponentPropsWithoutRef` /
  `ComponentPropsWithRef` when `ref` forwarding matters.
- Never `@ts-ignore`; `@ts-expect-error` with a reason comment if truly needed.

## 5. Error Handling & Resilience

- **Error boundaries are mandatory.** Without one, a single render throw blanks the entire SPA.
  Wrap (a) the app shell and (b) each independently-failing panel — a dashboard card must not
  take down the page. Boundaries catch errors thrown **while rendering**, and in lifecycle methods
  and constructors. They do **not** catch event-handler errors, throws inside
  `setTimeout`/`requestAnimationFrame`/a bare promise rejection, or an error thrown by the boundary
  component itself rather than its children — `try`/`catch` those yourself.
  Two documented exceptions *do* reach a boundary: a throw inside `startTransition` from
  `useTransition`, and a rejected `React.lazy()` import. The second matters here, because §8 makes
  `React.lazy` the route-splitting mechanism and a failed chunk load is exactly that case — so
  every `<Suspense>` boundary needs an error boundary beside it.
- **Every mutation handles failure.** Never fire-and-forget a write: on failure, surface a
  message, keep the user's input, and re-enable the control. Never swallow — no empty `catch`.
- **Map status codes to behaviour**, centrally in the provider/interceptor:
  `401` → re-auth; `403` → forbidden view (a dedicated `forbidden/` route is the clean pattern);
  `422` → field-level form errors (§6); `5xx`/network → retryable "something went wrong".
- **Retries** only for idempotent reads (GET), bounded with backoff. **Never auto-retry a
  non-idempotent write** — retrying a credit approval or invoice post can double-apply it.
- Timeouts on every request; treat "no response" as a failure state, not a permanent spinner.
- Show three distinct states — **loading / empty / error** — and never conflate empty with error.
- Log with `console.error` and real context; **never log tokens, credentials, or customer PII**.

## 6. Forms & Validation (react-hook-form)

These screens move money — credit requests, invoices, dispatch. Treat forms as critical paths.

- **Schema-validate** (zod/yup + resolver) as the single source of truth for rules; infer the TS
  type from the schema so types and validation can't drift.
- **Validate on the server too, always.** Client validation is UX, never a trust boundary.
- **Prevent double submit:** disable the submit control while `isSubmitting`. A double-click that
  posts a payment twice is a data-integrity incident.
- **Map server field errors back onto fields** via `setError`, with a form-level message for
  non-field errors. Don't drop a 422 into a toast and lose which field was wrong.
- Use **`Controller`** for MUI inputs that don't expose the native input's ref, or whose value
  isn't a plain DOM value — `Select`, `Autocomplete`, `DatePicker`, `Checkbox`/`Switch` groups. The
  documented trigger is **ref exposure, not controlled-ness**: a plain `TextField` takes
  `{...register("field")}` directly (MUI forwards it to the input) and is cheaper, because
  react-hook-form is ref-based by design. Where a field must stay controlled,
  `Controller`/`useController` isolates re-renders to that one field instead of the whole form.
- Subscribe narrowly: **`useWatch` on the specific field**, never `watch()` on the whole form
  (re-renders everything per keystroke).
- Warn on navigate-away when `isDirty`. Reset via `reset()` after a successful submit.
- Money/quantity inputs: parse and validate as fixed-precision; enforce min/max and step; reject
  negatives explicitly rather than relying on the input type.
- Dates: the backend stores **UTC**. Convert at the boundary with `dayjs` and be explicit about
  timezone — naive local parsing produces off-by-one-day delivery dates.

## 7. Testing

If no test framework is configured (**recommended: Vitest + React Testing Library + MSW**), that
is a gap — say so, and don't claim tests were run until one exists. Once present:

- **Vitest + RTL + `@testing-library/user-event`**; **MSW** to mock the API at the network layer.
- **Test behaviour, not implementation.** Query by role/label/text as a user would
  (`getByRole("button", {name:/approve/i})`); never assert on state internals or snapshot whole trees.
- **Cover per feature:** happy path; **empty, loading, and error states**; validation failures;
  permission-denied (RBAC) rendering; and the money/rounding edges.
- Test **custom hooks** directly (`renderHook`) — that's where logic should live and it's the
  cheapest place to assert it.
- Deterministic: fake timers, fixed clock (no `new Date()` in assertions), seeded data, no
  network, no `sleep`. Use builders/factories over giant literal fixtures.
- **Every bug fix ships a regression test** that fails before the fix.
- Priority when adding coverage to an untested codebase: money/credit logic → form validation →
  status transitions → table filtering. Don't chase a coverage % on presentational markup.

## 8. Performance

### Waterfalls (CRITICAL)

- **`async-parallel`** — independent requests in `Promise.all`, never sequential `await`s.
- **`async-cheap-condition-before-await`** — cheap sync checks (permission, empty input) first.
- **`async-defer-await`** — start the promise early, `await` only in the branch that needs it.
- **`async-dependencies`** — don't make C wait on A when only B depends on A.
- **`async-suspense-boundaries`** — one boundary per independently-loading region, so one slow
  panel doesn't block the screen. Upstream's mechanism for this rule is **RSC streaming**, which
  does not exist here: on React 18 + Vite, `<Suspense>` covers `React.lazy` chunks and a data layer
  explicitly opted into suspense (TanStack Query's `useSuspenseQuery`) — you cannot suspend on a
  bare promise. Otherwise each panel owns its own loading state rather than sharing one. Pair every
  boundary with an error boundary (§5).

```ts
// Bad — 3 sequential round trips
const ticket   = await api.getTicket(id);
const credit   = await api.getCredit(ticket.customerId);
const products = await api.listProducts();

// Good — products is independent; credit genuinely depends on ticket
const productsPromise = api.listProducts();
const ticket = await api.getTicket(id);
const [credit, products] = await Promise.all([
  api.getCredit(ticket.customerId),
  productsPromise,
]);
```

Never `await` inside a loop over rows — collect promises, then `Promise.all`.

### Bundle size (CRITICAL)

- **`bundle-dynamic-imports`** — `React.lazy` + `<Suspense>` for heavy/deferred UI: DataGrid
  screens, date pickers, charts, export/print views, large dialogs. Route-level splitting per
  `pages/<feature>` is the cheapest win, and the largest genuine shipped-bytes win in this list.
  (Upstream states this rule as "use `next/dynamic`" — `React.lazy` + `<Suspense>` is the
  adaptation for this stack, which is why §0 bans `next/dynamic` while the rule ID stays.)
- **`bundle-analyzable-paths`** — static literal import paths only; no template-string `import()`.
- **`bundle-conditional`** — load admin/export-only modules when activated, not at module scope.
- **`bundle-defer-third-party`** / **`bundle-preload`** — analytics after first paint; `import()`
  on nav hover/focus.
- **`bundle-barrel-imports`** — import concrete MUI modules:

```ts
// Bad
import { Button, Dialog } from "@mui/material";
// Good
import Button from "@mui/material/Button";
import DeleteIcon from "@mui/icons-material/Delete";
```

  Be honest about why. MUI's own guide is explicit that Vite/Rollup **already tree-shake barrel
  imports out of the production bundle**; the real cost is **dev-server startup and rebuild time**
  (worst with `@mui/icons-material`). Path imports remain MUI's documented preference and the lint
  rule here, so count the project's existing barrel imports before you start and add none — but
  treat this as a DX and lint gate, not shipped bytes, and don't call it a bundle win without a
  `vite build` measurement (§1: only optimize with a measurement). Type-only barrels
  (`interfaces/`) are exempt either way: `import type` is erased at compile time.
- Register `dayjs` plugins once at app setup, not per component.

### Data fetching

- **Query keys.** With Refine hooks the key is *generated* from the hook's own properties
  (`resource`, `filters`, `sorters`, `pagination`, `id`), so pass parameters **as hook properties**
  rather than closing over them in a fetch — anything smuggled in outside those props is invisible
  to the cache. Where you write a key by hand (`useCustom`, a raw `useQuery`), include **every**
  result-affecting parameter (filters, pagination, customer id) or you serve stale/cross-contaminated
  data. Verify with the TanStack Query devtools.
- **Server-side** pagination/filtering for large tables; never fetch-all-and-filter-client-side.
- Invalidate precisely (affected resource/id) after mutations, not the whole cache.
- **`client-event-listeners`** one shared global listener, not one per row.
  **`client-passive-event-listeners`** `{passive:true}` for scroll/wheel/touch.
- **`client-localstorage-schema`** version and minimize persisted data; read once into memory
  (`js-cache-storage`), never in a render path.
- Ignore/abort stale in-flight responses so a slow earlier one can't overwrite a newer one.

### Re-renders

- **`rerender-derived-state-no-effect`** derive during render; no `useEffect`+`setState` to compute.
- **`rerender-no-inline-components`** never define a component inside a component — it remounts and
  loses state every parent render. **Includes DataGrid cell and slot renderers** — `renderCell`,
  plus `slots`/`slotProps` on `@mui/x-data-grid` v6+ or `components`/`componentsProps` on v5 (check
  the installed major; the rename landed in Data Grid v6). Hoist or `useCallback`.
- **`rerender-functional-setstate`** `setX(prev=>…)` keeps callbacks stable.
- **`rerender-defer-reads`** don't subscribe to state used only inside a callback.
- **`rerender-derived-state`** subscribe to the derived boolean, not the churning raw value.
- **`rerender-dependencies`** primitive deps, not freshly-built objects/arrays.
- **`rerender-lazy-state-init`** `useState(() => expensive())`.
- **`rerender-memo`** memoize genuinely expensive subtrees;
  **`rerender-simple-expression-in-memo`** don't memo a primitive comparison.
- **`rerender-memo-with-default-value`** hoist non-primitive defaults (`const EMPTY: readonly T[] = []`).
- **`rerender-split-combined-hooks`**, **`rerender-move-effect-to-event`**,
  **`rerender-transitions`** / **`rerender-use-deferred-value`** (responsive input over a big list),
  **`rerender-use-ref-transient-values`** (scroll/drag values).

> If React Compiler is adopted (it supports React 17/18/19) it handles most memoization, and
> `rerender-memo` / `rerender-simple-expression-in-memo` become escape-hatch guidance rather than
> defaults. Keep existing memoization in place when enabling it.

### Rendering

- **`rendering-conditional-render`** ternary, not `&&` — `{count && <X/>}` renders a literal `0`.
- **Stable, data-derived `key`s** (`ticket.id`); never array index on reorderable/filterable rows.
- **`rendering-hoist-jsx`** static JSX to module scope. **`rendering-content-visibility`** +
  virtualization for long lists. **`rendering-usetransition-loading`**,
  **`rendering-animate-svg-wrapper`**, **`rendering-svg-precision`**,
  **`rendering-script-defer-async`** (plain `defer`/`async` on scripts in `index.html`).
- Two upstream rendering rules are **React 19 APIs and do not apply on React 18** (§0).
  `rendering-activity` needs `<Activity>` (React 19.2): to stop an expensive tab panel remounting,
  keep it mounted and hide it with CSS, or hoist its state above the tab switch — don't import a
  component the installed React doesn't have. `rendering-resource-hints` needs `preload` /
  `preconnect` / `prefetchDNS` from `react-dom` (React 19): use `<link rel="preconnect">` and
  `<link rel="preload">` in `index.html` instead.

### JavaScript (lowest priority — never trade readability for these)

- **`js-set-map-lookups`/`js-index-maps`** build a `Map` once instead of `.find()` in a loop
  (the classic O(n²) in a table render).
- **`js-combine-iterations`**, **`js-flatmap-filter`**, **`js-early-exit`**,
  **`js-length-check-first`**, **`js-hoist-regexp`**, **`js-cache-property-access`**,
  **`js-cache-function-results`**, **`js-min-max-loop`**,
  **`js-tosorted-immutable`** (never mutate props/state in place), **`js-batch-dom-css`**,
  **`js-request-idle-callback`**.

## 9. Hooks Correctness

- Rules of Hooks: top level of a component or custom hook only — never in a condition, loop, or
  after an early return, and never inside `try`/`catch`/`finally`, an event handler, a class
  component, or a function passed to `useMemo`/`useReducer`/`useEffect`.
- **Complete dependency arrays.** Never silence the lint by deleting a dep — fix the design
  (hoist, ref, functional update, stable callback).
- **Effects synchronize with external systems** (subscriptions, listeners, imperative APIs) —
  not for deriving data or reacting to your own `setState`.
- **Always clean up**: listeners, timers, subscriptions, aborts. A missing cleanup leaks the
  subscription or timer — connections pile up as the user navigates — and lets a stale response
  overwrite fresh state. **Silence is not evidence of correctness:** React removed the
  set-state-on-an-unmounted-component warning in **18.0**, the version this skill targets, so you
  will never be warned about it.
- **`advanced-use-latest`/`advanced-event-handler-refs`** stable callback identity without stale
  closures — these are the React 18 answer to the stale-closure problem. **`advanced-init-once`**
  app init once per load, not in `useEffect([])`. Upstream's **`advanced-effect-event-deps`** is
  about `useEffectEvent`, a React 19.2 API, and does not apply here (§0).

## 10. Security

- **Never `dangerouslySetInnerHTML`** with server/user content. If unavoidable, sanitize
  (DOMPurify) and justify in a comment. React escapes by default — don't defeat it.
- **Client-side authorization is display logic, not enforcement.** Hiding a button is UX; the
  backend must authorize every action. Never treat an RBAC check in the SPA as a control.
- **No secrets in the frontend.** Anything in `import.meta.env` shipped to the browser is public —
  no API keys or signing secrets. Only `VITE_`-prefixed public config.
- Tokens: prefer httpOnly cookies; if `localStorage` is used, accept the XSS exposure, keep TTLs
  short, and clear on logout. Never log or put a token in a URL/query param.
- Validate and allow-list any URL used in `href`/`src`/redirect (block `javascript:`, open redirects);
  `rel="noopener noreferrer"` on `target="_blank"`.
- Never render raw backend errors/stack traces to users; no PII or tokens in `console`.

## 11. Accessibility

Target **WCAG 2.2 Level AA**. Criterion numbers are given so a review finding can be escalated to a
real conformance failure rather than argued as taste; Level A items are the floor, not a
nice-to-have.

- Semantic elements first (`button`, `nav`, `table`); ARIA only to fill genuine gaps — the First
  Rule of ARIA Use.
- Every input has a **programmatically associated label** (SC 1.3.1, A), and a label must exist at
  all wherever content requires input (SC 3.3.2, A).
- **Errors: identify the field *and* describe the error in text** (SC 3.3.1, A) — a red border with
  no message fails, which is stronger than "not colour alone". Link the message with
  `aria-describedby` and set `aria-invalid` on the control. (W3C's forms tutorial endorses
  `aria-describedby`; MDN recommends `aria-errormessage`, which is semantically tighter. Pick one
  and stay consistent. Don't set `aria-invalid` on an untouched required field before a submit
  attempt.) Encoding the error by colour alone is a separate failure — SC 1.4.1, A.
- **Icon-only buttons need an accessible name** (`aria-label`) — SC 4.1.2, A.
- Keyboard reachable and operable (SC 2.1.1, A). **Visible focus** — never remove an outline
  without a replacement (SC 2.4.7, AA; doing so is documented failure F78). A focused row or field
  must also not end up **entirely hidden** behind a sticky AppBar, a sticky DataGrid header, or an
  open Snackbar (SC 2.4.11, AA — new in WCAG 2.2). The quantified indicator spec (≥ 2 CSS px
  perimeter, 3:1 focused-vs-unfocused) is SC 2.4.13, **AAA** — aim for it, but it is not required
  at AA.
- Dialogs move focus inside on open, wrap Tab within, and return focus to the invoking element on
  close (WAI-ARIA APG Modal Dialog pattern). MUI `Dialog`/`Modal` does all three by default — don't
  fight it, and only set `disableAutoFocus`/`disableEnforceFocus`/`disableRestoreFocus` with a
  documented reason. The focus trap is permitted **only because the user can escape it**, so keep
  the dialog keyboard-dismissible — Escape plus a visible Cancel/Close (SC 2.1.2, A). MUI does
  **not** label the dialog for you: add `aria-labelledby` pointing at the `DialogTitle` id, and
  `aria-describedby` where there is descriptive body text.
- **Contrast:** body text ≥ 4.5:1 (SC 1.4.3, AA); large text — ≥ 18pt, or ≥ 14pt bold — may drop
  to 3:1. Non-text parts need ≥ 3:1 against adjacent colours (SC 1.4.11, AA): chip fills and
  borders, icon glyphs, input outlines, focus rings. And don't encode status by colour alone — add
  text or an icon (SC 1.4.1, A). Both ratios matter for status chips and badges.
- Announce async results (toast / `role="status"`, a sufficient technique for SC 4.1.3, AA) so a
  screen-reader user learns the save succeeded without focus moving.
- Avoid `autoFocus` unless there's a strong, deliberate UX reason. This one is a **usability
  judgement, not a WCAG requirement** — no success criterion forbids it — but MDN documents real
  harms: screen readers "teleport" the user to the control with no warning, the page can scroll on
  load, and touch keyboards pop up.

## 12. Tooling Gates

Run before calling work complete, from the app root:

```bash
npm run typecheck     # tsc --noEmit — must be clean
npm run lint          # eslint src (--max-warnings 0)
npm run build         # tsc && vite build — must succeed
# npm test            # once Vitest is set up
```

**Measure the baseline before you trust a gate.** Run each command on an unmodified checkout and
record what it reports — total lint problems and their breakdown by rule, and whether typecheck and
build pass. Without that number you cannot tell your regressions from inherited debt.

If a gate is already red on an unmodified checkout, that pre-existing debt is not yours — but it
means **"the build passes" is not a signal**. In that case verify your change against the files you
touched (`npm run lint <paths>`, `tsc --noEmit` output filtered to them) and by running the app,
and fix the baseline failure separately if it is blocking.

- **Never introduce a new warning.** Leave files you touch at or below their previous count.
- Don't "fix" the baseline wholesale in an unrelated change — that buries the real diff.
- Never add `eslint-disable` without a reason comment; never disable a rule repo-wide to go green.
- `--max-warnings 0` means a non-zero baseline fails the whole command; while that is true, treat
  *your* files as the gate until the debt is burned down.

## 13. AI Agent Rules

1. **Read neighbouring code first** and match existing patterns. Repo convention beats this doc.
2. **Follow the structure**: `pages/<feature>/` + `components/`, hooks for logic, `interfaces/` for
   shared types. Don't invent a parallel tree.
3. **Don't grow a file that already exceeds the size limits** (§2) — extract the part you touch.
4. **No new `any`**, no `@ts-ignore`, no new lint warnings.
5. **Server state via Refine hooks**; URL state via `useSearchParams`. Never mirror server data
   into `useState`.
6. **Every async path gets loading, empty, and error states.** Every mutation handles failure.
7. **Never invent business rules** — credit limits, tax, rounding, status transitions, SLAs. Ask.
8. **Never guess at money or date semantics.** INR formatting via the shared helper; UTC↔local
   explicitly at the boundary.
9. **State assumptions** in your response when proceeding under ambiguity.
10. **Keep the diff focused** — no drive-by refactors or reformatting untouched files.
11. **Run the gates and report real output.** Never claim a typecheck/lint/test you didn't run.
    Say so plainly if one fails.
12. **Flag security-relevant changes** (auth, RBAC display, tokens, `dangerouslySetInnerHTML`,
    URL handling) in your summary.
13. **No commits unless asked.**

## 14. Review Checklist

Flag real defects only; cite `file:line` and the user-visible consequence.

**Architecture** — file over 250 lines or component over ~120? logic that belongs in a hook sitting
in JSX? component defined inside a component? prop-drilling past 2 levels? duplication that should
be extracted, or premature abstraction that shouldn't?

**Naming** — domain-accurate, not `data`/`tmp`/`item`? `handle*`/`on*` split right? booleans
`is/has/can`? units in the name? magic numbers/strings replaced by named constants?

**State** — server data mirrored into `useState`? filters/pagination/tab in component state instead
of the URL? two states that can disagree? `useEffect`+`setState` deriving what render could compute?
context value unmemoized or over-broad?

**Types** — new `any`/`@ts-ignore`? API response typed at the boundary? optional-flag soup where a
discriminated union belongs? `tsc` clean?

**Errors** — error boundary covering this subtree? mutation failure surfaced and input preserved?
empty `catch`? 401/403/422/5xx distinguished? non-idempotent write auto-retried? loading/empty/error
all present? PII or tokens logged?

**Forms** — schema validation? submit disabled while submitting (double-post risk)? server field
errors mapped back? `watch()` on the whole form? dirty-navigation guard? money precision and
timezone handled explicitly? `autoFocus` added without a reason (UX opinion, not a conformance
failure)?

**Testing** — new logic covered incl. error/empty/permission paths? behaviour not implementation?
deterministic (no real clock/network)? regression test for a bug fix?

**Performance** — sequential awaits that could be parallel? `await` in a loop? heavy component not
lazy? hand-written query key missing a parameter, or a filter closed over instead of passed as a
Refine hook prop? unbounded list fetch? `.find()` in a render loop? array index as `key`? `&&` with
a numeric left side? MUI barrel import (dev-time and lint cost, not shipped bytes)?

**Hooks** — conditional hook? dep array incomplete or suppressed? missing cleanup?

**Security** — `dangerouslySetInnerHTML`? client-side RBAC treated as enforcement? secret in
`import.meta.env`? unvalidated URL/redirect? missing `noopener`? raw backend error shown to user?

**A11y** — inputs labelled (SC 1.3.1) and errors described in text, not just a red border
(SC 3.3.1)? icon-only button named (SC 4.1.2)? keyboard reachable (SC 2.1.1), focus visible
(SC 2.4.7) and not hidden behind a sticky header (SC 2.4.11)? non-text contrast ≥ 3:1 on chips,
outlines and focus rings (SC 1.4.11)? status conveyed by colour alone (SC 1.4.1)? dialog labelled
and Escape-dismissible (SC 2.1.2)?

**Gates** — typecheck, lint, build green; no new warnings in touched files; no unexplained
`eslint-disable`.

## 15. References

Sources for every rule above are documented in the upstream repo:
https://github.com/Madheshvivekanandan/ai-engineering-skills (skills/react-best-practices/references/sources.md).
