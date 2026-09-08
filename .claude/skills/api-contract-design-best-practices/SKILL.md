---
name: api-contract-design-best-practices
description: Framework-agnostic standard for designing HTTP/REST API contracts. Load BEFORE adding or changing any HTTP endpoint, request/response schema, error payload, OpenAPI/Swagger document, or outbound webhook — in any language or framework (FastAPI, Express, Spring, Rails, Go, .NET, gateway config). Covers resource modeling, method and status-code semantics, RFC 9457 problem+json errors, idempotency keys, cursor pagination, filtering and sorting, versioning and breaking-change rules, ETags and conditional requests, rate-limit signaling, contract-level authorization, webhooks, OpenAPI 3.1+, and CI contract gates.
---

# API Contract Design Best Practices

Opinionated synthesis of RFC 9110 (HTTP Semantics), RFC 9457 (Problem Details), RFC 5789 and
RFC 6585 (PATCH; additional status codes), RFC 6902 and RFC 7396 (JSON Patch, Merge Patch),
RFC 9745 and RFC 8594 and RFC 8288 (Deprecation, Sunset, Web Linking), the OpenAPI Specification,
Google's API Improvement Proposals, the Zalando and Azure REST guidelines, the OWASP API Security
Top 10 (2023), and Stripe's production idempotency and webhook contracts.
Target: HTTP JSON APIs specified in **OpenAPI 3.1 or later**.
When this document conflicts with an existing in-repo convention, follow the repo and say so.

## 1. Philosophy

- **The contract is the product.** Clients integrate against the documented shape, not your code. Design and review the spec before writing the handler.
- **HTTP already decided most of this.** Methods, status classes, validators, and caching have normative meanings. Reusing them buys you proxies, SDKs, retries, and monitoring for free; inventing your own buys you nothing.
- **Every response field is forever.** Adding is cheap, removing is a migration. Ship the smallest surface that does the job.
- **Machines read errors.** The human-readable string is a courtesy; a stable machine-readable code is the contract.
- **Unbounded is broken.** Any endpoint that can return "all of them" is an outage waiting for the right customer.
- **Deny by default, per object.** Route-level auth plus a caller-supplied id is an enumeration vulnerability, not an authorization model.
- **Be pragmatic about hypermedia, and say so.** Emit absolute URLs where they save the client a round trip — pagination continuation, status monitors, related resources. Do **not** build a full HATEOAS state machine and expect clients to discover it: real clients hardcode paths from your docs, and a `_links` graph nobody follows is pure cost. Discoverability comes from OpenAPI.
- **Boring and consistent beats clever and local.** One casing rule, one error shape, one pagination style, one version mechanism across the whole surface.

## 2. Resource Modeling and URLs

| Rule | Good | Bad |
|---|---|---|
| Plural noun collection + id | `/shipment-orders/{shipment_order_id}` | `/getShipmentOrder?id=7` |
| `kebab-case` path segments matching `^[a-z][a-z0-9-]*$` | `/credit-notes` | `/CreditNotes`, `/credit_notes` |
| No verb in any path segment | `POST /orders` | `POST /orders/createNow` |
| Nest only for genuine containment, 2 levels max | `/orders/{order_id}/line-items` | `/customers/{c}/orders/{o}/line-items/{l}/taxes` |
| Sub-resources are independently addressable | `GET /orders/{id}/line-items/{line_item_id}` | `/orders/{id}/cancellation` as a fake noun |
| Query string filters and pages; it never identifies | `/orders?status=OPEN` | `/orders?action=cancel` |

- **Model resources from the caller's job, not from your tables.** A resource that only makes sense if you know the schema (`/order-header`, `/user-role-map`) is a leaked implementation detail and cannot be evolved independently of the database.
- **Non-CRUD actions get a colon-suffixed custom method** on the resource path: `POST /orders/{order_id}:cancel`. Use it only when Get/List/Create/Update/Delete genuinely cannot express the operation. `GET` is allowed for a custom method only if it is side-effect-free.
- Path segments are case-sensitive. Return `404` on a case mismatch rather than silently normalizing.
- Resource ids are **opaque strings** in the contract even when they are integers underneath. Never expose a sequential id where enumeration is a business risk.

## 3. Methods and Their Guarantees

RFC 9110 §9 fixes these properties. `PATCH` comes from RFC 5789, not RFC 9110.

| Method | Safe | Idempotent | Cacheable | Use for |
|---|---|---|---|---|
| `GET` | yes | yes | yes | Retrieve a representation |
| `HEAD` | yes | yes | yes | Metadata/existence, no body |
| `PUT` | no | **yes** | no | Full replacement of target state |
| `DELETE` | no | **yes** | no | Removal |
| `POST` | **no** | **no** | rarely | Server-defined processing, creation, custom methods |
| `PATCH` | no | **no** by default | no | Partial modification |
| `OPTIONS` | yes | yes | no | Communication options |

Hard rules:

