---
description: "Package your own application as an image that is small, fast to build and safe to run."
icon: file-lines
---

# 3. Images and Dockerfiles

{% hint style="info" %}
**Level:** Beginner → Intermediate · **Part:** Docker essentials
{% endhint %}

## Simple explanation

A **Dockerfile** is a recipe. Each line is an instruction: start from a base image, copy files, run commands, set the start command. `docker build` executes it and produces an image. Every instruction that changes files creates a **layer**, and Docker caches layers: if nothing a step depends on has changed, the step is skipped. Ordering your Dockerfile well is the difference between 3-second and 3-minute builds.

## Architecture: layers and cache

<figure><img src="../.gitbook/assets/image-layers.svg" alt="Images and Dockerfiles: Architecture: layers and cache"><figcaption><p>Each filesystem instruction adds a cached layer. Change main.py and only layer 5 rebuilds; change requirements.txt and layers 3–5 rebuild. That's why dependency files are copied before source code.</p></figcaption></figure>

## Key concepts

| Instruction | What it does | Tip |
| --- | --- | --- |
| `FROM` | Base image to build on | Prefer `-slim`, `-alpine` or distroless; pin a version |
| `WORKDIR` | Sets and creates the working directory | Use absolute paths like `/app` |
| `COPY` | Copies files from the build context | Copy dependency manifests first, source last |
| `RUN` | Runs a command at build time, creating a layer | Chain related commands with `&&` and clean caches in the same step |
| `ENV` | Sets environment variables for build and runtime | Never put secrets here |
| `ARG` | Build-time variable (`--build-arg`) | Visible in image history; not for secrets |
| `EXPOSE` | Documents the port the app listens on | Doesn't publish anything; `-p` does |
| `USER` | Switches to a non-root user | Always set one for the final stage |
| `ENTRYPOINT` / `CMD` | The executable and its default arguments | Use exec form `["app", "arg"]` so signals reach your app |
| `HEALTHCHECK` | Command Docker runs to test health | Kubernetes ignores it; it uses probes instead |

| Concept | What it means |
| --- | --- |
| Build context | The folder you pass to `docker build` (usually `.`). Everything in it is sent to the builder, so exclude junk with `.dockerignore`. |
| Multi-stage build | Several `FROM` stages in one file: compile in a big image, copy only the result into a small runtime image. |
| Tag vs digest | Tags like `1.4.0` can be moved; digests like `@sha256:…` never change. |
| Multi-platform | `docker buildx build --platform linux/amd64,linux/arm64` builds for Intel servers and Apple Silicon / Graviton at once. |

## Example 1: a Python API

{% code title="hello-api/main.py" %}
```python
from fastapi import FastAPI
import os, socket

app = FastAPI()

@app.get("/")
def root():
    return {"message": os.getenv("GREETING", "hello"), "host": socket.gethostname()}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```
{% endcode %}

{% code title="hello-api/requirements.txt" %}
```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
```
{% endcode %}

{% code title="hello-api/Dockerfile" %}
```docker
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# 1. dependencies first: this layer is reused until requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. source code last: edits only rebuild from here
COPY main.py .

RUN useradd --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
{% endcode %}

{% code title="hello-api/.dockerignore" %}
```text
__pycache__/
*.pyc
.venv/
.env
.git/
```
{% endcode %}

```bash
cd hello-api
docker build -t hello-api:1.0.0 .
docker run --rm -p 8000:8000 -e GREETING="hi from a container" hello-api:1.0.0
curl localhost:8000
```

## Example 2: a NestJS / Node.js API with a multi-stage build

{% code title="Dockerfile (NestJS)" %}
```docker
# ---- build stage: full toolchain ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

# ---- runtime stage: only what's needed to run ----
FROM node:20-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
COPY --from=build --chown=node:node /app/package.json ./
USER node
EXPOSE 3000
CMD ["node", "dist/main.js"]
```
{% endcode %}

{% hint style="success" %}
**Why multi-stage matters**

The build stage holds compilers, dev dependencies and source code, often over 1 GB. The runtime image carries only compiled output and production dependencies, typically under 200 MB, with fewer packages for attackers to exploit.
{% endhint %}

## Important commands

```bash
docker build -t myapp:1.0.0 .                 # build and tag
docker build --no-cache -t myapp:1.0.0 .      # ignore the cache
docker build --progress=plain .               # see every step's output
docker image ls                               # list images and sizes
docker history myapp:1.0.0                    # layers and their sizes
docker tag myapp:1.0.0 ghcr.io/gudditin/myapp:1.0.0
docker image prune                            # remove dangling images
docker builder prune                          # clear build cache
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:1.0.0 .   # multi-arch
```

## Hands-on exercises

{% stepper %}
{% step %}
Build `hello-api`, run it, and curl it. Note the build time.
{% endstep %}
{% step %}
Change the greeting in `main.py` and rebuild. Only the last layers run (look for `CACHED`).
{% endstep %}
{% step %}
Move `COPY main.py .` above the `pip install` step, change `main.py` again, and rebuild. Watch dependencies reinstall. Put it back.
{% endstep %}
{% step %}
Compare sizes: build the same app `FROM python:3.12` and `FROM python:3.12-slim`, then check `docker image ls`.
{% endstep %}
{% step %}
Run `docker history hello-api:1.0.0` and find the largest layer.
{% endstep %}
{% step %}
Stop the container with `docker stop` and time it. Then change CMD to the shell form `CMD uvicorn main:app --host 0.0.0.0`, rebuild, and time it again.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`COPY . .` before installing dependencies** — every code edit reinstalls everything. Copy manifests first.
- **Secrets baked into the image** — via `ENV`, `ARG` or a copied `.env`. Anyone with the image can read them from its layers. Use runtime env vars or BuildKit secrets (Module 7).
- **Running as root** — add a `USER`. Kubernetes security policies will reject root containers later.
- **Shell-form CMD** — `CMD npm start` runs under `/bin/sh`, which doesn't forward SIGTERM. Use exec form and start the app directly, not through `npm`.
- **Huge build context** — “Sending build context 1.2GB” means `node_modules` or `.git` is included. Add a `.dockerignore`.
- **`exec format error` on the server** — you built on an Apple Silicon Mac (arm64) for an amd64 server. Build with `--platform linux/amd64` or multi-arch.
- **Relying on `latest`** — it isn't “newest”, just a default tag. Pin versions for bases and your own images.
