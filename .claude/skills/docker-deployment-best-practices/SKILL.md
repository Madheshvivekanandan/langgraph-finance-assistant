---
name: docker-deployment-best-practices
description: Production standard for containerizing and shipping an application. Load BEFORE writing or reviewing a Dockerfile, .dockerignore, docker-compose file, Kubernetes Deployment/Pod manifest, Helm values, or a CI job that builds, scans, tags, pushes, deploys, or rolls back a container image. Covers multi-stage builds, base image pinning, layer cache ordering, build-time and runtime secrets, non-root and hardened runtime, PID 1 and graceful shutdown, health probes, resource limits, image tagging/provenance/SBOM, vulnerability scanning gates, and rollback-safe deploys.
---

# Docker and Deployment Best Practices

Opinionated synthesis of the Docker build and BuildKit documentation, the OWASP Docker Security
Cheat Sheet, NIST SP 800-190, the Twelve-Factor App, the OCI image spec annotations, and the
Kubernetes docs on probes, resources, and Deployments. Applies to any OCI image built with
Docker/BuildKit and run under Docker, Compose, or Kubernetes. When this document conflicts with an
existing in-repo convention, follow the repo and say so.

## 1. Philosophy

- **The image is the artifact.** Build once, promote the same bytes through every environment. Never
  rebuild per environment.
- **Config is injected, never baked.** The only thing that differs between staging and production is
  environment variables and mounted secrets.
- **Immutable and identifiable.** Every deployed image is addressable by a tag you can never
  overwrite, and ideally by digest.
- **Smallest thing that runs.** Every package you ship is a package you must patch.
- **Least privilege by default.** Non-root, no capabilities, read-only root filesystem; add back
  only what fails without it.
- **Containers die constantly.** Design for SIGTERM, crash-only restart, and at-least-once
  redelivery — not for a graceful world.
- **A gate that does not fail the build is documentation.** Scanning, linting, and policy checks
  must break CI.
- **Rollback is a feature you design in**, not something you improvise during an incident.

## 2. Hard Rules (non-negotiable)

| Rule | Why | Wrong | Right |
|---|---|---|---|
| Never bake a secret into an image | `ENV` values persist into every running container and show in `docker inspect`; `ARG` values are not embedded in the image but are recorded in build history (`docker history`) and in `max`-mode provenance attestations. Deleting the file in a later layer does not remove it from earlier layers | `ARG NPM_TOKEN` / `ENV API_KEY=...` / `COPY .npmrc .` | `RUN --mount=type=secret,id=npm_token ...` at build; env var or mounted secret file at run |
| Never run the app as root | Root in the container maps to real host privilege absent user namespaces | no `USER` instruction | explicit `USER 10001:10001` as the last identity change in the final stage |
| Never deploy a floating tag | You cannot tell what is running and have no known artifact to roll back to | `image: app:latest` | `image: app:1.8.3` or `app@sha256:...` |
| Pin base images by digest | A tag can be repointed at different content after you reviewed and scanned it | `FROM node:22.13-slim` (tag only, no digest) | `FROM node:22.13-slim@sha256:...` |
| Install dependencies before copying source | Otherwise every source edit reinstalls the whole dependency tree | `COPY . .` then `npm ci` | `COPY package*.json ./` then `npm ci` then `COPY . .` |
| Always ship a `.dockerignore` | Without it the context leaks `.git`, `.env`, and local credentials into the image | missing file | committed at the context root, and verified against the built image's **file listing** (`docker export` piped to `tar -tf`, section 12) — `docker history` cannot see this, and no build check detects a missing `.dockerignore` |
| Handle SIGTERM and drain | Unhandled SIGTERM means every deploy drops in-flight requests | no signal handler; shell-form `CMD` | exec-form entrypoint plus an explicit shutdown handler |
| Log to stdout/stderr as a stream | The platform owns aggregation and retention; in-container log files vanish on restart | writing `/var/log/app.log` plus logrotate | unbuffered structured lines on stdout |
| Set explicit resource requests and limits | Without limits one container starves its neighbours | no `resources:` block | CPU + memory requests and limits on every container |
| Act on scan findings | Unenforced scan output accumulates forever | scan step with `\|\| true` | non-zero exit on fixable HIGH/CRITICAL |

## 3. Base Image Selection

| Decision | Default | Notes |
|---|---|---|
| Source | Docker Official Image, Verified Publisher, or Docker-Sponsored Open Source; otherwise your own trusted registry mirror | Untrusted base images are a documented supply-chain risk |
| Variant | Smallest that runs the app: `-slim` for glibc, distroless-style for compiled binaries, Alpine only when you have verified musl compatibility | Fewer packages means fewer CVEs to triage |
| Reference | `FROM <image>:<tag>@sha256:<digest>` in production Dockerfiles | Update digests deliberately via a bot PR, not implicitly |
| Runtime version | Pin the narrowest variant tag the image actually publishes — check the registry's tag list rather than assuming. Official Images such as `python` and `node` publish `<major>.<minor>` and `<major>.<minor>.<patch>` variant tags alongside the bare `<major>`. Pin the digest as well. Never a bare `python:3` or `node:22` | Bare major tags move under you. Where an image publishes only a major-level variant tag, the digest is the only real pin |
| Refresh cadence | Rebuild and redeploy weekly, and immediately for a critical base CVE | Never patch a running container; the change is lost on restart |

