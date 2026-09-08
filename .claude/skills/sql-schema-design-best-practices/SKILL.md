---
name: sql-schema-design-best-practices
description: Stack-agnostic standard for designing and evolving relational database schemas. Load BEFORE writing or reviewing DDL, migration files, or index definitions (CREATE TABLE / ALTER TABLE / CREATE INDEX; Flyway, Liquibase, Alembic, Prisma, Knex, golang-migrate, Rails or Django migrations), and when picking types for money or timestamps, diagnosing a slow query with EXPLAIN, planning a zero-downtime schema change or a backfill, or designing multi-tenant row isolation. ORM-agnostic — applies equally to raw SQL and to Node, Go, Java, .NET, or Python backends.
---

# SQL Schema Design Best Practices

Opinionated synthesis of the current PostgreSQL documentation (the pages cited below self-reported PostgreSQL 18), the PostgreSQL wiki's "Don't Do This", Markus Winand's indexing material (*SQL Performance Explained*, freely readable as use-the-index-luke.com), Sadalage and Fowler's *Evolutionary Database Design* plus Danilo Sato's ParallelChange, Bill Karwin's *SQL Antipatterns* vocabulary, and Simon Holywell's SQL Style Guide.

**Default engine: PostgreSQL.** The design rules here — normalization, key choice, which constraint to reach for, composite index column order, migration sequencing, naming — port to any relational engine. The *spellings* and a handful of *behaviours* do not; section 2 names the ones that actually differ. This document is deliberately ORM-agnostic: it constrains the schema and the migration, not your data-access library. When this document conflicts with an existing in-repo convention, follow the repo and say so.

## 1. Philosophy

- **The schema is the contract.** Application code gets rewritten every few years; the data outlives it.
- **The application is not the only writer.** A backfill script, a second service, an admin session, a replayed message, a restore. Only a database constraint is a guarantee; application validation is a convenience.
- **Correctness before performance.** Normalize first. Denormalize with a measurement and a written reason, never by default.
- **Every index is a permanent tax on every write.** Add one for a named query, not for a feeling.
- **Nulls are a design decision**, not a default. Most columns should be `NOT NULL`.
- **Migrations are code**: versioned, reviewed, rollback-tested, in the same commit as the code that needs them. No manual DDL in production, ever.
- **A schema change to a live system is a three-release conversation**, not one `ALTER TABLE`.
- **Name it once, name it forever.** A rename is the most expensive cheap-looking change in a database.
- **Boring wins.** A typed column beats a clever document; a foreign key beats a convention.

## 2. Dialect Scope

Carry over the *intent* of PostgreSQL syntax (`timestamptz` = timezone-aware instant, `numeric` = exact decimal, `text` = unbounded string, `jsonb` = indexable document, `EXCLUDE USING gist` = race-free overlap check, `GENERATED ... AS IDENTITY` = server-generated key) and look up the target engine's equivalent. These behaviours differ more deeply than spelling — verify against your engine's own docs before assuming:

| Behaviour | PostgreSQL (the default assumed here) | Elsewhere |
|---|---|---|
| Nulls in `UNIQUE` | Nulls are distinct, so a nullable unique column accepts unlimited null rows; a `NULLS NOT DISTINCT` clause opts out | The PostgreSQL docs state the SQL standard leaves this implementation-defined. Check your engine; do not assume — and the `NULLS NOT DISTINCT` opt-out itself only exists on PostgreSQL 15 and later (it is documented on the PostgreSQL 15 constraints page and absent from the PostgreSQL 14 one). |
| Transactional DDL | DDL runs in a transaction and rolls back cleanly | MySQL largely lacks it — a failed migration can leave a half-applied schema. There: one statement per migration file, each re-runnable. |
| `ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT` | The standard way to add a constraint to a big table online | PostgreSQL-specific syntax. Other engines need their own online-DDL path or an external tool. |
| `CREATE INDEX CONCURRENTLY` | Builds without blocking writes | PostgreSQL-specific spelling; most engines have some online index build, with different caveats. |
| Expression indexes | Index the expression directly | MySQL supports functional key parts directly since 8.0.13 (`CREATE INDEX idx ON t ((lower(email)))` — note the required extra parentheses); SQL Server still needs a computed column that you then index. Winand's material predates the MySQL feature, so verify against your engine's current `CREATE INDEX` reference. |
| Clustered primary key | Heap table; the PK is just another unique index | InnoDB clusters the table on the PK, so a wide or random PK costs materially more. Re-examine the surrogate-key and UUID advice there. |
| Row-level security | Built-in policies (section 12) | Not universal. Where absent, isolation must be enforced in one shared query layer. |

Where a rule below is PostgreSQL-specific, it is marked. Everything unmarked is a design rule that holds anywhere.

## 3. Logical Modeling

Model to third normal form before writing DDL: one table per entity, one atomic value per column, every non-key column dependent on the whole key and nothing but the key.

| Rule | Good | Bad |
|---|---|---|
| No list inside a column | `order_items` child table with an `order_id` FK | `orders.item_ids = '3,17,42'`; a `jsonb` array of foreign keys |
| No numbered repeating columns | `contact_phones(contact_id, kind, number)` | `phone_1`, `phone_2`, `phone_3`; `tag1..tag5` |
| No attribute bag for a known shape | Real typed columns | `attributes(entity_id, attr_name, value text)` |
| No untyped polymorphic parent | One nullable FK per possible parent plus a `CHECK` that exactly one is non-null, or one intersection table per parent type | `parent_id bigint` + `parent_type text` (cannot carry an FK) |
| No hand-maintained derived value | Generated column, a view, or compute on read | `line_total` kept in sync by application code |
| No free-text state machine | Lookup table + FK, or a `CHECK` against an explicit list | `status text` holding whatever the last developer typed |