1. **`GET` and `HEAD` must never mutate state** — not a view counter, not a `last_seen_at` touch, not a lazily-created row. Crawlers, prefetchers, link previewers, and retrying proxies fire them repeatedly with no user intent behind it.
2. **`PUT` and `DELETE` must be idempotent.** A repeated `DELETE` of an already-deleted resource returns `204` (or `200`), never `404`: a client retrying after a dropped connection must not be told its own success failed. (RFC 9110 requires the idempotent *effect*; returning `2xx` on the repeat is the house rule that makes it observable.)
3. **`POST` is neither safe nor idempotent.** Any `POST` that creates, charges, ships, or notifies needs an idempotency key (§6).
4. **`PUT` replaces; `PATCH` merges.** Reject a partial body on `PUT` instead of merging it — clients that correctly send a full representation would otherwise silently lose fields.
5. **`PATCH` needs a declared patch format.** RFC 5789 defines no default patch document format, so "PATCH with a JSON body" is not a specification. Accept `application/merge-patch+json` or `application/json-patch+json` and reject bare `application/json` on `PATCH` with `415`.
6. **`PATCH` is idempotent only by construction.** RFC 5789 says PATCH "is neither safe nor idempotent" and recommends a conditional request — a strong ETag in `If-Match` — for patch formats that operate from a known base-point (it explicitly exempts append-style patches); **this document requires `If-Match` on every `PATCH`**, so a retry cannot apply twice. **Prefer absolute values in write bodies**, never `{"increment": 1}`. Where a relative body is genuinely unavoidable (a counter you cannot read-modify-write), an `Idempotency-Key` (§6) is **mandatory in addition to** `If-Match`; document the exception on that operation.

| Patch format | Semantics you must document | Choose when |
|---|---|---|
| `application/merge-patch+json` (RFC 7396) | A `null` member **deletes** the field; arrays are replaced whole, never element-wise; a non-object patch replaces the whole target | **Default.** Simple resources where `null` is not a meaningful stored value |
| `application/json-patch+json` (RFC 6902) | Ops `add`, `remove`, `replace`, `move`, `copy`, `test`; the document applies **atomically** — any failing op means no mutation at all | You need element-level array edits, meaningful explicit `null`s, or test-and-set preconditions |

Merge Patch is unsuitable for any resource where "set this field to null" is a real operation: RFC 7396 gives `null` the reserved meaning of removal, so that intent becomes inexpressible. Document each operation's safe/idempotent/cacheable properties in the spec; do not leave clients to infer them.

## 4. Status Codes

Pick from a short documented set and enumerate every code each operation can emit in OpenAPI. Exotic codes get mistranslated by intermediaries and SDK generators, and undocumented ones become production surprises.

| Code | Means | Contract requirement |
|---|---|---|
| `200 OK` | Success with a body | |
| `201 Created` | Resource created | `Location` header pointing at it (RFC 9110 §9.3.3 says SHOULD for POST-created resources — treat it as MUST); return the created representation |
| `202 Accepted` | Work queued, not done | Return the status-monitor URL in `Operation-Location`, not `Location` (§4.1) |
| `204 No Content` | Success, deliberately no body | Never send a body |
| `304 Not Modified` | Validator matched a conditional `GET`/`HEAD` | Never send a body; send the same `ETag` (and `Cache-Control`) the `200` would have carried |
| `400 Bad Request` | Malformed, unparseable, or unknown parameter | Not a catch-all |
| `401 Unauthorized` | Authentication missing, invalid, or expired | **`WWW-Authenticate` is a MUST** (RFC 9110 §15.5.2). Retryable with new credentials |
| `403 Forbidden` | Authenticated but refused | Not retryable with the same credentials |
| `404 Not Found` | Absent — **or hidden** (§10) | Identical shape for "absent" and "not yours" |
| `405 Method Not Allowed` | Wrong method for this resource | **`Allow` header is a MUST** (RFC 9110 §15.5.6) |
| `409 Conflict` | Conflicts with current resource state | Client re-reads and reconciles |
| `410 Gone` | Existed, permanently removed | Use for endpoints past their sunset date |
| `412 Precondition Failed` | A precondition header evaluated false | Client re-fetches the validator and retries |
| `415 Unsupported Media Type` | Wrong `Content-Type` | Use for `PATCH` without a patch media type |
| `422 Unprocessable Content` | Syntax correct, instructions unprocessable | Field-level validation errors go here, not in `400` |
| `428 Precondition Required` (RFC 6585 §3) | Server requires the request be conditional | Use for an unconditional write to a contested resource |
| `429 Too Many Requests` (RFC 6585 §4) | Throttled | `Retry-After` plus rate-limit fields (§13) |
| `500 Internal Server Error` | Unexpected server fault | Never leak the cause |
| `503 Service Unavailable` | Temporarily down or overloaded | `Retry-After` where known |

- **`400` vs `422` vs `409` vs `412` map to four different client remedies** — fix the syntax, fix the values, re-read state and reconcile, re-fetch the validator and retry. Collapsing them into `400` makes automated retry logic impossible to write.
- **Never return `200` with an error in the body**, and never ship a `{"success": false}` envelope. It defeats every proxy, SDK, retry policy, alert rule, and dashboard that keys on the status class.
- Clients interpret unrecognized codes by their class (`4xx` client fault, `5xx` server fault). Design so that fallback produces sane behavior.
- `428` and `429` are **not** in RFC 9110; they are defined by RFC 6585, which is Standards Track and current.

### 4.1 Long-running operations

