---
description: "Every module combined into one working system on your laptop."
icon: diagram-project
---

# Capstone project: Notes API

## What you'll build

A small FastAPI service that stores notes in PostgreSQL. You'll containerize it, run the whole stack locally with **Docker Compose**, then run it on kind with:

- a Deployment with non-root, read-only containers and startup/readiness/liveness probes
- a PostgreSQL StatefulSet with a PersistentVolumeClaim so notes survive restarts
- a ConfigMap for settings and a Secret for database credentials
- a Service and an Ingress at `http://notes.local`
- an HPA that scales on CPU, plus a PodDisruptionBudget
- Prometheus scraping the app's `/metrics`, an alert rule, and Grafana panels

<figure><img src="../.gitbook/assets/capstone-architecture.svg" alt="Capstone project architecture"><figcaption><p>Solid lines carry requests; dashed lines are configuration, scaling and monitoring relationships.</p></figcaption></figure>

| Piece | Kubernetes object | What it teaches | Module |
| --- | --- | --- | --- |
| Image | Dockerfile | Small, non-root, cache-friendly build | 3 |
| Local dev | Docker Compose | Run the whole stack on one machine | 6 |
| Front door | Ingress + ingress-nginx | Host-based HTTP routing | 16 |
| Stable address | Service `notes-api` | Load balancing across Ready Pods | 12 |
| The app | Deployment `notes-api` | Rolling updates, probes, security context | 11, 17, 18 |
| Scaling | HPA + PodDisruptionBudget | CPU-based scaling, safe disruptions | 20 |
| Settings | ConfigMap `notes-config` | Config outside the image | 13 |
| Credentials | Secret `notes-db` | Shared by app and database | 13 |
| Database | StatefulSet `postgres` + headless Service | Stable identity for stateful apps | 14 |
| Data | PVC `data-postgres-0` | Storage that outlives Pods | 14 |
| Visibility | ServiceMonitor + PrometheusRule | Scraping app metrics, alerting | 21 |

## Project layout

```text
notes-project/
├── app/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-config.yaml
│   ├── 02-postgres.yaml
│   ├── 03-api.yaml
│   ├── 04-ingress.yaml
│   ├── 05-autoscaling.yaml
│   └── 06-monitoring.yaml
├── compose.yaml            # Docker Compose (Step 3)
├── .env.example
├── kind-config.yaml        # from Module 9
└── setup.sh
```

{% hint style="success" %}
**All source files are in the repository** under `notes-project/`, ready to copy: the app, Dockerfile, every manifest, and `setup.sh`.
{% endhint %}