- **Denormalize only after a measured query problem.** Record three things in the migration message: the query, the measurement, and which invariant application code now owns. A duplicated fact with no mechanism keeping it consistent is a scheduled data-integrity bug.
- **Hierarchies: choose the traversal structure deliberately**, up front, not after the first "all descendants" ticket. A plain adjacency list is fine when you read one level at a time or can use a recursive CTE. For arbitrary-depth subtree reads, moves, or deletes: **default to a closure table** when subtrees are both read *and* moved, because a move touches only closure rows; use a **materialized path** when subtree reads dominate and moves are rare, accepting that one move rewrites every descendant's path; use **`ltree`** only on PostgreSQL, where the extension is permitted on your platform and you want path operators and GiST indexing for free.
- **A lookup table beats an enum type** when values need labels, ordering, or soft retirement, because adding a value is then a row rather than a schema change.
- **Credentials are never recoverable.** Store salted password hashes only; no reversible storage, no "email me my password" path. Otherwise a backup, a log line, or one injection equals full account compromise.

## 4. Keys and Identity

- **Every table gets a primary key** — including join tables and event logs. Without one, duplicates are undetectable, individual rows cannot be addressed by `UPDATE`/`DELETE`, and logical replication and most tooling break.
- **Surrogate vs natural:** use the natural key when it is genuinely immutable and narrow (ISO country code, currency code). Use a surrogate when the natural key is wide, mutable, or controlled by someone else (email, phone, external account number).
- **Adding a surrogate does not retire the natural key.** Keep a `UNIQUE` constraint on it, or you have licensed logical duplicates behind distinct ids.
- **Auto-generated integer keys:** `bigint GENERATED ALWAYS AS IDENTITY`. Use `BY DEFAULT` only where the application must supply explicit ids (imports, replication). Do not use `serial` — the PostgreSQL wiki recommends identity columns on PostgreSQL 10+ and calls out serial's awkward schema, dependency, and permission behaviour. `bigint` from the start avoids the emergency migration at 2147483647.
- **Identity is not a uniqueness guarantee.** The docs say so explicitly: sequences can be reset and values can be supplied manually. Always back the column with `PRIMARY KEY` or `UNIQUE`.
- **If keys must be opaque or client-generated, use time-ordered UUIDv7** (`uuidv7()`), not random UUIDv4 (`gen_random_uuid()` / `uuidv4()`), for anything that will be a primary key or a heavily-inserted index key. RFC 9562 states that time-ordered monotonic UUIDs "benefit from greater database-index locality because the new values are near each other in the index", and that the difference versus random insertion "can be one order of magnitude or more". RFC 9562 also recommends UUIDv7 over v1/v6. **Availability matters here:** server-side `uuidv7()` is a recent PostgreSQL addition, and `gen_random_uuid()` is the only UUID generator present in older majors. Check `\df uuidv7` on the target server; where it is absent, generate UUIDv7 in the application (every major language has a library) and keep the column type `uuid` with no server default. Do not swap in `gen_random_uuid()` as a substitute — that is UUIDv4, which is exactly what this rule rejects for index keys.
- **Never renumber or reuse surrogate key values** to close gaps. Gaps are meaningless; renumbering silently repoints every external reference, cached id, and exported report at the wrong row.

## 5. Constraints Are the Guarantee

Every rule that must *always* hold is a database constraint, not only an application check. Pick the weakest constraint that actually expresses the rule:

| Constraint | Use it for | The trap |
|---|---|---|
| `NOT NULL` | Anything without a documented meaning for "absent" | The PostgreSQL docs: "in most database designs the majority of columns should be marked not null". Nullable-by-default pushes three-valued-logic bugs into every query and every caller. |
| `CHECK` | Single-row invariants (`amount > 0`, `ends_at > starts_at`, an allowed value list) | A `CHECK` passes when the expression is **true or null**, so `CHECK (price > 0)` permits a null price. Write `CHECK (price IS NULL OR price > 0)`, or make the column `NOT NULL`. |
| `UNIQUE` | Business keys | Nulls are distinct by default (see section 2). Make the columns `NOT NULL` — the portable fix, and the default. `NULLS NOT DISTINCT` is the alternative, but it is a PostgreSQL 15+ clause (absent from the PostgreSQL 14 documentation), so confirm it parses on the target major before relying on it; on older majors use `NOT NULL`, or a unique expression index over `coalesce(col, <sentinel>)`. |
| Unique partial index | Uniqueness over a *subset* of rows: `CREATE UNIQUE INDEX subscriptions_user_id_active_key ON subscriptions (user_id) WHERE status = 'active'` | A plain `UNIQUE` constraint cannot express a predicate, and a read-then-write check in application code races under concurrency. |
| `FOREIGN KEY` | Every reference between tables | See the three rules below. |
| `EXCLUDE USING gist` | "Must not overlap": bookings, price validity windows, employment spans | The only race-free way to forbid overlapping intervals; an application-side overlap check is always a lost race. Requires `CREATE EXTENSION btree_gist` whenever the constraint also equality-matches a scalar column — the usual case (`room_id WITH =`, `product_id WITH =`, `employee_id WITH =`) — because core PostgreSQL ships no GiST operator class for `integer`/`bigint`/`uuid`. Working shape: `CREATE EXTENSION IF NOT EXISTS btree_gist;` then `ALTER TABLE bookings ADD CONSTRAINT bookings_room_id_during_excl EXCLUDE USING gist (room_id WITH =, during WITH &&);` where `during` is a `tstzrange`. Confirm the extension is permitted on your managed platform before designing around it. |

- **Choose the referential action explicitly.** Silence means `NO ACTION`, which is deferrable and differs subtly from `RESTRICT`, which is not deferrable and blocks even an update whose end state would be valid. `CASCADE` only when the child is genuinely a component of the parent (order lines, not invoices); `SET NULL`/`SET DEFAULT` only for optional references.
- **Index the referencing (child) columns of every foreign key.** PostgreSQL does not create that index for you; without it, a parent `DELETE` or key `UPDATE` requires a scan of the whole child table for each affected row.
- **Composite foreign keys:** make all referencing columns `NOT NULL`, or declare `MATCH FULL`. By default a child row escapes the constraint entirely if *any* referencing column is null.
- **Never write a `CHECK` that reads other rows or other tables** (directly, or through a function that queries). The docs state PostgreSQL cannot guarantee consistency for such constraints and that they break dump/restore, because `CHECK` expressions are assumed immutable and are evaluated only for the row being modified. Use `UNIQUE`, `EXCLUDE`, or `FOREIGN KEY` for cross-row rules.

## 6. Data Types