Work that cannot finish inside the request returns `202 Accepted` plus a URL to a **status monitor**
resource. Return the monitor URL in a dedicated `Operation-Location` header **and** as a `monitor`
member in the body; do not overload `Location` on a `202`, which clients read as the created
resource. (Azure's guidelines define `Operation-Location` for exactly this purpose.) The monitor's
representation carries `id`, a `status` from a documented closed set (`NOT_STARTED`, `RUNNING`,
`SUCCEEDED`, `FAILED`, `CANCELED`), and on failure an `error` member in the problem+json shape. Retain the monitor for a documented minimum — **24 hours** is a sane floor.
Never return `200` with a fabricated result, and never make the client poll the target resource and
guess whether absence means "not yet" or "failed".

## 5. Errors: One Machine-Readable Shape

Serve **every** `4xx`/`5xx` as `application/problem+json` per **RFC 9457**, which obsoletes RFC 7807.
Cite 9457; when a vendor doc or style guide still shows 7807, check whether its text has been
refreshed before copying it.

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://api.example.com/problems/validation-failed",
  "title": "Request body failed validation",
  "status": 422,
  "detail": "2 fields were rejected.",
  "instance": "/orders/9f2c1b",
  "code": "VALIDATION_FAILED",
  "request_id": "01J8Z3K9QW4",
  "errors": [
    { "pointer": "/items/0/quantity", "code": "OUT_OF_RANGE", "message": "must be between 1 and 500" },
    { "pointer": "/currency", "code": "UNSUPPORTED_VALUE", "message": "must be one of INR, USD, EUR" }
  ]
}
```

| Member | Rule |
|---|---|
| `type` | Stable URI identifying the problem **class**; part of the contract, because clients branch on it. Prefer a dereferenceable URI that documents the problem. Omit it (defaulting to `about:blank`) only when the status code alone carries all the semantics |
| `title` | Constant per `type`, varying only by localization. **Never** put occurrence-specific text here |
| `status` | Exactly the HTTP status of the response. Advisory duplication — the status line stays authoritative |
| `detail` | Occurrence-specific, written for a technical caller trying to fix their request |
| `instance` | URI reference for this occurrence. A per-occurrence URI (correlation id) is preferred; the target resource URI is acceptable only when paired with a correlation-id extension (as in the example above, which carries `request_id`) |
| Extensions | Names of 3+ characters matching `^[A-Za-z][A-Za-z0-9_]*$`. All machine-readable payload lives here |

- **Add a stable `UPPER_SNAKE_CASE` reason code** as an extension alongside `type`, plus an `errors` array of `{pointer, code, message}` for field validation. Without them clients parse English prose and every copy edit becomes a breaking change.
- **Clients must ignore extension members they do not recognize** — RFC 9457 requires it. State it in your docs; it is what makes adding error detail non-breaking.
- **Never** put stack traces, SQL, internal hostnames, upstream vendor error text, internal identifiers, or PII in an error body. Log those and return a correlation id instead.
- Keep a registry of your `type` URIs and reason codes where the team can see it. Changing the `type`, code, or status for the same condition is a **breaking change**.
- If your organization already standardizes a different envelope (for example Azure's `{"error": {"code", "message", "target", "details", "innererror"}}`), use it consistently — but **never mix two error envelopes in one API**.

## 6. Idempotency for Unsafe Operations

`GET`, `HEAD`, `PUT`, and `DELETE` are idempotent by definition. `POST` is not, and `PATCH` is not
unless you construct it that way (§3, rule 6). So: **accept `Idempotency-Key` on every `POST` that
creates, charges, ships, or notifies**, and on the documented exception in §3 rule 6 — a `PATCH` whose
body is unavoidably relative rather than absolute, where the key is required *in addition to*
`If-Match`. Do not require or honor it elsewhere.

| Aspect | Rule |
|---|---|
| Key format | Client-generated, high-entropy (UUIDv4 or equivalent), max **255 characters**, no PII or secrets. Reject malformed keys with `400` |
| Scope | Per endpoint **and** per authenticated principal/tenant. Never a global namespace |
| Storage | Persist the first request's **status code and response body** against the key |
| Replay | Return that stored response byte-for-byte for any later request with the same key — **including `4xx` and `5xx` produced once the operation began executing**. Responses that never reached execution are not stored at all (see "Do not record") |
| Fingerprint | Hash the request body alongside the key. Same key + different body is an error, not a replay: return **`409 Conflict`** with problem `type` `.../idempotency-key-reused` (a house choice; `422` is acceptable if your organization already uses it for this) — never a replayed `2xx` |
| Retention | Document the window after which keys are pruned and reuse executes fresh. **24 hours is the canonical baseline** |
| Do not record | Input-validation failures, and collisions with a concurrently-executing request for the same key. Return a documented **retryable** error for both |
| Concurrency | Lock the key (or use a unique constraint) so two simultaneous retries cannot both execute |

- Caching only successes is the classic mistake. The retry that matters is the one after a `500` or a dropped connection — exactly the double-charge the mechanism exists to prevent.
- Caching a validation failure permanently poisons the key: the client fixes its payload, retries with the same key, and can never succeed.
- Ignoring the body means a client bug that reuses one key across different payloads silently receives the wrong prior result and never learns.
- Azure-aligned estates spell this `Repeatability-Request-ID` / `Repeatability-First-Sent`. Either is legitimate; pick one per organization and use it everywhere.

## 7. Pagination

**Paginate every collection endpoint from its first release.** Adding pagination later is a
backwards-incompatible change — clients that read the whole array silently truncate — so an
unpaginated list is a permanent mistake and a standing resource-exhaustion vector. "The table is
small" is not an exemption; the table is small today.

**Default to cursor (token) pagination.** Offset pagination **skips and duplicates rows** when the
underlying set changes between page fetches, and degrades as the offset grows because the database
walks and discards everything before it. Use offset only for small, static, human-browsed sets that
genuinely need "jump to page N", and document that results may shift.

| Aspect | Rule |
|---|---|
| Parameters | One page-size parameter and one opaque page-token parameter, named identically across the whole API. **Default: `page_size` and `page_token` in the request, `items` and `next` in the response** (AIP-158 naming, adapted to this document's response envelope). `limit`/`cursor` is an acceptable house alternative; pick one per organization and lint it |
| Default size | Documented and finite. **20–50 items** is a sane default. Never "all" |
| Maximum size | Hard cap, enforced. Silently coerce oversize requests **down** to the cap; reject negative or non-numeric values with `400` |
| Cursor | Opaque and URL-safe. Clients must not parse or construct it, and it must **never** carry or widen authorization |
| Short pages | Allowed. A page may contain fewer items than requested |
| End of collection | Signaled **only** by an absent/empty next-page token. Clients must not infer "last page" from a short or empty page |
| Envelope | A JSON object: `{"items": [...], "next": "<token>"}`. **Never** a bare top-level array |
| Last page | **Omit** `next` — do not send `null` |
| Total count | Optional, and documented as an estimate if present. Do not promise consistency with the pages returned |
| Token expiry | Document it (a few days is typical). Return `400` with a specific problem `type` for an expired token |

- Base64-encoding an offset, or a JSON blob naming a table and sort key, is **not** an opaque cursor. Clients will decode and hand-construct it, turning it into an unversioned public interface — and if it encodes tenant or filter scope, into an access-control bypass. Sign it, encrypt it, or store it server-side.
- A top-level array can never gain pagination or metadata without breaking every client.
- Cursor pagination requires a **total order**: pair the sort key with a unique tiebreaker (`created_at`, then `id`).

## 8. Filtering, Sorting, and Field Selection

- **Allowlist** filterable and sortable fields explicitly, with documented operators. Never pass a client expression to the query planner — that is both an injection and a denial-of-service surface.
- **Reject unknown or unsupported query parameters with `400`** plus a problem document. Silently ignoring `?statu=open` returns the entire unfiltered collection and the caller acts on it.
- Fix one sort syntax and use it everywhere: `?sort=created_at,-id` (leading `-` is descending). **Document the default sort** — an undocumented default order is a pagination bug generator.
- **Default filter syntax:** one parameter per field for equality (`?status=OPEN`), a closed set of suffixed operators for ranges (`?created_at_gte=2026-01-01`, `?amount_lt=500`). Adopt an expression language (OData `$filter`, RSQL) only where the organization already standardizes one — it is a parser, an injection surface, and a permanent compatibility commitment.
- **Repeated parameters mean OR within a field; separate parameters mean AND across fields**: `?status=OPEN&status=HELD&currency=INR` is `(OPEN or HELD) and INR`. Pick this or comma-separated values, never both, and state it in the spec.
- Bound anything expandable: cap `?expand=` depth and breadth, and never allow an expansion that triggers unbounded fan-out.

## 9. Representation Conventions

| Concern | Rule |
|---|---|
| Property casing | Pick one (`snake_case` or `camelCase`), state it, lint it. Consistency beats the choice |
| Path segments | `kebab-case` |
| Query and path parameter names | Same casing as body properties (this document's examples use `snake_case`) |
| Enums | `UPPER_SNAKE_CASE` **strings**, never bare integers. Document the closed set; clients must tolerate new members |
| Absent values | **Omit the member.** Do not send explicit `null` for "not set" unless `null` is a distinct, documented state |
| Timestamps | RFC 3339 UTC with an explicit offset: `2026-01-31T09:15:00Z`. Name them `*_at` |
| Durations | Units in the name: `timeout_seconds`, `ttl_ms` |
| Money | Integer minor units plus an ISO 4217 currency code, or a decimal **string**. Never a float |
| Booleans | `is_*` / `has_*`, never tri-state via `null` |
| Identifiers | Strings, and the same id format for the same concept everywhere |
| Links | Absolute URLs, in a named member (`next`, `monitor`, `self`). Emit them where they save a lookup; do not build a link graph clients are required to traverse |
| Link relation types | Registered relations (`next`, `deprecation`, ...) are bare tokens; a relation **you** invent must be an absolute URI you control (RFC 8288 §2.1.2), lowercase, compared as a string |

Wrap every single-resource response in an object rather than returning a bare scalar or array, so the representation can grow. Add fields; never repurpose one.

## 10. Authentication and Authorization at the Contract Level

- **Declare every scheme in `components.securitySchemes`** and attach a `security` requirement to **every** operation — including an explicit `security: []` for deliberately public ones. An operation with no declared security is indistinguishable in review from one that is intentionally open, so gaps survive.
- **TLS only.** Never accept credentials, tokens, or signatures in the query string or path: they land in access logs, proxies, browser history, and `Referer` headers.
- **Authorize the specific object, not just the role.** Derive tenant/owner scope from the authenticated principal, never from a request parameter. Broken Object Level Authorization is OWASP API1:2023 and the most common API vulnerability class — a route guard plus a caller-supplied id is an enumeration tool, and **IDOR is the default bug** unless the query is scoped by principal.
- **Return the same response for "absent" and "not yours".** Where confirming existence is itself a leak, return `404` rather than `403` — a candid `403` on a record the caller cannot see is an existence oracle. Document the choice so clients do not read `404` as "safe to create".
- **Authorize properties, not just endpoints** (OWASP API3:2023). Bind request bodies to explicit per-role request models, never to the persistence model, or a caller sets `role`, `owner_id`, or `balance` through an otherwise-legitimate endpoint. Mark server-owned fields `readOnly` and secrets `writeOnly`.
- **Quota is part of the contract** (OWASP API4:2023): document rate limits, maximum page size, maximum body size, maximum array lengths, and maximum expansion depth. Undocumented limits get discovered in production.
- **Inventory every endpoint and version** (OWASP API9:2023). A forgotten `/v1` still serving unpatched traffic is the breach path.
- Treat responses from third-party APIs as untrusted input and validate them (OWASP API10:2023) — a partner's payload is not safer than a user's.

## 11. Versioning and Backward Compatibility

**Default to not versioning.** Extend compatibly. Every live major version multiplies the
maintenance, test, and security-patch surface, and the large majority of changes can be made
compatibly if the surface was designed for extension.

When you genuinely must version, **pick exactly one mechanism for the whole API** and enforce it in
the spec. Recommended default: **a single major version segment in the path (`/v1/...`), applied
API-wide, bumped almost never.** It is visible in logs, routing, and cache keys, needs no header
negotiation, and is what the overwhelming majority of public APIs ship.

- **Never version per endpoint** (`/v1/orders` beside `/v3/orders`) and never mix mechanisms — caching, routing, and client configuration all become undecidable.
- Two alternatives are legitimate house styles, and if your organization already standardizes one, follow it: **media-type versioning** via `Accept` (Zalando's rule 114 requires it and rule 115 forbids URL versioning), and **a required dated version parameter** such as `api-version=YYYY-MM-DD` (the Azure guidelines require this and forbid path versioning). The dated parameter is the better choice when you ship frequent dated behavior changes to a large external client base and want every client pinned.
- With **header or query-parameter** versioning, **reject a missing or unknown version with `400`** and a specific problem `type`; never silently default it — defaulting an absent version pins clients to whatever "current" happens to mean the day they integrate. With **path** versioning an unversioned URL simply does not exist: return `404` (§2), and do not add a catch-all route that would mask genuine `404`s. Either way, never infer a version for the client.

### Breaking vs non-breaking

Forbid all of these within a major version. Each breaks working client code even when the wire format still parses — which is exactly why they feel small.

| Breaking change | Why it surprises people |
|---|---|
| Removing or renaming a field, endpoint, or enum member | Obvious, but "nobody uses it" is unverifiable without per-caller telemetry |
| **Adding a required request field** | Every existing request instantly becomes invalid |
| **Removing a response field** | Clients dereference it unconditionally |
| **Narrowing a type** (`string` to `integer`, wider to narrower numeric) | Wire-compatible in some cases, still a compile or parse break |
| **Tightening validation** (new `maxLength`, stricter regex, new required combination) | Payloads that worked yesterday start failing |
| Making an always-populated response field sometimes absent or `null` | Its presence was treated as guaranteed |
| Changing a default value, or whether defaults are serialized | Behavior changes for a byte-identical request |
| Changing an id or resource-name format — looser **or** stricter | Client-side validation and storage break |
| Changing the `type`, reason code, or status for the same error condition | Error-handling branches stop matching |
| Changing observable behavior or semantics for an unchanged request | The worst kind: invisible in the schema diff |
| Adding pagination to an existing collection | Clients reading the whole array silently truncate |

Non-breaking, but **only** if the tolerant-reader contract below is published: adding an optional
request field with a safe default; adding a response field; adding a new endpoint, method, or
optional query parameter; adding a new error `type` for a genuinely new condition under an existing
status code. Adding a member to a **response** enum is the borderline case — clients that switch
exhaustively still break, so announce it rather than slipping it in.

**Publish the tolerant-reader contract explicitly**, because compatible extension is only safe if
clients were told to tolerate it: clients MUST ignore unknown response fields and unknown enum
members, MUST NOT depend on property order, and MUST NOT depend on a field's absence.

### Deprecation and sunset

| Signal | Form | Note |
|---|---|---|
| `Deprecation` (RFC 9745, Standards Track, March 2025) | Structured Field Item carrying a date: `Deprecation: @1688169599` | May be past or future. Changes no behavior on its own |
| `Sunset` (RFC 8594, Informational, May 2019) | HTTP-date: `Sunset: Sun, 31 Dec 2028 23:59:59 GMT` | RFC 9745 requires it be **no earlier** than the `Deprecation` date. Clients SHOULD treat it as a hint |
| Migration docs | `deprecation` link relation in a `Link` header (RFC 8288) | Registered by RFC 9745 §6.2, so use the bare token: `Link: <https://api.example.com/deprecation-policy>; rel="deprecation"` — not an absolute-URI relation type |