Alpine caveat: musl changes DNS resolution and native-extension builds, so if you choose it you own
the compatibility testing. The default recommendation is `-slim`.

## 4. Dockerfile Authoring

Order instructions from least to most frequently changing, because everything after the first
changed layer is rebuilt: pinned `FROM`, system packages, non-root user creation, absolute
`WORKDIR`, dependency manifests, dependency install, application source, then `USER` / `EXPOSE` /
`HEALTHCHECK` / `ENTRYPOINT`.

| Rule | Good | Bad |
|---|---|---|
| One `RUN` for update + install + cleanup | `RUN apt-get update && apt-get install -y --no-install-recommends curl=7.88.* && rm -rf /var/lib/apt/lists/*` | `RUN apt-get update` then a separate `RUN apt-get install` (freezes a stale index in cache) |
| Pin package versions | `libpq5=15.*` | `libpq5` |
| Sort multi-line lists alphanumerically, one per line | one package per line, backslash-continued, sorted | one long unsorted line with duplicates |
| Absolute `WORKDIR` | `WORKDIR /app` | `RUN cd /app && ...` |
| `COPY` for local files | `COPY --chown=10001:10001 app/ ./app/` | `ADD . .` |
| `ADD` only for remote/Git sources, with a checksum | `ADD --checksum=sha256:... https://... /tmp/x` | unverified `ADD https://...` |
| `chown` at copy time, numerically | `COPY --chown=10001:10001` | `RUN chown -R 10001:10001 /app` (duplicates the whole tree into a new layer); a named `--chown=app:app` also fails silently if the `COPY` runs before the user exists, and will not match a numeric `runAsUser` in Kubernetes |
| `ENV key=value` | `ENV PYTHONUNBUFFERED=1` | `ENV PYTHONUNBUFFERED 1` (legacy form, flagged by `LegacyKeyValueFormat`) |
| Labels, not `MAINTAINER` | `LABEL org.opencontainers.image.authors="..."` | `MAINTAINER ...` (deprecated) |
| `pipefail` for piped `RUN` | `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` once per stage, or `RUN ["/bin/bash", "-c", "set -o pipefail && wget -O - https://... \| wc -l > /number"]` | a pipe whose first command's failure is silently swallowed (`/bin/sh -c` only checks the last command); plain `RUN set -o pipefail && ...` also **fails outright** on Debian-based `-slim` images, whose `/bin/sh` is dash and has no `-o pipefail` |
| One concern per container | app image; separate DB and cron images | app + Postgres + cron + nginx in one image |
| No `sudo` in an application image | `gosu` if a runtime user switch is truly required | `RUN apt-get install -y sudo` |

Use `RUN --mount=type=cache,target=<pkg cache dir>` for package manager caches (pip, npm, apt, Go
module cache) so rebuilds re-download only what changed and the cache never lands in a layer. Use
`RUN --mount=type=bind` to read build-only files without creating a layer.

On ephemeral CI runners the local layer cache is empty every run, so the ordering discipline above
pays off only with an external cache:
`docker buildx build --cache-from type=registry,ref=$REPO:buildcache --cache-to type=registry,ref=$REPO:buildcache,mode=max`.
Treat the cache ref as build infrastructure, never as a deployable tag. Registry cache export has the
same driver precondition as attestations (section 11): with the default `docker` driver it requires the
containerd image store, otherwise create a container builder first (`docker buildx create --use`).
Provision the builder as an explicit CI step, not implicitly — on an ephemeral runner without one, the
command above fails outright at cache export.

### Multi-stage build (mandatory for any compiled or dependency-installing app)

```dockerfile
# syntax=docker/dockerfile:1
# check=error=true
FROM python:3.12-slim@sha256:<digest> AS builder
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim@sha256:<digest> AS runtime
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=10001:10001 app/ ./app/
ENV PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()"]
# LABEL org.opencontainers.image.* belongs here, in the last layer — see section 11.
ENTRYPOINT ["python", "-m", "app.main"]
```

The final stage must contain no compilers, no build toolchain, no dev dependencies, no test
fixtures, and no `.git`. Note that the runtime stage copies the **application package only**, not the
whole build context: `COPY . .` in a final stage ships whatever `.dockerignore` happened to miss.
`.dockerignore` is the safety net, an explicit copy list is the actual control, and the whole-context
copy belongs only where the point is cache ordering (section 2).

The `HEALTHCHECK` timings above are a starting point, not a documented default — pick your own and
state them explicitly, as section 8 requires.