| Need | Use | Never | Why |
|---|---|---|---|
| Money / any exact quantity | `numeric(p,s)` with an explicit scale, or `bigint` minor units **plus a currency column** | `real`, `double precision`, PostgreSQL's `money` | The docs recommend `numeric` "for storing monetary amounts and other quantities where exactness is required", and warn that comparing floats for equality "might not always work as expected". The wiki rejects `money`: it cannot hold sub-cent fractions, and changing `lc_monetary` changes what stored values mean. |
| A point in time | `timestamptz` | `timestamp without time zone`, even "because we store UTC" | `timestamptz` converts input to UTC on the way in; `timestamp` silently *discards* any zone indication in the input and gives wrong answers for arithmetic across DST and locations. |
| A calendar date | `date` | a timestamp | Date of birth and invoice date have no instant; storing one forces an arbitrary zone and makes equality zone-dependent. |
| A duration | `interval` | a bare integer of unspecified unit | `interval` stores months, days and microseconds separately precisely because months and DST days are not fixed multiples of seconds. If an integer is unavoidable, put the unit in the name (`timeout_seconds`). |
| Time of day | `time` (plus a separate date/zone if needed) | `time with time zone`, `CURRENT_TIME` | The docs recommend against `time with time zone` outright. |
| Sub-second truncation | `date_trunc('second', ts)` | `timestamptz(0)` | The precision modifier **rounds** rather than truncates, so it can store a value in the future (wiki). |
| Character data | `text` | `char(n)`; `varchar(n)` as a reflex | `char(n)` space-pads, producing surprising comparisons and wasted storage. A guessed `varchar` limit becomes a production error later. Apply a limit only as a real business rule, and prefer `CHECK (length(col) <= n)` because it can be relaxed online with `ADD CONSTRAINT ... NOT VALID` then `VALIDATE CONSTRAINT` (section 9), whereas *narrowing* a `varchar(n)` rewrites the table — widening one does not. |
| Case-insensitive text | `text` plus `CREATE UNIQUE INDEX users_email_lower_key ON users (lower(email))`, and query with `lower(email) = lower($1)` | a plain `UNIQUE (email)` and hoping callers normalize; `citext` as a reflex | Uniqueness must be enforced on the same expression the query uses, or two rows differing only in case both get in. |
| Fixed value set | Lookup table + FK, or `CHECK (col IN (...))` | free text; a value set that lives only in application code | Adding a value should not require redeploying every consumer, and labels/ordering need somewhere to live. |
| Open-ended document | `jsonb` | `json`; `jsonb` as a way to avoid designing | The docs say most applications should prefer `jsonb`, the documented exception being legacy assumptions about object-key ordering — and only `jsonb` supports GIN indexing of the document itself (an expression index such as `((doc->>'sku'))` works on either type). |
| Boolean | `boolean NOT NULL`, positively named | a nullable three-state boolean | If there is a real third state, it is an enum or a lookup, not a null. |

Exact limits worth knowing, from the numeric and date/time docs: `smallint` -32768..32767, `integer` -2147483648..2147483647, `bigint` -9223372036854775808..9223372036854775807; `numeric` up to 131072 digits before and 16383 digits after the decimal point; `timestamp`/`timestamptz` 8 bytes at 1 microsecond resolution; `date` 4 bytes at 1 day; `interval` 16 bytes.

**Collation is part of the schema.** Set it deliberately at database creation and treat a later change as a breaking one: sort order, comparison, and therefore `UNIQUE` and range results all depend on it. The ALTER TABLE docs are explicit that "if the collation for a column has been changed, an index rebuild is required because the new sort order might be different".

**Rules for `jsonb` columns:**