**Instrument the deprecated operation per caller.** Without usage telemetry the sunset date is a
guess and the removal is an outage. After sunset, return `410 Gone`, not `404`.

## 12. Conditional Requests, ETags, and Concurrency

Per RFC 9110 §13:

- **Return an `ETag` on every single-resource `GET`** and support `If-None-Match`, so an unchanged resource answers `304 Not Modified` with no body. Without a validator every poll transfers the whole representation.
- **Require `If-Match` on every `PATCH` (§3 rule 6), and on `PUT` and `DELETE` for any resource with concurrent writers**, and return `412 Precondition Failed` on mismatch. This is the only interoperable defense against the lost-update (mid-air collision) problem; without it the last writer silently overwrites changes it never saw. **Default: `428 Precondition Required`** for an unconditional write — that is the condition RFC 6585 §3 defines it for, whereas `412` properly means a precondition was present and evaluated false. `412` is an acceptable house alternative if your clients already special-case it; document whichever you pick, and never return `200`.
- Use **strong** ETags by default; `W/` weak validators only where you deliberately mean semantic equivalence (ignoring a formatting-only difference).
- **Evaluate preconditions in RFC 9110's order:** `If-Match`, then `If-Unmodified-Since`, then `If-None-Match`, then `If-Modified-Since`. Reordering makes a request's outcome depend on which headers a client happened to combine.
- **Derive the ETag deterministically from stored state** — a version column, or a content hash over a canonically-ordered serialization. Never from a request-time timestamp, a random id, an object address, or a hash over an unordered map: a non-deterministic ETag makes every `If-None-Match` miss and every `If-Match` fail, converting an optimization into a permanent `412` generator.
- Document cacheability per operation and set `Cache-Control` deliberately. Anything user-scoped is `private`.