### .dockerignore

Commit it in the same change as the Dockerfile. At minimum:

```
.git
.env
.env.*
*.pem
*.key
node_modules
__pycache__
.venv
dist
build
coverage
tests
test
docs
*.md
.pytest_cache
.mypy_cache
.ruff_cache
Dockerfile*
docker-compose*.yml
.github
**/*.log
!README.md
```

Re-include anything your packaging metadata reads at build time (`readme = "README.md"` in
`pyproject.toml`, `long_description = file: README.md` in setuptools) — otherwise the dependency
install fails inside the builder stage with an opaque metadata error. An over-broad ignore is also
what `CopyIgnoredFile` fires on; see section 12.

Then confirm nothing sensitive survived, with the right tool for each half. `docker history
--no-trunc <image>` reveals leaked `ARG` values and instruction text, **not file contents** — a
`COPY . .` that swept in `.env` records only `COPY . . # buildkit`, so history cannot detect the
failure mode this file exists to prevent. Listing the image's actual contents is what proves it:

```bash
cid=$(docker create <image>)
docker export "$cid" | tar -tf - | grep -Ei '(^|/)(\.env($|\.)|\.git/|\.npmrc|\.netrc|\.aws/|id_(rsa|dsa|ecdsa|ed25519)$)|\.(pem|key|p12|pfx|jks)$'
docker rm "$cid"
```

`docker export` works on shell-less and distroless-style images because it reads the filesystem from
outside the container. Section 12 wires both checks in as failing gates.

## 5. Secrets

| Phase | Do | Never |
|---|---|---|
| Build | `RUN --mount=type=secret,id=<id>` (default target `/run/secrets/<id>`, or `env=` to expose as an env var for that RUN only), passed as `docker build --secret id=<id>,src=<path>` or `--secret id=<id>,env=<VAR>` | `--build-arg TOKEN=...`, `ENV TOKEN=...`, `COPY .netrc`, a token inside a `RUN` command line |
| Private Git/dependency fetch | `--ssh default` with an SSH mount, or the predefined `GIT_AUTH_TOKEN` / `GIT_AUTH_HEADER` secrets | tokens embedded in a repository URL |
| Runtime | Env vars from the orchestrator, or files mounted from a secret manager (Compose `secrets:` with `file:`, or `docker secret` when running Swarm — the `docker secret` CLI does not exist outside Swarm mode), read at startup | secrets in image `ENV` (they persist into every container and show in `docker inspect`), secrets in committed manifests |
| Rotation | Restart-to-reload, or re-read the mounted file on a signal | requiring an image rebuild to rotate a credential |

