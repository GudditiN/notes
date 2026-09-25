---
description: "Seeing inside the cluster, and a repeatable method for fixing what's broken."
icon: chart-line
---

# 21. Monitoring and troubleshooting

{% hint style="info" %}
**Level:** Intermediate → Advanced · **Part:** Operating in production
{% endhint %}

## Simple explanation

Observability has three pillars: **metrics** (numbers over time — CPU, request rate, error rate), **logs** (what happened, line by line), and **traces** (one request's path across services). The standard open-source stack is **Prometheus** (metrics) + **Grafana** (dashboards) + **Alertmanager** (alerts), with **Loki** or CloudWatch for logs and OpenTelemetry for traces. The `kube-prometheus-stack` Helm chart installs the metrics side in one command.

## Key concepts

| Concept | What it means |
| --- | --- |
| Prometheus | Scrapes `/metrics` endpoints every N seconds and stores time series. |
| ServiceMonitor | A CRD telling the Prometheus Operator which Services to scrape. |
| kube-state-metrics | Exposes object state as metrics (desired vs available replicas, Pod phase, restarts). |
| node-exporter | Node-level CPU, memory, disk, network. |
| PromQL | Query language, e.g. `rate(http_requests_total[5m])`. |
| Golden signals | Latency, traffic, errors, saturation — alert on these, not on CPU alone. |
| Events | Short-lived (1 h) records of what Kubernetes did. First place to look. |

## Architecture

<figure><img src="../.gitbook/assets/m14-diagram-1.svg" alt="Monitoring and troubleshooting: Architecture"><figcaption></figcaption></figure>

## Install the monitoring stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.adminPassword=admin123
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
# open http://localhost:3000 → admin / admin123 → Dashboards → "Kubernetes / Compute Resources / Namespace (Pods)"
```

{% code title="servicemonitor.yaml" %}
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp
  labels:
    release: monitoring            # must match the Helm release name so Prometheus picks it up
spec:
  selector:
    matchLabels: { app: myapp }
  endpoints:
    - port: http                   # named port on the Service
      path: /metrics
      interval: 30s
```
{% endcode %}

{% code title="alert-rule.yaml" %}
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp-alerts
  labels: { release: monitoring }
spec:
  groups:
    - name: myapp
      rules:
        - alert: PodCrashLooping
          expr: increase(kube_pod_container_status_restarts_total{namespace="prod"}[15m]) > 3
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "{{ $labels.pod }} is restarting repeatedly"
        - alert: HighErrorRate
          expr: |
            sum(rate(http_requests_total{job="myapp",status=~"5.."}[5m]))
              / sum(rate(http_requests_total{job="myapp"}[5m])) > 0.05
          for: 10m
          labels: { severity: warning }
```
{% endcode %}

## The troubleshooting method

Work from the outside in. Most problems are found in the first three steps.

<figure><img src="../.gitbook/assets/m14-diagram-2.svg" alt="Monitoring and troubleshooting: The troubleshooting method"><figcaption></figcaption></figure>

| Tool | Command |
| --- | --- |
| Recent cluster events | `kubectl get events -A --sort-by=.lastTimestamp \| tail -30` |
| Why is it Pending/failing? | `kubectl describe pod POD` |
| Crash output | `kubectl logs POD --previous` |
| All Pods of a Deployment | `kubectl logs deploy/api --all-containers -f --since=10m` |
| Exit code / reason | `kubectl get pod POD -o jsonpath='{.status.containerStatuses[0].lastState}'` |
| Debug a distroless container | `kubectl debug -it POD --image=nicolaka/netshoot --target=CONTAINER` |
| Debug a node | `kubectl debug node/NODE -it --image=busybox:1.36` |
| Network test from inside | `kubectl run net --image=nicolaka/netshoot --rm -it -- bash` → curl, dig, nc |
| Resource pressure | `kubectl top pods -A --sort-by=memory`, `kubectl describe node` |
| Everything in one TUI | `k9s` |

| Exit code | Meaning |
| --- | --- |
| 0 | Process exited normally — did your container run a command that finishes? (Needs a long-running process.) |
| 1 / 2 | Application error — read logs. |
| 126 / 127 | Command not executable / not found — check `command`, entrypoint, image architecture. |
| 137 | SIGKILL — usually OOMKilled or failed liveness probe. |
| 143 | SIGTERM — normal shutdown. |

## Hands-on exercises

{% stepper %}
{% step %}
Install kube-prometheus-stack, open Grafana, and find the dashboard showing CPU per Pod in the `default` namespace.
{% endstep %}
{% step %}
Run the HPA load test from Module 20 while watching the dashboard.
{% endstep %}
{% step %}
In Prometheus (`port-forward svc/monitoring-kube-prometheus-prometheus 9090`), query `sum(kube_pod_container_status_restarts_total) by (pod)`.
{% endstep %}
{% step %}
**Break-fix drill:** ask a friend (or yourself, a day later) to introduce one fault: wrong image tag, wrong Service selector, bad targetPort, missing Secret key, 10Mi memory limit. Diagnose each with the flowchart only.
{% endstep %}
{% endstepper %}

## Common mistakes and tips

- **ServiceMonitor ignored** — the `release` label doesn't match, the Service port isn't named, or it's in a namespace Prometheus doesn't watch.
- **Logging to files inside the container** — Kubernetes only collects stdout/stderr. Log to stdout in JSON.
- **Relying on events for history** — they expire after an hour. Ship them with an event exporter if you need them later.
- **Alerting on CPU** instead of user-facing symptoms. Alert on error rate and latency; use CPU for dashboards.
- **Prometheus without persistence** loses all history on restart. Enable a PVC in the chart values for real use.