## 13. Rate-Limit Signaling

- On throttling, return **`429` with `Retry-After`**. RFC 6585 makes `Retry-After` a MAY; treat it as mandatory, because a bare `429` gives clients nothing to compute backoff from and they will hammer you.
- Advertise quota with the IETF `RateLimit-Policy` and `RateLimit` structured fields:

```http
RateLimit-Policy: "burst";q=100;w=60,"daily";q=1000;w=86400
RateLimit: "burst";r=50;t=30
```

  `RateLimit-Policy` carries `q` (quota, required) plus optional `qu`, `w`, `pk`; `RateLimit` carries
  `r` (remaining, required) plus optional `t`, `pk`.
- **These fields are not an RFC.** They are an active IETF Internet-Draft (`draft-ietf-httpapi-ratelimit-headers`), so names and parameters can still change. Track the draft, and say "draft" in your documentation.
- `Retry-After` should not point earlier than the end of the effective window, and when both `Retry-After` and `RateLimit` are present **`Retry-After` takes precedence**. An inconsistent pair produces premature retries and a retry storm.
- `X-RateLimit-Limit` / `-Remaining` / `-Reset` are pre-standard de facto conventions, which the draft documents only in a non-normative appendix (marked for removal before RFC publication) while cataloguing their interoperability problems — the same field name variously carries seconds, milliseconds, a UNIX timestamp, or an HTTP-date. Keeping them for compatibility is fine; **document them as legacy aliases** rather than describing them as standardized.
- A rate-limit response is still an error: return problem+json with a stable reason code, and document which limits apply per endpoint, principal, and tenant.