`docker build --check` reports `SecretsUsedInArgOrEnv`; treat that finding as a build failure. Run a
secret scanner (for example Gitleaks or TruffleHog — check each tool's own flags) over the
repository so a credential never reaches the build context.

## 6. Configuration and Logging (Twelve-Factor)

- All configuration comes from the environment: hostnames, credentials, feature flags, log level,
  worker counts. Same image bit-for-bit across dev, staging, and production.
- Strict build / release / run separation: a release is image digest + config, immutable and
  individually addressable so it can be rolled back as a unit.
- Processes are stateless and share nothing; anything that must persist goes to a database, object
  store, or cache — never the container filesystem.
- Logs are an event stream: write unbuffered, one structured line per event, to stdout (errors to
  stderr). The app never opens, rotates, ships, or retains log files.
- Set the runtime's unbuffered flag (`PYTHONUNBUFFERED=1`, no output buffering in your logger) or
  logs are lost when the container is killed.
- Admin/one-off tasks (migrations, backfills) run as separate processes using the **same image and
  config**, not from the app's startup path.

## 7. PID 1, Signals, and Graceful Shutdown

| Rule | Detail |
|---|---|
| Exec form only | `ENTRYPOINT ["./app"]`. Shell form runs under `/bin/sh -c`, which does not pass signals and ignores `CMD` and `docker run` arguments, so `docker stop` degrades into SIGKILL. `docker build --check` flags this as `JSONArgsRecommended`. |
| `ENTRYPOINT` + `CMD` split | `ENTRYPOINT` is the binary; `CMD` supplies default, overridable arguments. |
| Entrypoint scripts end with `exec` | `exec "$@"` (or `exec ./app`) so the real process becomes PID 1 instead of the shell. |
| Use an init when you spawn children | `docker run --init` runs an init that forwards signals and reaps processes; in Kubernetes use a process supervisor inside the image or avoid spawning unreaped children. |
| `STOPSIGNAL` | Set it explicitly only if your application expects a signal other than the runtime default. |

Shutdown sequence the application must implement:

1. Receive SIGTERM. Immediately flip readiness to failing.
2. Stop accepting new work — close the listening socket / release the port.
3. Finish in-flight requests, bounded by a deadline shorter than the grace period.
4. Workers: return or NACK the in-flight job to the queue and release locks.
5. Flush logs and metrics, close DB pools and client connections.
6. Exit 0.

- Make every job **reentrant and idempotent**: containers also die without warning, so at-least-once
  redelivery must be safe.
- In Kubernetes, endpoint removal is asynchronous. Add a `preStop` hook that sleeps 5-15s (matched
  to your proxy's propagation time) so SIGTERM does not arrive while the load balancer is still
  routing new connections. Prefer Kubernetes' native `Sleep` handler, which needs no in-image binary;
  the `exec` form (`["sh", "-c", "sleep 10"]`) requires a shell and a `sleep` binary inside the image,
  which the distroless-style bases recommended in section 3 do not ship — the hook then fails with a
  `FailedPreStopHook` event and the pod terminates immediately, silently losing the very drain the
  hook was added to guarantee. Verify the handler's field shape against your cluster's Pod API
  reference.
- Set `terminationGracePeriodSeconds` to preStop delay + worst-case drain time + 5s headroom. The
  default is 30s; after it expires the container is SIGKILLed.
- Target startup in seconds, not minutes. Slow starts stall rolling updates and autoscaling.

Verify, do not assume:

```bash
docker run -d --name t <image>
docker stop -t 30 t
code=$(docker inspect -f '{{.State.ExitCode}}' t)
docker logs t 2>&1 | grep -q '<your shutdown log line>' \
  || { echo "no drain observed: SIGTERM handler did not run" >&2; exit 1; }
[ "$code" = 0 ] || { echo "exit $code -- 143: killed by the default SIGTERM disposition, no handler installed; 137: SIGKILL after the grace period, signal never reached the process" >&2; exit 1; }
```

A fast `docker stop` is not evidence of a clean drain. An exec-form entrypoint whose app installs no
SIGTERM handler is terminated by the signal's default disposition, exits 143 (128+15) immediately, and
`docker stop` returns at once having dropped every in-flight request. Exit code alone cannot tell that
apart from a real drain, which is why the check asserts both a `0` exit and an observable shutdown log
line.

## 8. Health Checks and Probes

| Signal | Question it answers | Consequence of failure | Depth |
|---|---|---|---|
| Startup probe | "Has initialization finished?" | suspends liveness/readiness until it passes | cheap in-process check |
| Readiness | "Can this instance serve traffic now?" | removed from the load balancer's endpoints | may check required dependencies |
| Liveness | "Is this process wedged beyond recovery?" | container is **restarted** | shallow, dependency-free, in-process only |

- **Never let a downstream dependency fail liveness.** A deep liveness check turns a database blip
  into a cluster-wide restart storm. Put dependency checks in readiness.
- Use a startup probe for slow-initializing apps instead of inflating liveness `initialDelaySeconds`
  or `timeoutSeconds`.
- Set probe timing explicitly. Defaults are `initialDelaySeconds: 0`, `periodSeconds: 10`,
  `timeoutSeconds: 1`, `successThreshold: 1`, `failureThreshold: 3` — a 1s timeout marks
  healthy-but-busy containers as failed. Recommended starting point: `timeoutSeconds: 3`,
  `periodSeconds: 10`, `failureThreshold: 3` for readiness; `failureThreshold: 6` for liveness.
- Handler types: `exec`, `httpGet` (success is HTTP 200-399), `tcpSocket`, `grpc`. Prefer `httpGet`
  on a dedicated route (`/healthz` shallow, `/readyz` with dependencies), gated on real checks
  rather than a fixed `sleep`.
- In a plain Docker/Compose deployment add a `HEALTHCHECK` (or `--health-cmd`) that calls the app's
  own health route with a short bounded command and no downloaded tooling. Set `--health-interval`,
  `--health-timeout`, `--health-retries`, and `--health-start-period` explicitly rather than relying
  on defaults. `--start-period` defaults to `0s`, so without it a slow-starting container is reported
  `unhealthy` throughout normal startup, which then blocks the `service_healthy` Compose gating
  described below. It is the plain-Docker analogue of the startup probe above. **Docker
  itself takes no action on an unhealthy container** — the status is only reported (`docker ps`,
  `docker inspect --format '{{.State.Health.Status}}'`), and restart policies react to exit codes,
  not health. Use `HEALTHCHECK` to gate Compose `depends_on: condition: service_healthy` and to feed
  external monitoring; if you need restart-on-unhealthy, the app must exit non-zero itself or an
  orchestrator must own the decision. The restart and endpoint-removal consequences in the table
  above are Kubernetes behaviour.
- Health endpoints must be unauthenticated but leak nothing: status only, no versions, no connection
  strings, no stack traces.

## 9. Resource Limits

- Set **both requests and limits** for CPU and memory on every container. Requests drive scheduling;
  limits are enforced at runtime. A limit with no request implies an equal request.
- Memory limits are enforced by **OOM kill**; CPU limits are enforced by **throttling**. Size memory
  from observed peak RSS plus headroom; be cautious with tight CPU limits, which produce latency
  spikes rather than errors.
- Measure before you set: run the container under representative load and record your project's own
  peak RSS and CPU baseline in the repo. Do not copy another service's numbers. Docker equivalents:
  `-m 512m --cpus 0.5`.
- For containers running untrusted or user-supplied workloads, also cap process and descriptor
  counts: `--pids-limit 256`, `--ulimit nproc=...`, `--ulimit nofile=...`.
- Use `--restart=on-failure:3` (or a controller's backoff) rather than unbounded restarts; a
  repeating crash-restart (`CrashLoopBackOff`) should page, not loop silently.

## 10. Runtime Hardening

| Control | Docker | Kubernetes |
|---|---|---|
| Non-root | `--user 10001:10001` (image already declares `USER`) | `runAsNonRoot: true`, `runAsUser: 10001` |
| Read-only root filesystem | `--read-only --tmpfs /tmp` | `readOnlyRootFilesystem: true` + `emptyDir` volumes |
| Drop capabilities | `--cap-drop all --cap-add <needed>` | `capabilities: {drop: ["ALL"], add: [...]}` |
| No privilege escalation | `--security-opt=no-new-privileges` | `allowPrivilegeEscalation: false` |
| Never privileged | never `--privileged` | `privileged: false` |
| Syscall filtering | keep the default seccomp profile; add AppArmor/SELinux where supported | `seccompProfile: {type: RuntimeDefault}` |
| Never expose the daemon | never mount `/var/run/docker.sock`; never expose the daemon over TCP; prefer rootless mode | no `hostPath` on the socket |
| Network exposure | publish to a specific interface (`-p 127.0.0.1:8000:8000`); use user-defined networks, not the default bridge | Services + NetworkPolicy; do not use `hostNetwork` |
| Volumes | mount read-only where possible (`:ro`) | `readOnly: true` on volumeMounts |

Docker's published ports can bypass host firewall rules, so binding `0.0.0.0` on a public host
silently exposes the service. `--read-only` needs a `tmpfs` for `/tmp` and every other path the
runtime writes to, or the container crashes at startup — smoke test the hardened configuration in CI
rather than shipping it untested.

## 11. Tagging, Labels, and Provenance

- Tag every image with an immutable, traceable identifier. Minimum set: `<repo>:<git-sha>` always,
  plus `<repo>:<semver>` for releases. Optionally a moving `:main` for convenience, never for
  deployment.
- **Deploy the digest or an immutable tag.** In Kubernetes an omitted `imagePullPolicy` defaults to
  `Always` for `:latest` or for an omitted tag, and to `IfNotPresent` for any other tag or for a
  digest reference. Either way a mutable tag means nodes
  can run different code under one name — and with `IfNotPresent` a node that already cached the tag
  never picks up the new content. Deploy a digest and the question disappears.
- Stamp OCI pre-defined annotation labels so any consumer can trace the running image back to a
  commit without external bookkeeping:

```dockerfile
# Non-secret build args only — anything in section 5 must never travel this way.
ARG GIT_SHA
ARG VERSION
ARG BUILD_DATE
LABEL org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.revision="$GIT_SHA" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.title="payments-api" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.base.name="python:3.12-slim" \
      org.opencontainers.image.base.digest="sha256:..."
```

Declare the `ARG`s or the values expand to empty strings and trip the `UndefinedVar` check that the CI
gates fail on. CI supplies them:
`--build-arg GIT_SHA=$(git rev-parse HEAD) --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)`.
Alternatively `docker buildx build --label org.opencontainers.image.revision=...` sets them without a
Dockerfile edit. Never hardcode a version or timestamp in the Dockerfile — it goes stale on the next
build. Put the `LABEL` in the **last** layer so per-build values do not bust the cache.

- Generate SBOM and provenance attestations with the build (see section 12 for the command).
  Attestations attach to the image index. Pushing to a registry always preserves them; `--load`
  preserves them only when the daemon uses the **containerd image store**, and the `docker` driver
  requires that store for attestations at all — the `docker-container`, `kubernetes` and `remote`
  drivers do not. Verify with
  `docker buildx imagetools inspect <image> --format '{{ json .Provenance }}'`.
- Sign released images and verify signature plus policy at admission, pulling only from your own
  trusted registry. Tool choice (Sigstore/cosign, Notation, Docker Content Trust) is
  environment-dependent; pick one and enforce it in the admission path.

## 12. CI Gates

Every gate must fail the pipeline, not print a warning. Check each tool's own `--help` before
pasting; flags change.

```bash
set -euo pipefail   # without this a failing gate below is only a message in the log

docker build --check .                      # checks only, no image; exits non-zero if any violation is reported
hadolint Dockerfile                         # lint: last USER not root (DL3002), pinned versions, no ADD
gitleaks dir .                              # no secrets in the build context (the deprecated form was `gitleaks detect --no-git`)

# Provision the builder explicitly: attestations and the registry cache need a non-default
# driver, or the containerd image store on the `docker` driver (sections 4 and 11).
docker buildx create --use --name ci --driver docker-container

# One build, and it is the one that ships. The build arg escalates check warnings to
# failures here too; a Dockerfile carrying `# check=error=true` needs no build arg at all.
docker buildx build --build-arg "BUILDKIT_DOCKERFILE_CHECK=error=true" \
  --cache-from "type=registry,ref=$REPO:buildcache" \
  --cache-to "type=registry,ref=$REPO:buildcache,mode=max" \
  --sbom=true --provenance=mode=max --push -t "$REPO:$GIT_SHA" .
docker pull "$REPO:$GIT_SHA"                # --push keeps attestations; pull it back for the local-store gates below

trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed "$REPO:$GIT_SHA"
trivy image --scanners secret --exit-code 1 "$REPO:$GIT_SHA"   # secret scanning is on by default for `trivy image`; this isolates it as its own failing gate
docker scout cves --exit-code --only-severity critical,high "$REPO:$GIT_SHA"   # gate: exit 2 on findings
docker scout quickview "$REPO:$GIT_SHA"     # informational only: quickview has no --exit-code, it never fails the build

test -n "$(docker image inspect --format '{{.Config.User}}' "$REPO:$GIT_SHA")"   # this, not hadolint, is what proves a USER was declared at all
docker image inspect --format '{{.Config.User}}' "$REPO:$GIT_SHA" \
  | grep -Eq '^[1-9][0-9]*(:[0-9]+)?$'      # ...and that it is a non-zero numeric UID, as agent rule 3 requires

# Contents, not history: history records instruction text and ARG values, never file contents,
# so only a file listing can prove a `COPY . .` did not sweep in `.env` or `.git`.
files=$(mktemp)
cid=$(docker create "$REPO:$GIT_SHA")
docker export "$cid" | tar -tf - > "$files"
docker rm "$cid"
if grep -Eiq '(^|/)(\.env($|\.)|\.git/|\.npmrc|\.netrc|\.aws/|id_(rsa|dsa|ecdsa|ed25519)$)|\.(pem|key|p12|pfx|jks)$' "$files"; then
  echo "sensitive file shipped inside the image" >&2; exit 1
fi
hist=$(mktemp)
docker history --no-trunc --format '{{.CreatedBy}}' "$REPO:$GIT_SHA" > "$hist"   # a broken producer aborts here under set -e
if grep -Eiq '^(ARG|ENV) [^=]*(secret|token|password|api[_-]?key)[^=]*=' "$hist"; then
  echo "possible credential baked into ARG/ENV" >&2; exit 1
fi

# Hardened-runtime smoke test: the app must actually bind and serve under the flags.
cid=$(docker run -d -p 127.0.0.1:18000:8000 --read-only --tmpfs /tmp --cap-drop all \
  --security-opt=no-new-privileges --pids-limit 256 -m 512m --cpus 0.5 \
  "$REPO:$GIT_SHA")
trap 'docker rm -f "$cid" >/dev/null 2>&1' EXIT
for _ in $(seq 30); do
  curl -fsS http://127.0.0.1:18000/healthz >/dev/null && break || sleep 1
done
curl -fsS http://127.0.0.1:18000/healthz >/dev/null   # served a request with a read-only root and only /tmp writable
[ "$(docker inspect -f '{{.State.Running}}' "$cid")" = true ]   # still up under the hardened flags
```

`BUILDKIT_DOCKERFILE_CHECK` is a **build argument**, not an environment variable, and the value is
`error=true` — `BUILDKIT_DOCKERFILE_CHECK=error docker build .` sets an unused shell variable and the
build succeeds with warnings. The in-Dockerfile equivalent, and the better default because it travels
with the file, is the directive `# check=error=true` on the line after `# syntax=docker/dockerfile:1`.
`docker build --check` already exits non-zero on violations by itself; `error=true` is what makes the
build that actually produces the image fail too. Put the build arg on the build that pushes the
artifact, never on a throwaway build whose image is discarded — escalating checks on an image you do
not ship proves nothing about the one you do, and building the same Dockerfile twice per pipeline run
doubles the cost for no coverage.

Write every gate as `if <command>; then exit 1; fi` over output you have already materialised. Bash
exempts `!`-negated commands from `set -e`, so `! cmd | grep -q ...` does not abort the script; it only
happens to leave a non-zero status if it is the last line of the block, and any gate appended after it
silences it. Worse, under `pipefail` a negated pipeline turns a *broken* command — an unset `$REPO`, an
image not present locally — into a pass. The `if` form removes the `!` errexit exemption, but a
pipeline inside an `if` condition is still exempt from `set -e`, so a broken producer inside the
condition passes exactly as it would under `!`. Run the producer as its own statement, redirect to a
file, then test the file — which is why both content gates above write to `$files` and `$hist` first.
The same reasoning applies to the hardened-runtime smoke test: it must reach the state where the app has bound its port and written its first log line, or it
proves nothing about writable-path requirements. Invoking the image with `--version` short-circuits
before the runtime opens any log, pid, or cache path, so a missing `tmpfs` mount sails through, and it
assumes a `--version` flag the canonical entrypoint above does not document.

Named `docker build --check` rules worth knowing: `SecretsUsedInArgOrEnv`, `JSONArgsRecommended`,
`WorkdirRelativePath`, `CopyIgnoredFile`, `UndefinedVar`, `LegacyKeyValueFormat`,
`MaintainerDeprecated`, `StageNameCasing`, `FromAsCasing`. The set grows with BuildKit releases —
read the current reference rather than assuming a fixed list. Note what `CopyIgnoredFile` actually
means: it fires when a `COPY`/`ADD` targets a path your `.dockerignore` excludes — an over-broad
ignore pattern is silently breaking a copy. **No build check detects a missing or under-broad
`.dockerignore`**, so it is not evidence that secrets are excluded from the context.

Scope the history gate to `ARG`/`ENV` assignments. A `RUN` that consumes a file-mounted secret
necessarily has `--mount=type=secret` and `/run/secrets/<id>` in its history entry, so an unanchored
case-insensitive match over full history fails the very pattern section 5 requires.

`docker scout cves --exit-code` returns exit code 2 when vulnerabilities are detected, which is what
makes it a gate. `docker scout quickview` has no `--exit-code` flag: it summarises the policy areas
(non-root default user, fixable critical/high, base image currency, attestations present) and exits 0
either way, so keep it as informational output beside the gate and never as the gate.

Manifest and cluster gates: `kubesec scan` or `kubeaudit` for `runAsNonRoot`,
`readOnlyRootFilesystem`, `allowPrivilegeEscalation`, dropped capabilities and resource limits;
`conftest test k8s/` (OPA) to block images without a digest or missing probes/limits;
`docker-bench-security` and `kube-bench` for CIS Benchmark conformance on hosts and clusters.

`--ignore-unfixed` is the pragmatic default so the gate stays actionable, but review the unfixed set
on a schedule. Every suppression carries an expiry date and an owner.

## 13. Deployment and Rollback

- Roll out through a controller with a surge-and-drain strategy. Never mutate a bare Pod or patch a
  running container in place; only a controller can reschedule and step a change out gradually while
  readiness gates traffic.
- A Deployment rollout triggers only on `.spec.template` changes (an image tag or digest change
  counts); scaling does not roll.
- Set `maxSurge` and `maxUnavailable` explicitly rather than relying on defaults. Safe starting
  point for a stateless HTTP service: `maxSurge: 25%`, `maxUnavailable: 0`.
- Set `minReadySeconds` above zero (10-30s) so a pod that crashes shortly after becoming ready does
  not let the rollout continue.
- Bound failure with `progressDeadlineSeconds`, keep `revisionHistoryLimit` large enough to roll
  back more than one release, and apply manifests from version control rather than a local file.
- Rollback must be one command, documented in the runbook:

```bash
kubectl rollout status  deployment/<name> --timeout=5m
kubectl rollout history deployment/<name>
kubectl rollout undo    deployment/<name> --to-revision=<n>
```

- **Migrations must be backward compatible or the rollback command is unusable.** Use
  expand/contract: add the new column/table, deploy code that writes both and reads the new,
  backfill as a separate idempotent job, then contract in a later release. Never drop or rename in
  the same release that stops using it.
- Run migrations as a separate one-off process (a Job using the same image and config), never from
  the app's startup path — otherwise N replicas race and a failed migration becomes a crash loop.
- Promote a digest that already passed the gates in a lower environment; do not rebuild for
  production.

## 14. AI Agent Rules

When writing or modifying container, deployment, or CI files, the agent **must**:

1. **Read the existing Dockerfile, `.dockerignore`, CI workflow, and manifests first** and match
   their patterns, base images, and naming. The repo's convention beats this document.
2. **Never write a secret into a Dockerfile, image layer, `ENV`, build arg, or committed manifest.**
   Use `RUN --mount=type=secret` at build and injected env/mounted files at run, and say in the
   summary where the value must come from.
3. **Always end the final stage with a `USER` naming a non-root numeric UID**, and create that user
   and group explicitly in the Dockerfile.
4. **Always pin base images by digest** in production Dockerfiles. If you do not have the digest,
   leave a clearly marked placeholder and tell the user to resolve it — never invent a `sha256`
   value.
5. **Never emit `:latest`** in a deploy manifest, Compose file, or CI deploy step.
6. **Create or update `.dockerignore` in the same change** as any new Dockerfile.
7. **Use exec-form `ENTRYPOINT`/`CMD`**, and end any entrypoint script with `exec "$@"`.
8. **Add or verify SIGTERM handling** whenever you touch the server or worker entrypoint; if the app
   has none, say so explicitly rather than assuming the platform handles it.
9. **Order layers for cache reuse:** dependency manifests and install before source copy. Never
   `COPY . .` before dependency installation.
10. **Set requests, limits, and explicit probe timings** on every container you add; do not leave
    probe defaults implicit.
11. **Never mount the Docker socket, never use `--privileged`**, and never disable seccomp to make
    something work — report the blocker instead.
12. **Do not weaken a gate to get green.** No `|| true`, no `--severity` downgrades, no blanket
    ignore files. Fix the finding or escalate it with the scanner output.
13. **Never claim a build, scan, or deploy succeeded without running it** and pasting the real
    output. If you cannot run it in this environment, say so.
14. **Never invent version numbers, digests, CVE IDs, image sizes, or tool flags.** If a flag or
    default is uncertain, say it must be checked against the tool's `--help` or current docs.
15. **Ship the rollback story with the deploy change:** how to identify the previous artifact and
    the exact command to restore it, plus whether the migration is reversible.
16. **Flag every security-relevant change** (user, capabilities, mounted paths, published ports,
    network policy, secret handling) in the summary.
17. **Keep changes minimal.** No drive-by base image bumps, no reformatting unrelated manifests, no
    new dependencies or tools without saying why.

## 15. Review Checklist

For an AI reviewer. Flag only real defects; cite `file:line` and state the failure scenario.

**Secrets** — any secret in `ARG`, `ENV`, a `COPY`ed file, a `RUN` command line, or a committed
manifest? Build secrets using `--mount=type=secret`? Does `docker history` contain a token, and does
the image's **file listing** contain `.env`, `.git`, `.npmrc`, or a key file (history alone cannot
answer this)? Is a secret scanner running in CI? Is rotation possible without a rebuild?

**Image identity** — base image pinned by digest? Package versions and lockfiles pinned? Deploy
referencing an immutable tag or digest rather than `:latest` or a branch tag? OCI provenance labels
present and accurate? SBOM and provenance attestations produced and pushed?

**Build hygiene** — multi-stage with no toolchain or dev dependencies in the final stage? Dependency
install before source copy? `apt-get update` and `install` in one `RUN` with the lists cleaned?
`.dockerignore` committed and covering `.git`, `.env`, keys, and `node_modules`? `COPY` used instead
of `ADD` for local files, with a checksum on any remote fetch? Absolute `WORKDIR`? No recursive
`chown` layer? One concern per image?

**Runtime identity and hardening** — `USER` present with a non-root numeric UID, after every step
needing root? Read-only root filesystem with `tmpfs` for the paths actually written? All
capabilities dropped and only the needed ones added? `no-new-privileges` set? Nothing `privileged`?
Docker socket unmounted? Ports bound to a specific interface?

**Process lifecycle** — exec-form `ENTRYPOINT`/`CMD`? Entrypoint script ends with `exec`? SIGTERM
handler that stops intake, drains, and exits? Workers NACK in-flight jobs and are idempotent?
`terminationGracePeriodSeconds` longer than worst-case drain? `preStop` delay where the proxy
removes endpoints asynchronously, and can the image actually execute the `preStop` handler it declares
(an `exec` sleep needs a shell and `sleep` in the image)? Does the container exit 0 after emitting its
shutdown log line — not 143 (no handler) and not 137 (SIGKILL after the grace period)?

**Health and resources** — separate liveness and readiness? Liveness shallow and free of downstream
dependencies? Startup probe for slow init? Probe timeouts raised above the 1s default? Requests
**and** limits set for CPU and memory, derived from a measurement? Restart policy bounded?

**Configuration and logs** — all config from the environment, one image across environments? Nothing
stateful on the container filesystem? Logs unbuffered structured lines on stdout/stderr, with no
in-container log files or rotation? Nothing sensitive in the log stream or the health endpoint?

**CI gates** — `docker build --check` and a Dockerfile linter running and failing the build?
Vulnerability scan failing on fixable HIGH/CRITICAL rather than reporting only? Is every gate written
so it cannot fail open — `if cmd; then exit 1; fi` rather than a `!`-negated pipeline that `set -e`
ignores and that turns a broken command into a pass? Hardened-runtime smoke test present, and does it
reach a real serving state rather than printing a version? Is the escalated-checks flag on the build
that actually ships? Any suppression carrying an owner and an expiry? Images pulled only from a
trusted registry, with signature/policy verification at admission?

**Deployment and rollback** — rollout via a controller with explicit `maxSurge`/`maxUnavailable`
and `minReadySeconds`? Manifests in version control? Rollback documented as a single command with
retained revision history? Migrations backward compatible and run as a separate one-off job rather
than at app startup? Is the previously deployed artifact still identifiable and pullable?

## References

Sources for every rule above are documented in the upstream repo:
https://github.com/Madheshvivekanandan/ai-engineering-skills (skills/docker-deployment-best-practices/references/sources.md).
