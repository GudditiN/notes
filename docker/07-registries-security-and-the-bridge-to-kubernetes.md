---
description: "Ship images safely, then see exactly what Kubernetes adds on top of Docker."
icon: shield
---

# 7. Registries, image security, and the bridge to Kubernetes

{% hint style="info" %}
**Level:** Intermediate · **Part:** Docker essentials
{% endhint %}

## Simple explanation

To run your image anywhere other than your laptop, you push it to a **registry**. Docker Hub is public by default; for company work you'll use a private registry such as **Amazon ECR** or **GitHub Container Registry (GHCR)**. Whatever you push will run in production, so this is also where image security happens: minimal base images, non-root users, vulnerability scans and no secrets inside.

Once an image is in a registry, Kubernetes can pull it onto any node. This module closes Part 1 by mapping every Docker and Compose idea you've learned to its Kubernetes equivalent.

## Key concepts

| Concept | What it means |
| --- | --- |
| Registry / repository / tag | `123456789012.dkr.ecr.ap-south-1.amazonaws.com/api:3f9c2ab` is registry / repository : tag. |
| Digest | `api@sha256:…` identifies exact image bytes. Use digests when you must guarantee what runs. |
| Credential helpers | `docker-credential-ecr-login` and friends fetch short-lived tokens instead of storing passwords. |
| Vulnerability scanning | Trivy or Docker Scout list known CVEs in OS packages and libraries. |
| SBOM | Software bill of materials: a list of everything in the image (`docker buildx build --sbom=true`). |
| Signing | `cosign sign` lets clusters verify an image came from your pipeline. |
| BuildKit secrets | `RUN --mount=type=secret` makes a token available to one build step without storing it in any layer. |
| Minimal bases | `-slim`, `-alpine`, distroless and Chainguard images ship fewer packages, so fewer CVEs. |

## Important commands

```bash
# GitHub Container Registry
echo "$GITHUB_TOKEN" | docker login ghcr.io -u gudditin --password-stdin
docker tag hello-api:1.0.0 ghcr.io/gudditin/hello-api:1.0.0
docker push ghcr.io/gudditin/hello-api:1.0.0

# Amazon ECR
aws ecr create-repository --repository-name hello-api --image-scanning-configuration scanOnPush=true
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-south-1.amazonaws.com
docker tag hello-api:1.0.0 123456789012.dkr.ecr.ap-south-1.amazonaws.com/hello-api:1.0.0
docker push 123456789012.dkr.ecr.ap-south-1.amazonaws.com/hello-api:1.0.0

# build for Intel and ARM servers and push in one go
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/gudditin/hello-api:1.0.0 --push .

# scan
trivy image --severity HIGH,CRITICAL hello-api:1.0.0
docker scout cves hello-api:1.0.0
```

## Example: using a secret at build time without leaking it

{% code title="Dockerfile" %}
```docker
# syntax=docker/dockerfile:1
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
COPY . .
USER node
CMD ["node", "dist/main.js"]
```
{% endcode %}

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t app:1.0.0 .
```

## Example: run a container the hardened way

```bash
docker run -d --name api \
  --user 10001 \
  --read-only --tmpfs /tmp \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --memory 256m --cpus 0.5 \
  -p 8000:8000 hello-api:1.0.0
```

Every flag here has a Kubernetes twin in a Pod's `securityContext` and `resources` (Modules 15 and 18).

## Example: build and push from GitHub Actions

{% code title=".github/workflows/image.yaml" %}
```yaml
name: image
on:
  push:
    branches: [main]
permissions:
  contents: read
  packages: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```
{% endcode %}

## The bridge: why Kubernetes?

Docker and Compose run containers on *one* machine. Real production needs more than that:

<table data-view="cards"><thead><tr><th></th><th></th></tr></thead><tbody><tr><td><strong>Many machines</strong></td><td>Spread containers across a fleet and keep running when a machine dies.</td></tr><tr><td><strong>Self-healing</strong></td><td>Restart, reschedule and replace containers automatically, forever.</td></tr><tr><td><strong>Safe rollouts</strong></td><td>Replace versions gradually, only when health checks pass, with one-command rollback.</td></tr><tr><td><strong>Scaling</strong></td><td>Add and remove copies based on CPU, queue length or schedule.</td></tr><tr><td><strong>Service discovery</strong></td><td>Stable names and load balancing across copies, wherever they run.</td></tr><tr><td><strong>Desired state</strong></td><td>Declare what you want in files; the cluster keeps reality matching them.</td></tr></tbody></table>

<figure><img src="../.gitbook/assets/docker-to-kubernetes.svg" alt="Registries, image security, and the bridge to Kubernetes: The bridge: why Kubernetes?"><figcaption><p>Everything up to the registry is Docker. Kubernetes takes over from there: it pulls the same image and runs, heals and scales it across a fleet of machines.</p></figcaption></figure>

| Docker / Compose | Kubernetes | Module |
| --- | --- | --- |
| `docker run` one container | Pod | 11 |
| Compose service with several copies | Deployment + ReplicaSet | 11 |
| `ports:` / `-p` | Service (ClusterIP, LoadBalancer) and Ingress | 12, 16 |
| Network DNS by service name | Service DNS (`api.namespace.svc`) | 12 |
| `environment:` / `env_file` | ConfigMap and Secret | 13 |
| Named volume | PersistentVolumeClaim | 14 |
| `--memory`, `--cpus` | requests and limits | 15 |
| `healthcheck` + `depends_on` | readiness, liveness and startup probes | 17 |
| `--user`, `--cap-drop`, `--read-only` | securityContext and Pod Security | 18 |
| `docker compose up` | `kubectl apply` / Helm | 10, 19 |
| `restart: unless-stopped` | Controllers that reconcile desired state | 8 |

## Hands-on exercises

{% stepper %}
{% step %}
Push `hello-api` to GHCR (or ECR) and pull it back on another machine or after `docker image rm`.
{% endstep %}
{% step %}
Scan it with Trivy. Rebuild on a different base (for example `python:3.12-alpine` or a distroless image) and compare the CVE counts.
{% endstep %}
{% step %}
Run it with the hardened flags above. If it fails, read the error and add only the mount or permission it needs.
{% endstep %}
{% step %}
Take the Compose file from Module 6 and write, next to each line, the Kubernetes object that replaces it. Keep the list: you'll build those objects in the capstone.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`denied: requested access to the resource is denied`** — not logged in, the repository doesn't exist (ECR needs it created first), or the token lacks push rights.
- **Only pushing `latest`** — you can't tell what's running or roll back. Tag with the git SHA and a version.
- **Leaving CI credentials behind** — `docker login` stores them in `~/.docker/config.json`. Use OIDC and short-lived tokens in pipelines.
- **Accidentally public images** — new GHCR packages from personal accounts can be public. Check visibility.
- **Ignoring scan results forever** — fail builds on CRITICAL, rebuild regularly to pick up patched base images.
- **`exec format error` on Kubernetes nodes** — architecture mismatch. Build multi-arch images.