## 14. Webhooks (Outbound Events)

| Concern | Rule |
|---|---|
| Transport | HTTPS only, TLS 1.2+. Reject plaintext receiver URLs at registration time |
| Signature | HMAC-SHA256 over `timestamp + "." + raw_body`, in a dedicated header carrying the timestamp and a scheme identifier |
| Verification | Constant-time comparison over the **unparsed raw bytes**. Ignore unknown or superseded schemes so a downgrade attack cannot pick a weaker one |
| Replay window | Reject timestamps outside a documented tolerance. **5 minutes** is the canonical default; a tolerance of 0 must not be used |
| Secret rotation | Overlap window with both secrets valid, one signature per active secret. Document the window (24 hours is a sane default) |
| Delivery guarantee | **At-least-once and unordered.** State this in the docs — a `deleted` event can arrive before the `created` |
| Consumer contract | Verify the signature, then durably persist or enqueue the raw event, then return `2xx` — before any business logic. Never return `2xx` before the event is durably recorded, and never run business logic before responding. Deduplicate on event `id` (fall back to object id + event type) |
| Retries | Exponential backoff over a documented window (hours to a few days). `3xx` redirects count as delivery **failures** |
| Envelope | Stable `id`, `type`, `created`, an explicit payload version, and a reference to the affected resource |
| Immutability | An emitted event's shape is pinned to the version in effect when it was created; events are never rewritten |
| Subscription | Subscribers select specific event types. Never force a firehose |
| CSRF | Exempt receiver routes from CSRF token middleware, or legitimate machine-to-machine POSTs are silently rejected |
| IP allowlisting | A useful second control, **never** a substitute for signature verification — IPs are shared and rotate |

Failure modes worth naming, because they are silent: doing the real work before responding (the
delivery times out, gets retried, and the duplicate work compounds); verifying the signature against
a framework-parsed or re-serialized body (always fails); and comparing signatures with `==` (leaks
the signature by timing). Where a number above comes from a specific provider's production defaults,
treat it as a sane starting value, not a standard.

## 15. Specifying the Contract: OpenAPI

- **Write the OpenAPI document first and review it as the contract.** A spec generated from code after the fact documents whatever the code happens to do, accidents included, and cannot be used to review a design before it ships.
- One self-contained document per API, carrying `info.title`, `info.version`, `contact`, and an owning-team/audience marker. An unowned spec is an inventory failure waiting to happen.
- **Target OpenAPI 3.1 or later** (v3.2.0 is the current release, published 19 September 2025), because from 3.1 the Schema Object is real JSON Schema 2020-12 rather than Draft 05:

| Do | Don't |
|---|---|
| `type: ["string", "null"]` | `nullable: true` — **removed** in 3.1, not deprecated |
| `examples: [...]` (the JSON Schema array) | the singular schema-level `example` |
| Set `jsonSchemaDialect` if you deviate from the default | assume 3.0-era keywords are still honored |

- Describe outbound webhooks in the top-level **`webhooks`** field (present in 3.1.0, absent from 3.0) with the same schema rigor as inbound operations. Webhooks documented only in prose are untestable and drift immediately.
- Reuse via `components` — schemas, parameters, responses, `securitySchemes`. Duplicated inline schemas guarantee a later fix lands in some copies and not others.
- Every operation declares: `operationId`, at least one tag, a `security` requirement, every response code it can emit, and a `Location` header on `201` responses (a `202` declares `Operation-Location` instead, §4.1).
- Separate request and response schemas per operation (`OrderCreate`, `OrderPatch`, `Order`). Never publish one model used in both directions — that is how `readOnly` fields become writable.

