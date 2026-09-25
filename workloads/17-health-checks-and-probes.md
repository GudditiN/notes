---
description: "Teaching Kubernetes the difference between \"running\" and \"working\"."
icon: heart-pulse
---

# 17. Health checks and probes

{% hint style="info" %}
**Level:** Intermediate · **Part:** Running real workloads
{% endhint %}

## Simple explanation

A process can be running but broken: deadlocked, still loading, or unable to reach its database. **Probes** let the kubelet ask your app how it's doing and act on the answer.

| Probe | Question it asks | On failure |
| --- | --- | --- |
| **startupProbe** | Has the app finished booting? | Keeps waiting until `failureThreshold × periodSeconds`, then restarts. Liveness/readiness are paused until it passes. |
| **readinessProbe** | Can it serve traffic *right now*? | Pod removed from Service endpoints. **Not restarted.** |
| **livenessProbe** | Is it stuck beyond recovery? | Container is **restarted**. |

## Key concepts

| Concept | What it means |
| --- | --- |
| Probe handlers | `httpGet` (2xx/3xx = healthy), `tcpSocket`, `exec` (exit 0 = healthy), `grpc`. |
| Timing fields | `initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`, `failureThreshold`, `successThreshold`. |
| Graceful shutdown | On termination Kubernetes sends SIGTERM, removes the Pod from endpoints, waits `terminationGracePeriodSeconds` (default 30), then SIGKILL. |
| preStop hook | A command run before SIGTERM; a short `sleep` lets load balancers stop sending traffic first. |

## Flow

<figure><img src="../.gitbook/assets/m10-diagram-1.svg" alt="Health checks and probes: Flow"><figcaption></figcaption></figure>

## Design your endpoints well

- `/healthz` (liveness): only checks the process itself. Returns 200 if the event loop/threads respond. **Never check the database here** — a DB outage would restart every Pod in a loop and make things worse.
- `/ready` (readiness): checks dependencies needed to serve requests (DB connection pool, cache warm). Failing temporarily is fine.

## YAML example

{% code title="probes.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: probed }
spec:
  replicas: 2
  selector: { matchLabels: { app: probed } }
  template:
    metadata: { labels: { app: probed } }
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: web
          image: nginx:1.27
          ports: [{ name: http, containerPort: 80 }]
          startupProbe:
            httpGet: { path: /, port: http }
            periodSeconds: 5
            failureThreshold: 24          # up to 2 minutes to boot
          readinessProbe:
            httpGet: { path: /, port: http }
            periodSeconds: 5
            timeoutSeconds: 2
            failureThreshold: 3
          livenessProbe:
            httpGet: { path: /, port: http }
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3           # restart after ~30s of failure
          lifecycle:
            preStop:
              exec: { command: ["sh", "-c", "sleep 5"] }   # drain before SIGTERM
---
# exec and tcp probe variants
# livenessProbe:
#   exec: { command: ["pg_isready", "-U", "postgres"] }
# readinessProbe:
#   tcpSocket: { port: 6379 }
```
{% endcode %}

## Important commands

```bash
kubectl describe pod POD | grep -A3 -E "Liveness|Readiness|Startup"
kubectl get events --field-selector reason=Unhealthy --sort-by=.lastTimestamp
kubectl get pods -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply `probes.yaml` with a Service in front. Break readiness on one Pod: `kubectl exec POD -- rm /usr/share/nginx/html/index.html`. It goes `0/1` and disappears from `kubectl get endpointslices`, but the restart count stays 0… until liveness also fails and it restarts (both use `/`). Point readiness at `/` and liveness at `/50x.html` to separate them, and repeat.
{% endstep %}
{% step %}
Set `startupProbe.failureThreshold: 1` with an image that takes 20 s to start (`command: ["sh","-c","sleep 20; nginx -g 'daemon off;'"]`) and watch the restart loop. Fix with a bigger budget.
{% endstep %}
{% step %}
Run a load test (`kubectl run load --image=busybox:1.36 --rm -it -- sh -c 'while true; do wget -qO- http://probed; done'`) while doing `kubectl rollout restart deploy/probed`. With probes and preStop, you see no errors.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Liveness checks dependencies** → cascading restarts during a DB blip. Keep liveness shallow.
- **No startupProbe on slow apps (JVM, Rails)** → liveness kills them before they finish booting. Use startupProbe instead of a huge `initialDelaySeconds`.
- **Timeouts too tight** — a 1 s timeout under GC pause or load triggers false restarts. Start with 2–5 s.
- **No readiness probe** — new Pods receive traffic before they can serve it, causing errors on every deploy.
- **App ignores SIGTERM** — in-flight requests are cut after 30 s. Handle SIGTERM (NestJS: `app.enableShutdownHooks()`; FastAPI/uvicorn does this by default) and make PID 1 your app, not a shell script.