1. Keep documents small and atomic. Any update takes a row-level lock on the **whole row**, so a large document is a write-contention hotspot.
2. Keep a somewhat fixed structure, as the JSON docs themselves recommend. A document whose shape is genuinely unpredictable is also unqueryable.
3. Promote any field you filter, sort, join, or constrain on into a real column — or at minimum add an expression index on it. There are no types, no `NOT NULL`, and no foreign keys inside a document.
4. Choose the GIN operator class deliberately: default `jsonb_ops` indexes keys and values; `jsonb_path_ops` is smaller and faster but supports fewer operators.
5. `jsonb` rejects null bytes inside strings and rejects `NaN`/`Infinity` numerics. Do not design a serialization format that needs them. (Note: PostgreSQL's JSON docs still cite RFC 7159, which has been obsoleted by RFC 8259, Internet Standard STD 90.)

**Timestamp range queries:** write `ts >= :start AND ts < :end`. Never `BETWEEN` — it is a closed interval, so a month range includes only the first instant of the final day, and adjacent ranges double-count the boundary instant (wiki).

## 7. Indexing

Every index must be justified by a specific named query. Indexes are pure redundancy the database keeps consistent on every write: an `INSERT` takes no *direct* benefit from an index on the table it writes, so every index there is net insert cost (indexes still serve an `INSERT` indirectly, via unique-constraint and foreign-key parent checks — which is why the *parent* index matters); `UPDATE`/`DELETE` use indexes to find rows but still pay index maintenance. Unused indexes also prevent heap-only tuple updates, which is why the docs say indexes "seldom or never used in queries should be removed".

**Composite index column order** — order by predicate shape, never by selectivity:

1. All equality (`=`, `IN`) columns first.
2. Then at most **one** range column (`<`, `>`, `BETWEEN`).
3. Then, only if justified, `INCLUDE` payload columns.

Only leading equality predicates plus the first inequality act as *access* predicates that narrow the scanned index range. Everything after it is a *filter* predicate that still reads index leaf entries. Winand's rule of thumb: "Index for equality first — then for ranges."

**Leftmost prefix:** an index on `(a, b, c)` serves `(a)`, `(a, b)` and `(a, b, c)` — and does not usefully serve `(b)` or `(c)` alone, exactly as a phone book sorted by surname cannot be searched by first name. (Recent PostgreSQL can sometimes rescue a non-leading predicate with a B-tree *skip scan*, but only when the leading column has very few distinct values; treat that as a lucky recovery, never as a design assumption.) Order the columns so the widest set of *real* queries can share one index; a wrongly-ordered index is dead weight that still costs write time.

| Index tool | Use when | Limits and traps |
|---|---|---|
| Composite B-tree | The dominant query filters on several columns | Keep to about **3 key columns**; the docs say indexes with more than three columns are unlikely to help "unless the usage of the table is extremely stylized". Hard maximum 32 columns including `INCLUDE`. |
| Expression index | The query filters on an expression: `lower(email)`, `date_trunc('day', created_at)`, `(payload->>'sku')` | Wrapping an indexed column in a function makes the plain index unusable — the optimizer treats the function as a black box. The index is used only when "the exact expression of the index definition appears in an SQL statement". Alternative: a stored generated column indexed normally (and still the only route on SQL Server). |
| Partial index | Excluding a very common value, excluding uninteresting rows (`WHERE deleted_at IS NULL`, `WHERE status <> 'done'`), or subset uniqueness | The query predicate must *imply* the index predicate, and the planner cannot prove that for a parameterized predicate — a partial index on `WHERE status = 'active'` will not serve `WHERE status = $1`. Do **not** build a fan of non-overlapping partial indexes as a substitute for partitioning; the planner understands partition bounds and does not understand that relationship. |
| `INCLUDE` payload / covering index | One hot query on a **slowly-changing** table | An index-only scan needs the heap page's all-visible bit set, so on a frequently-updated table the heap is visited anyway and the payload was pure bloat. The docs: "little point in including payload columns ... unless the table changes slowly enough". |
| Non-B-tree access methods | Containment, full text, geometry, huge append-only ranges | Only B-tree, GiST, GIN and BRIN support multiple key columns at all. Column order matters for B-tree and GiST; it is irrelevant for GIN and BRIN. |

- **Do not index every column named in a `WHERE` clause.** One well-ordered composite index usually replaces three single-column ones at a third of the write cost.
- **`ANALYZE` the affected tables** after creating an index, after a backfill, and after any bulk load, before judging anything. Plans come from statistics.
- **Drop indexes with zero recorded scans** (see the gate in section 16), after confirming they do not enforce a constraint and are not used only by a monthly job.
- Prefer a real index over a cache. Add the index first, measure, then decide whether the cache is still needed.

## 8. Query Performance and EXPLAIN

- Validate every index or query change with `EXPLAIN (ANALYZE, BUFFERS)` against a **production-scale** dataset. Plain `EXPLAIN` shows only estimates in arbitrary cost units (`seq_page_cost = 1.0` is the unit), and the docs warn that results do not extrapolate across data sizes — a 1,000-row development table genuinely is faster to sequentially scan, so no index will ever be chosen there.
- **Compare estimated rows to actual rows at every node.** Agreement within an order of magnitude is the bar. A large divergence means the statistics or your model of the data is wrong, and no index will fix that.
- **Multiply a node's reported time and rows by its `loops` count** before concluding anything. Per-node figures are averages per execution, so a cheap-looking inner node of a nested loop can dominate the runtime.
- **`EXPLAIN ANALYZE` actually executes the statement.** For `INSERT`/`UPDATE`/`DELETE`, always wrap it: `BEGIN; EXPLAIN (ANALYZE, BUFFERS) UPDATE ...; ROLLBACK;`
- Recent PostgreSQL enables `BUFFERS` implicitly with `ANALYZE`; older majors default it off. **Always write `EXPLAIN (ANALYZE, BUFFERS)` explicitly** and read the buffer counts to distinguish "slow because it read a lot" from "slow because it computed a lot" — a bare `EXPLAIN ANALYZE` on a pre-18 server reports no buffers at all, which is not the same as no I/O.
- Timing instrumentation has overhead. Before trusting a microbenchmark, measure it with `pg_test_timing`.
- **Never use `NOT IN` against a subquery whose expression can be null** — a single null makes the predicate return zero rows, and the wiki notes it also optimizes poorly (O(N^2)). Use `NOT EXISTS`.
- **List columns explicitly in production queries.** `SELECT *` breaks silently when a column is added, dropped, or reordered, and it defeats index-only scans.

## 9. Migrations and Zero-Downtime Evolution

- **Every schema change is a versioned migration file**, committed in the same repository and the same commit as the code that needs it. Sadalage and Fowler are explicit: all database artifacts belong in version control alongside the application, each change expressed as a migration script. Out-of-band DDL desynchronizes environments and makes the schema unreproducible.
- **Every migration ships a tested rollback path.** Either a reverse migration that CI actually executes, or — for genuinely irreversible steps — a written recovery plan in the PR (restore point, retained shadow column, replay procedure). "We would restore a backup" is only a plan once someone has timed it.
- **Every developer and every CI job gets its own database instance**, and migrations run in CI on every commit.
- **No destructive DDL without an explicit sign-off note** in the PR naming what is dropped, what reads it today, and how long the data has been unused.

**Expand / migrate / contract** (ParallelChange, as documented by Danilo Sato on martinfowler.com, which credits Joshua Kerievsky with first documenting it as a refactoring strategy in 2006). Three **separately released** phases, because during a rolling deploy old and new application code run simultaneously against one schema:

| Phase | Schema | Application |
|---|---|---|
| Expand | Add the new column/table/constraint, nullable or with a non-volatile default. Nothing removed. | Deploy code that writes both old and new, reads old. Old instances keep working untouched. |
| Migrate | Backfill the new structure in batches (section 10). Add constraints `NOT VALID`, then validate. | Switch reads to the new structure. Verify under real traffic; this is the last phase where reverting is cheap. |
| Contract | Drop the old column/table/constraint. | Remove the dual-write and the compatibility code. Only after the previous release is fully retired. |

- **Never rename or drop a column, table, or constraint in the same release that changes the code using it.** To a still-running old process a rename is a drop plus an add: it fails every in-flight query, and rollback becomes impossible without data loss. Add the new name, dual-write, migrate, then drop.
- **Never combine an additive change with a destructive one in one migration.** They have different rollback stories.

**PostgreSQL lock and rewrite discipline** — the mechanics that decide whether a migration is invisible or an outage. `ACCESS EXCLUSIVE` is the default DDL lock, conflicts with every other lock mode, and is the only mode that blocks a plain `SELECT`; waiters wait indefinitely by default.

| Operation | Safe recipe | If you do it naively |
|---|---|---|
| Lock waits, in every migration session | `SET lock_timeout = '3s'`, and retry the statement on `55P03` (`lock_not_available`). This is the setting that prevents the DDL-queue outage. | The DDL queues behind one long-running query, and every subsequent `SELECT` queues behind the DDL. A one-millisecond `ALTER` becomes a site outage. |
| Runaway statement runtime | Set a `statement_timeout` on lock-taking, table-scanning DDL. Explicitly raise or disable it (`SET statement_timeout = 0`) for the long online operations — `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`, `REINDEX ... CONCURRENTLY` — which are designed to run long *without* blocking writes. | Both extremes bite. Unbounded, a scanning `ALTER` holds `ACCESS EXCLUSIVE` for hours; bounded at a minute, the timeout kills a legitimate `CREATE INDEX CONCURRENTLY` on a large table and leaves an INVALID index behind. `statement_timeout` bounds total statement runtime, not lock waits, so it is never a substitute for `lock_timeout`. |
| `ADD COLUMN` | Nullable, or with a **non-volatile** `DEFAULT` (stored in catalog metadata and applied on read, so it is fast at any table size) | A volatile default (`clock_timestamp()`), a stored generated expression, an identity column, or a constrained domain type rewrites the entire table and all its indexes under `ACCESS EXCLUSIVE`. |
| Add `CHECK` or `FOREIGN KEY` to a populated table | `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` in a **separate transaction** — validation takes only `SHARE UPDATE EXCLUSIVE` and does not lock out writes | A single-step `ADD CONSTRAINT` scans the whole table with writes blocked. |
| `SET NOT NULL` | Add a **valid** `CHECK (col IS NOT NULL)` first (itself `NOT VALID` then `VALIDATE`); `SET NOT NULL` then skips the scan because a proving constraint exists | A bare `SET NOT NULL` scans the table. |
| Create an index | `CREATE INDEX CONCURRENTLY`, **outside** any transaction block; afterwards confirm the index is not `INVALID`. Most migration runners wrap each migration in a transaction by default, so you must turn that off for this migration (Rails `disable_ddl_transaction!`, Django `atomic = False`, an Alembic autocommit/`AUTOCOMMIT` block, Flyway `executeInTransaction=false`) or the statement errors out immediately. The same applies to `REINDEX ... CONCURRENTLY` and `DETACH PARTITION CONCURRENTLY`. Confirm the flag's current spelling in your runner's own documentation. | A plain `CREATE INDEX` blocks all writes for the duration. `CONCURRENTLY` costs two table scans and waits on existing transactions, and on failure leaves behind an "invalid" index that carries write cost while never serving a query — drop and retry, or `REINDEX INDEX CONCURRENTLY`. |
| Change a column type | Treat it as expand/migrate/contract with a new column | A type change normally rewrites the table unless the types are binary coercible. |
| Several scans or rewrites needed | Combine the subcommands into **one** `ALTER TABLE` — the docs give combining scans/rewrites into a single pass as the main reason multiple subcommands are allowed | Sequential statements lock the table repeatedly. Note the strictest subcommand's lock applies to the whole statement, and rewriting forms are not MVCC-safe. |
| `DROP COLUMN` | Expect the space back only after a rewrite | The column becomes invisible; the storage is not reclaimed. |

## 10. Backfills and Bulk Loads

**A backfill is not a migration.** Run it as a separate, restartable job:

1. **Batched** on an indexed key (primary key ranges or a keyset cursor). Start around 1,000-10,000 rows per batch and tune from measured lock duration and WAL volume.
2. **One transaction per batch.** A single `UPDATE` over millions of rows holds row locks and bloats WAL for its whole duration, cannot resume after a failure, and can time out repeatedly with zero progress.
3. **Idempotent** — re-running a batch is a no-op (`WHERE new_col IS NULL`).
4. **Resumable** — persist the cursor, so a killed job restarts where it stopped.
5. **Throttled and observable** — a pause between batches, a progress log, and a kill switch.
6. **`ANALYZE` the table afterwards**, before judging any query's performance.
7. **Expect bloat.** A backfill that touches every row writes a new version of every row, so heap and index size roughly double; autovacuum makes the space reusable but does not return it to the filesystem. Keep autovacuum running during the backfill — do not disable it — then decide deliberately whether to leave the space for reuse or reclaim it. `VACUUM FULL` and `CLUSTER` take `ACCESS EXCLUSIVE` for the whole rewrite, so on a live table use an online repack tool or the expand/migrate/contract route instead.

**Initial loads and large restores**, in the order the docs prescribe: one transaction; `COPY` rather than `INSERT`; create indexes *after* the data is in; drop and recreate foreign keys around the load — loading millions of rows with FK triggers active can overflow the trigger event queue and fail the command outright; raise `maintenance_work_mem` and `max_wal_size`; then `ANALYZE`.

## 11. Soft Deletes and Audit Columns

- **Prefer an explicit state column** (`status`, or `archived_at` with a documented meaning), or moving the row to an archive table, over a generic soft delete. "Deleted" usually means something more specific, and the specific thing is queryable.
- **If you use `deleted_at timestamptz`:** every unique index must become a partial index `WHERE deleted_at IS NULL`, or a logically deleted record can never be re-created; and **every** read path must filter it. Audit the existing queries in the same PR — one forgotten filter leaks deleted rows into a report, an export, or an authorization check.
- **Audit columns on every table:** `created_at timestamptz NOT NULL DEFAULT now()` and `updated_at timestamptz NOT NULL DEFAULT now()`, with `updated_at` maintained by a **trigger**, not by application code. Application-maintained timestamps are skipped by every other writer, which destroys their value for incremental syncs and debugging.
- **For "who changed what", write an append-only history table** (or use logical decoding). Mutable audit columns record only the latest change and can never answer what the previous value was or who set it — the questions audits actually ask.

## 12. Multi-Tenancy and Row Isolation

For a shared-schema multi-tenant database:

- `tenant_id NOT NULL` on **every** tenant-scoped table.
- `tenant_id` is the **leading column** of the primary key and of tenant-scoped indexes. By the leftmost-prefix rule, one such index then serves both "this tenant" and "this tenant plus this filter".
- **Foreign keys are composite** — `(tenant_id, parent_id)` referencing `(tenant_id, id)`. A single-column FK permits a child row that references another tenant's parent, and no application check catches that reliably.
- Unique constraints on tenant-scoped business keys include `tenant_id`.

**Row-level security is defense in depth, not the isolation mechanism** (PostgreSQL-specific):

- Enabling RLS with no policy is default-deny. `USING` governs visibility, `WITH CHECK` governs writes — write both.
- Permissive policies are OR-combined; only `RESTRICTIVE` policies are AND-combined. A hard tenant boundary must be `RESTRICTIVE`, or any permissive policy can widen it.
- **Table owners are not subject to policies** unless you set `FORCE ROW LEVEL SECURITY`, and superusers and `BYPASSRLS` roles always bypass them. An application connecting as the table owner or as a superuser has silently disabled the entire mechanism.
- Referential-integrity checks necessarily bypass RLS, so a unique-constraint violation can reveal the existence of a row the caller cannot see. Design unique constraints and foreign keys with that inference channel in mind; RLS is not a confidentiality guarantee against constraint probing.
- Set `row_security = off` in jobs that must never be silently filtered — it turns silent filtering into an error.

## 13. Partitioning

- **Do not partition until the table is genuinely very large.** The documented rule of thumb: the benefit is worthwhile when the table size exceeds the physical memory of the database server. Below that you pay planning time and memory for no pruning benefit.
- **Choose the key from the columns that dominate `WHERE` clauses and from how you intend to drop old data.** The payoff is partition pruning plus dropping or detaching whole partitions instead of a bulk `DELETE`. Pruning is driven by partition bounds, not by indexes.
- **Check the constraint blocker first:** `PRIMARY KEY`, `UNIQUE` and `EXCLUDE` constraints on a partitioned table must include **all** partition key columns, because each partition's index is local. If a required uniqueness rule cannot include the key, do not partition on that key. This is what most often invalidates a partitioning plan after the fact.
- **Keep the partition count modest** and simulate the real workload before committing. Too few leaves oversized indexes and poor locality; too many inflates planning time and per-session memory, since each partition's metadata must be loaded. OLTP workloads tolerate far fewer partitions than data-warehouse workloads.
- **Prefer hash over list partitioning** when the number of distinct values will grow — the docs note hash is more future-proof. Avoid sub-partitioning unless a single partition is itself too large.
- Detach with `DETACH PARTITION CONCURRENTLY` where available; it takes a weaker lock. Like every other `CONCURRENTLY` form it cannot run inside a transaction block, so the migration must have its runner's per-migration transaction turned off (section 9).
- Do not fake partitioning with dozens of partial indexes, and do not clone tables or columns per value (`orders_2026`, `orders_2027`) instead of partitioning.

## 14. Naming Conventions

All lower_snake_case, never quoted, never mixed-case. PostgreSQL folds unquoted identifiers to lower case, so a quoted mixed-case name must be quoted everywhere, forever, across every tool and driver.

| Object | Convention | Good | Bad |
|---|---|---|---|
| Table | lower_snake_case; **default to plural** (singular is an acceptable house style only where the repo already uses it), and never mix the two | `order_items` | `OrderItems`, `tbl_order`, `orderitems2` |
| Column | singular, no table-name prefix, no reserved keyword | `email`, `shipped_at` | `Email`, `order_order_id`, `desc`, `value_` |
| Foreign key column | `<referenced_table>_id` | `customer_id` | `cust`, `fk1`, a bare `id` naming a reference |
| Timestamp / date | `_at` for instants, `_date` for calendar dates | `cancelled_at`, `invoice_date` | `cancel_ts`, `dt` |
| Numeric roles | `_count`, `_total`, `_seq`, `_num`, `_size` | `retry_count`, `line_total` | `cnt2`, `amt` |
| Boolean | positive predicate | `is_active`, `has_consent` | `not_disabled`, `inactive`, `flag` |
| Primary key | `<table>_pkey` | `orders_pkey` | unnamed |
| Unique constraint | `<table>_<columns>_key` | `users_email_key` | unnamed |
| Foreign key | `<table>_<column>_fkey` | `orders_customer_id_fkey` | unnamed |
| Check constraint | `<table>_<rule>_check` | `orders_total_non_negative_check` | unnamed |
| Index | `<table>_<columns>_idx`, `_key` suffix when unique | `orders_tenant_id_created_at_idx` | `idx1`, `orders_idx` |

- **Default to the engine's own auto-generated shape, written out explicitly** — `orders_pkey`, `users_email_key`, `orders_customer_id_fkey`, `orders_total_non_negative_check`, `orders_tenant_id_created_at_idx`. The `pk_`/`uq_`/`fk_`/`ck_`/`ix_` prefix family is an acceptable alternative (it groups objects by kind in a sorted listing), but pick one family per repository and never mix them.
- **Name every constraint and index explicitly.** Auto-generated names differ between environments and between creation paths, so a migration that does `DROP CONSTRAINT` by name breaks in some environments and not others.
- Names begin with a letter, contain only letters, digits and underscores, never end in an underscore, and never contain consecutive underscores.
- No Hungarian prefixes (`tbl_`, `sp_`); no table named the same as one of its columns; always spell out `AS` for aliases.
- **House convention:** keep identifiers under 30 characters so they stay readable and survive every tool. This is a style-guide convention, not a database limit — check your engine's actual identifier limit before relying on any number.
- Do not use table inheritance or rules. Use declarative partitioning and foreign keys instead of inheritance, and triggers instead of rules — the wiki notes a rule rewrites the query rather than adding conditional logic, so non-trivial rules are simply incorrect.

## 15. Named Anti-Patterns

Karwin's *SQL Antipatterns* vocabulary, worth adopting because it makes review comments short and unambiguous:

| Name | What it looks like | Fix |
|---|---|---|
| Jaywalking | Comma-separated ids in one column | Child or junction table with a real FK |
| Naive Trees | Adjacency list where the queries are subtree-shaped | Pick a traversal structure by the rule in section 3 (closure table by default) |
| ID Required | A surrogate `id` bolted onto every table reflexively | Natural key where it is immutable and narrow; where you add a surrogate, keep the natural-key `UNIQUE` |
| Keyless Entry | Tables or joins with no foreign keys, or no primary key | Declare them |
| Entity-Attribute-Value | `(entity_id, attr_name, value)` for a shape you know | Typed columns; `jsonb` only for genuinely open shapes |
| Polymorphic Associations | `parent_id` + `parent_type` | One nullable FK per parent + `CHECK`, or per-parent intersection tables |
| Multicolumn Attributes | `tag1`, `tag2`, `tag3` | Child table |
| Metadata Tribbles | A table or column cloned per value (`orders_2026`) | Declarative partitioning |
| Rounding Errors | Float for money | `numeric`, or integer minor units |
| 31 Flavors | The allowed value set hardcoded where it cannot be joined or extended | Lookup table + FK, or an explicit `CHECK` |
| Index Shotgun | Indexing at random, or one index per `WHERE` column | One justified composite index per query shape |
| Fear of the Unknown | Mishandling null (`= NULL`, `NOT IN` with nulls, a null-defeated `CHECK`) | `IS NULL`/`IS NOT NULL`, `NOT EXISTS`, `NOT NULL` |
| Implicit Columns | `SELECT *` in production code | Explicit column lists |
| Readable Passwords | Recoverable password storage | Salted hashes only |
| Pseudokey Neat-Freak | Renumbering surrogate keys to close gaps | Leave the gaps |

## 16. Schema Gates

Run these as review aids, and as CI checks where they prove stable. **Record your project's own baseline the first time you run each one**, then gate on "no worse than baseline" — never on an absolute number copied from another project. The catalog queries below are hand-written constructions, not documented APIs: test each against your own database and confirm the hits by hand before wiring it into CI.

```sql
-- Tables with no primary key
SELECT t.table_schema, t.table_name
FROM information_schema.tables t
WHERE t.table_type = 'BASE TABLE'
  AND t.table_schema NOT IN ('pg_catalog', 'information_schema')
  AND NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints tc
    WHERE tc.table_schema = t.table_schema AND tc.table_name = t.table_name
      AND tc.constraint_type = 'PRIMARY KEY');

-- Forbidden data types
-- this excludes only the system schemas; replace with an inclusion list of your project's
-- schemas (e.g. table_schema IN ('app','billing')) so extension-owned tables do not show up
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND data_type IN ('real', 'double precision', 'money', 'character',
                    'timestamp without time zone', 'time with time zone');

-- Foreign keys whose leading child column is not indexed
-- (leading-column heuristic: expect false positives and negatives on composite keys.
--  A partial or INVALID index does not count as covering a foreign key, hence the
--  indpred/indisvalid tests: a partial index WHERE deleted_at IS NULL would otherwise
--  mask a genuinely unindexed FK.)
SELECT c.conrelid::regclass AS child_table, c.conname
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (SELECT 1 FROM pg_index i
                  WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]
                    AND i.indisvalid AND i.indpred IS NULL);

-- Never-used indexes, largest first
-- this also lists primary-key and unique-constraint indexes, which cannot be dropped
-- without dropping the constraint (see section 7), and on an idle or freshly restored
-- database every index has zero scans -- read it against production statistics only
SELECT relname, indexrelname, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- INVALID indexes left behind by a failed CREATE INDEX CONCURRENTLY
SELECT c.relname
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
WHERE NOT i.indisvalid;

-- NOT VALID constraints that were never validated
SELECT conrelid::regclass, conname, contype
FROM pg_constraint
WHERE NOT convalidated;

-- Nullable-column ratio per table: a rigor signal, not a verdict
-- this excludes only the system schemas; replace with an inclusion list of your project's
-- schemas (e.g. table_schema IN ('app','billing')) so extension-owned tables do not show up
SELECT table_schema, table_name,
       count(*) FILTER (WHERE is_nullable = 'YES') AS nullable,
       count(*) AS total
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
GROUP BY 1, 2 ORDER BY 3 DESC;
```

| CI gate | How |
|---|---|
| Migrations reproduce the committed schema | Run all migrations on an empty database, `pg_dump --schema-only --no-owner --no-privileges`, diff against the checked-in reference schema, fail on any difference. |
| Rollback actually works | Apply the migration, run the reverse migration, apply it again. Fail if any step errors or the dumps disagree. |
| Backward compatibility during rollout | Run the **previous** release's test suite against the new schema. An expand-phase migration that fails it is not an expand-phase migration. |
| No migration can hang the database | Grep every migration file for `lock_timeout`; fail if it is missing. Require `statement_timeout` to be **stated** rather than merely present — a value, or an explicit `SET statement_timeout = 0` with a one-line reason — so long online builds are opted out on purpose instead of being killed mid-build. |
| Plan verification for index and query changes | `EXPLAIN (ANALYZE, BUFFERS)` output on production-sized data pasted in the PR, with estimated vs actual rows agreeing within an order of magnitude at every node. |
| Rewrite detection | Run the migration against a production-sized copy and compare `pg_relation_filenode('tbl')` before and after — a changed filenode means a full rewrite happened. (Hand-rolled technique; verify it on your version.) |
| Style and unsafe-DDL linting | A SQL linter for style and naming, plus a Postgres migration linter for unsafe DDL (sqlfluff and squawk are the usual choices). Confirm current rule names and config format against each tool's own documentation before wiring it up. |

## 17. AI Agent Rules

When writing or reviewing schema, DDL, or migrations, the agent **must**:

1. **Read the existing schema first.** Match the repo's naming, key strategy, audit columns, and migration tooling. The repo's convention beats this document.
2. **Never store money in a float or double.** Exact `numeric`/`decimal`, or integer minor units plus a currency column. Not negotiable, and not "close enough".
3. **Store every instant as a timezone-aware UTC timestamp** (`timestamptz`), and convert to a local zone only at the presentation boundary.
4. **Put the constraint in the database.** Anything described as "must always" gets `NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`, or `EXCLUDE`. Application-only validation is not a guarantee, because the application is not the only writer.
5. **Mark columns `NOT NULL` by default**, and when leaving one nullable, state in the migration what a null means there.
6. **Declare a foreign key for every reference, and index the child columns of every foreign key.**
7. **Give every table a primary key**, join tables and event logs included.
8. **Ship a reviewed migration with every schema change, with a tested rollback path.** Never edit an already-applied migration; add a new one.
9. **Never rename or drop a column, table, or constraint in the same release that stops using it.** Propose expand / migrate / contract explicitly as three deploys, and say which phase the current change is.
10. **Never mix an additive and a destructive change in one migration.**
11. **Set `lock_timeout` in every migration** and retry on `55P03`; state `statement_timeout` deliberately — a bound for lock-taking, table-scanning DDL, and an explicit `SET statement_timeout = 0` with a stated reason for long online operations (`CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`), which a timeout kill would leave half-done. Use the online recipes in section 9 (`NOT VALID` then `VALIDATE`, `CREATE INDEX CONCURRENTLY` outside a transaction, non-volatile defaults), and state which statements can rewrite the table.
12. **Write backfills as separate batched, idempotent, resumable jobs** — never as one unbounded `UPDATE` inside a migration — and `ANALYZE` afterwards.
13. **Never run destructive DDL without an explicit sign-off note** naming what is dropped, what still reads it, and the recovery path. Ask; do not assume the data is dead.
14. **Justify every new index with the query it serves**, and state the write cost. Do not add an index per `WHERE` column.
15. **Verify performance claims with `EXPLAIN (ANALYZE, BUFFERS)` on production-scale data**, quote the real output, and wrap DML explains in `BEGIN; ... ROLLBACK;`. Never claim a measurement you did not take.
16. **Never invent business rules** — retention windows, allowed statuses, rounding and currency behaviour, tenancy boundaries, uniqueness rules. Ask, and state assumptions explicitly when proceeding under uncertainty.
17. **Say which engine and version you are assuming**, and flag any syntax that is PostgreSQL-specific when the project is not PostgreSQL.
18. **Keep the change minimal.** No drive-by renames, no reformatting untouched migrations, no "while I was in there" index changes.

## 18. Review Checklist

For a reviewer or an AI reviewer. Flag only real defects; cite `file:line` and state the failure scenario.

**Modeling** — one entity per table, one atomic value per column? any list-in-a-column, numbered repeating columns, EAV bag, or untyped polymorphic parent? denormalization justified with a measurement and a named owner for the invariant? hierarchy structure matched to the queries it must answer?

**Keys** — primary key on every new table? natural key still `UNIQUE` behind a new surrogate? `bigint` identity rather than `serial` or a 32-bit key? a random UUID used as a primary key where a time-ordered one belongs? any renumbering of existing keys?

**Constraints** — every "must always" rule enforced in the database? `CHECK` on a nullable column handling the null case explicitly? `UNIQUE` on nullable columns doing what the author thinks? referential action chosen deliberately rather than defaulted? composite FK columns `NOT NULL` or `MATCH FULL`? overlap rules using `EXCLUDE` instead of an application check? any `CHECK` reading other rows or tables?

**Types** — money exact, with a currency column? instants as `timestamptz`, calendar facts as `date`? no `char(n)`, no guessed `varchar(n)`, no `money`, no float for exact quantities? case-insensitive uniqueness enforced on the same expression the queries use, rather than assumed? `BETWEEN` used on a timestamp range? new `jsonb` column small, mostly-fixed, with filtered fields promoted or expression-indexed?

**Indexing** — each new index tied to a named query? composite order equality-then-range, and does the leading column match how the query actually filters? more than about three key columns? expression index text matching the query exactly? partial index predicate provable from a parameterized query? `INCLUDE` columns on a hot-write table? any existing index made redundant and not dropped?

**Query performance** — `EXPLAIN (ANALYZE, BUFFERS)` shown, on production-scale data? estimated vs actual rows within an order of magnitude at each node? nested-loop inner nodes read with `loops` applied? `NOT IN` over a nullable subquery? `SELECT *` in production code? `ANALYZE` after the data change?

**Migrations** — one migration per logical change, additive and destructive kept apart? rollback path tested rather than merely written? `lock_timeout` set, and `statement_timeout` stated deliberately (a bound, or an explicit `0` with a reason for a long online build)? non-transactional migration flag set for every `CONCURRENTLY` statement? any statement that rewrites the table or takes `ACCESS EXCLUSIVE` on a large table, and was the online recipe used? a rename or drop in the same release as the code change? which expand/migrate/contract phase is this, and is the previous release still compatible?

**Backfills** — batched on an indexed key, one transaction per batch, idempotent, resumable, throttled? run outside the schema migration? `ANALYZE` afterwards? autovacuum left enabled, and the doubled heap/index size either accepted deliberately or reclaimed without an `ACCESS EXCLUSIVE` rewrite? bulk-load ordering (COPY, indexes after, FKs recreated) followed?

**Soft delete and audit** — unique indexes converted to partial `WHERE deleted_at IS NULL`? every read path filtering deleted rows, including exports and permission checks? `updated_at` maintained by a trigger rather than application code? history needs met by an append-only table rather than mutable columns?

**Multi-tenancy** — `tenant_id NOT NULL` present, and leading the primary key and tenant-scoped indexes? foreign keys composite so cross-tenant references are impossible? RLS policies covering both `USING` and `WITH CHECK`, `RESTRICTIVE` for the tenant boundary, `FORCE ROW LEVEL SECURITY` set, and the application role neither owner-exempt nor superuser/`BYPASSRLS`?

**Partitioning** — is the table actually large enough to warrant it? does the key match the dominant `WHERE` clauses and the retention story? can every required `PRIMARY KEY`/`UNIQUE`/`EXCLUDE` include the partition key? partition count modest? not a fan of partial indexes or per-value cloned tables instead?

**Naming** — lower_snake_case, unquoted, no reserved keywords, no `tbl_`/`sp_`? constraints and indexes named explicitly rather than auto-generated? booleans positive? `_at`/`_date` suffixes correct? consistent with the tables around it?

**Security** — credentials stored only as salted hashes? no new PII without a retention answer? tenancy and ownership enforceable in a query rather than only in code? nothing in a constraint name or error message that leaks data?

## 19. References

Sources for every rule above are documented in the upstream repo:
https://github.com/Madheshvivekanandan/ai-engineering-skills (skills/sql-schema-design-best-practices/references/sources.md).