## 16. Contract Gates in CI

Make the rules above machine-enforced; anything a reviewer must remember will eventually be
forgotten. Treat these as starting points — confirm flag names against the versions you install.
**The lint, diff, and grep lines are gates: a non-zero exit fails the build. The `changelog` line is
informational and is explicitly forced to exit 0**, because `oasdiff changelog` does exit non-zero
when a spec fails to load or parse, and that failure would otherwise be misread as a breaking
change. The greps are negated because a match *is* the violation.

```bash
# Lint the spec: built-in OpenAPI ruleset plus a project ruleset
spectral lint openapi.yaml --ruleset .spectral.yaml --fail-severity=warn

# Fail the PR on any change that breaks existing clients; publish a human changelog too
# --fail-on ERR is required; without it oasdiff prints findings and exits 0
oasdiff breaking --fail-on ERR released/openapi.yaml openapi.yaml
oasdiff changelog released/openapi.yaml openapi.yaml || true   # informational; exits 0 unless a spec fails to load

# Cheap greps that catch the recurring mistakes.
# 'test -f' first: '! grep' turns grep's exit-2 (missing/unreadable file) into a passing gate
test -f openapi.yaml
! grep -n 'nullable:' openapi.yaml            # removed in OpenAPI 3.1 - use type: ["x","null"]
! grep -nE '(^|/)(get|create|update|delete|list|fetch|remove)([A-Z][A-Za-z0-9]*)?([/:"]|$)' openapi.yaml
# ^ verbs as a whole path segment (/orders/create, /users/delete) or camelCase-prefixed
#   (/getShipmentOrder, /orders/createNow). Anchoring on the segment boundary leaves genuine
#   hyphenated nouns (/delete-requests, /update-schedules) alone, so no allowlist is needed;
#   only a legitimate segment like /create-only-mode would - pipe it through `grep -v`.
```

Project Spectral rules worth writing, each failing the build: every `4xx`/`5xx` response declares
`content['application/problem+json']`; every declared `401` declares a `WWW-Authenticate` header;
every operation has a `security` field (explicit `security: []` for public ones); every operation
returning a collection declares the pagination parameters under their house names (`page_size` and
`page_token` by default, §7); every creating `POST` declares a `Location` header on its `201`; every
operation has an `operationId` and at least one tag.

Contract tests to run against a live instance:

| Probe | Expected |
|---|---|
| Same `POST` body twice with one `Idempotency-Key` | Byte-identical status and body |
| Same key, different body | `409` (or your documented `422`) problem+json, never a replayed `201` |
| `DELETE` twice | Same `2xx` both times, never `404` on the second |
| `GET`, then re-`GET` with `If-None-Match` | `304` |
| `PUT` with a stale `If-Match` | `412` |
| `PATCH` with no `If-Match` (any resource), or `PUT`/`DELETE` with no `If-Match` on a contested resource | `428` (or your documented `412`), never `200` |
| `PATCH` with `Content-Type: application/json` | `415` |
| Wrong method on a resource | `405` **with** `Allow` |
| Unauthenticated request to a protected operation | `401` **with** `WWW-Authenticate` |
| Request another tenant's object id | The documented code, identical to "absent" |
| Request maximum page size + 1 | Coerced down to the documented cap |
| Follow page tokens to exhaustion | Terminates on an absent token, not on a short page |
| Unknown query parameter | `400`, not a silently unfiltered collection |
| Exceed the rate limit | `429` with `Retry-After` and the rate-limit fields |

**Record your project's own numbers** — default and maximum page sizes, idempotency retention,
webhook retry window, rate limits per tier — in the spec and in these tests after you first run this
gate. Do not carry another project's numbers over as if they were measured here.

## 17. AI Agent Rules

When designing or changing an HTTP API, the agent **must**:

1. **Read the existing spec and neighbouring endpoints first.** Match the repo's casing, error envelope, pagination style, and version mechanism. The repo's convention beats this document.
2. **Update the OpenAPI document in the same change** as the handler. A change to a public surface with no spec change is incomplete.
3. **Never write a mutating `GET` or `HEAD`**, and never make `PUT` or `DELETE` non-idempotent.
4. **Add an idempotency path** to any new `POST` that creates, charges, ships, or notifies — including the body fingerprint and the retention window — or state explicitly why it is unnecessary. Write `PATCH` bodies as absolute values; if a relative body is unavoidable, it needs an `Idempotency-Key` **on top of** `If-Match` (§3 rule 6), and say so.
5. **Paginate every new collection endpoint** with a documented default and an enforced maximum page size. Never ship an unbounded list, however small the table is today.
6. **Return an `ETag` on every single-resource `GET` and require `If-Match` on writes per §12**, answering `412` on mismatch and `428` on an unconditional write to a contested resource. Derive the ETag from stored state, never from request time or a random value.
7. **Return `application/problem+json` with a stable machine-readable code** on every error path, and never include stack traces, SQL, upstream error text, internal ids, or PII.
8. **Scope every query by the authenticated principal**, never by an id taken from the path or body, and return the same response for "absent" and "not yours".
9. **Bind request bodies to explicit request schemas**, never to persistence models, and mark server-owned fields `readOnly`.
10. **Classify every contract change as breaking or non-breaking against §11 and say which** in the response. If it is breaking, stop and propose the compatible alternative or the version and deprecation path — do not ship it silently.
11. **Never invent business semantics.** If status transitions, currency rounding, retry windows, quota tiers, or which fields are required are ambiguous, **ask**; do not guess a default.
12. **State every assumption explicitly** in the response when proceeding under uncertainty.
13. **Cite the normative source when it decides a design question** (RFC 9110 for methods and status codes, RFC 5789 for `PATCH`, RFC 6585 for `428`/`429`, RFC 9457 for errors), and never assert a version number, header name, limit, or protocol detail you have not verified. `RateLimit`/`RateLimit-Policy` are still an Internet-Draft — say so whenever you recommend them.
14. **Run the contract gates** (spec lint, breaking-change diff, contract tests) and report the real output. Never claim verification you did not perform.
15. **Flag anything security-relevant** you touch — auth, tenancy scoping, id handling, outbound URLs, webhook verification, quota — in the summary.

## 18. Review Checklist

For an AI reviewer. Flag only real defects; cite `file:line` and state the failure scenario.

**Resource design** — plural noun collections, `kebab-case` segments, no verbs in paths? Nesting no deeper than genuine containment? Non-CRUD actions as custom methods rather than fake sub-resources? Any resource that only makes sense if you know the database schema?

**Methods** — any `GET`/`HEAD` that writes (counter, timestamp, lazy row creation)? `PUT` merging a partial body? `DELETE` returning `404` on the second call? `PATCH` accepting bare `application/json`? Merge Patch chosen where `null` is a real stored value? JSON Patch applied non-atomically? Relative `PATCH` bodies (`increment`) with no conditional request?

**Status codes** — `201` without `Location`? `405` without `Allow`? `401` without `WWW-Authenticate`? `400` as a catch-all where `422`, `409`, or `412` is correct? `200` with an error body, or a `success: false` envelope? `204` with a body? Every emitted code enumerated in the spec?

**Errors** — problem+json on every `4xx`/`5xx`? Stable `type` plus a machine-readable reason code? `title` constant per `type`, occurrence text in `detail`? `status` matching the status line? Any stack trace, SQL, internal hostname, upstream text, internal id, or PII? Two error envelopes mixed in one API?

**Idempotency** — key accepted on every creating or charging `POST`? Failures replayed too, not only successes? Body fingerprinted? Validation failures and concurrent-key collisions deliberately unrecorded and documented as retryable? Retention window documented? Key scoped per principal, not global? Concurrent retries serialized?

**Pagination** — every collection paginated? Maximum page size enforced, oversize coerced down, negatives rejected? Cursor genuinely opaque, carrying no scope or authorization? Termination on an absent token rather than a short page? Object envelope rather than a top-level array? `next` omitted rather than `null`? A stable total order behind the cursor?

**Filtering and sorting** — fields allowlisted with documented operators? Multi-value and cross-field combination semantics documented? Unknown parameters rejected rather than ignored? Default sort documented? Expansion depth and breadth bounded?

**Representation** — one casing convention throughout? Enums as `UPPER_SNAKE_CASE` strings? Explicit `null` used to mean "absent"? Money as a float? Timestamps timezone-explicit UTC? Units in duration names?

**Auth** — `security` declared on every operation, `security: []` on intentionally public ones? Object-level authorization on every caller-supplied id, scoped from the principal? Same response for absent and forbidden? Property-level allowlists and `readOnly` on server-owned fields? Credentials or tokens anywhere in a URL? Limits and quotas documented?

**Versioning** — anything from §11's breaking table shipped inside a major version: newly required request field, removed response field, an always-present field now sometimes omitted, narrowed type, tightened validation, changed default, changed error code? Version mechanism consistent with the rest of the API? Missing or unknown version rejected rather than defaulted (`400` under header/query versioning, `404` under path versioning)? Tolerant-reader contract published? `Deprecation` + `Sunset` (never earlier than `Deprecation`) + migration link + per-caller telemetry on anything being retired?

**Conditional requests** — `ETag` on single-resource `GET`s? `If-None-Match` honored with `304`? `If-Match` required on every `PATCH`, and on `PUT`/`DELETE` to concurrently-edited resources, `412` on mismatch? ETag derived deterministically from stored state? Preconditions evaluated in the specified order?

**Rate limits** — `429` carrying `Retry-After` and the rate-limit fields? `Retry-After` consistent with the window end? `X-RateLimit-*` documented as legacy rather than presented as standard?

**Webhooks** — HTTPS/TLS enforced at registration? HMAC over timestamp plus **raw** body, constant-time comparison, superseded schemes rejected? Timestamp tolerance documented and non-zero? Secret rotation with overlap? Event durably recorded **before** the `2xx`, and no business logic before responding? Dedupe on event id? Retries with backoff, `3xx` treated as failure? Envelope with id, type, created, payload version? CSRF exemption on the receiver route?

**Spec quality** — spec updated with the code? `nullable` anywhere? Singular `example` where `examples` belongs? One model shared across request and response? Shared schemas duplicated inline? `operationId` and tags present? Webhooks in the `webhooks` field rather than only in prose?

**Gates** — spec lint clean? Breaking-change diff clean or explicitly approved? Contract tests present for idempotency replay, pagination caps, conditional requests, unknown parameters, and repeated `DELETE`?

## References

Sources for every rule above are documented in the upstream repo:
https://github.com/Madheshvivekanandan/ai-engineering-skills (skills/api-contract-design-best-practices/references/sources.md).
