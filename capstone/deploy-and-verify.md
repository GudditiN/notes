---
description: "One script to build everything, then prove each requirement works."
icon: circle-check
---

# 4. Deploy and verify

## Step 10 — One script to build it all

{% code title="setup.sh" %}
```bash
#!/usr/bin/env bash
set -euo pipefail

CLUSTER=learn
IMAGE=notes-api:1.0.0

echo "==> 1. Cluster"
if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --config kind-config.yaml
fi
kubectl config use-context "kind-$CLUSTER"

echo "==> 2. Platform add-ons"
# If you installed ingress-nginx from the raw kind manifest in Module 16, remove it first:
#   kubectl delete namespace ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace \
  --set controller.hostPort.enabled=true \
  --set controller.service.type=NodePort \
  --set-string controller.nodeSelector.ingress-ready=true \
  --set 'controller.tolerations[0].key=node-role.kubernetes.io/control-plane' \
  --set 'controller.tolerations[0].operator=Exists' \
  --set 'controller.tolerations[0].effect=NoSchedule' \
  --wait

helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
  --set 'args={--kubelet-insecure-tls}' --wait

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.adminPassword=admin123 \
  --wait --timeout 10m

echo "==> 3. Build and load image"
docker build -t "$IMAGE" ./app
kind load docker-image "$IMAGE" --name "$CLUSTER"

echo "==> 4. Namespace, config, secret"
kubectl apply -f k8s/00-namespace.yaml -f k8s/01-config.yaml
if ! kubectl get secret notes-db -n notes >/dev/null 2>&1; then
  kubectl create secret generic notes-db -n notes \
    --from-literal=DB_USER=notes \
    --from-literal=DB_PASSWORD="$(openssl rand -hex 16)"
fi

echo "==> 5. Database"
kubectl apply -f k8s/02-postgres.yaml
kubectl rollout status statefulset/postgres -n notes --timeout=180s

echo "==> 6. App, ingress, autoscaling, monitoring"
kubectl apply -f k8s/03-api.yaml -f k8s/04-ingress.yaml -f k8s/05-autoscaling.yaml -f k8s/06-monitoring.yaml
kubectl rollout status deploy/notes-api -n notes --timeout=180s

echo "==> Done. Try: curl -H 'Host: notes.local' http://localhost/"
```
{% endcode %}

```bash
chmod +x setup.sh
./setup.sh
```

## Step 11 — Verify every requirement

### It's running and reachable through the Ingress

```bash
kubectl get all,ingress,pvc,hpa,pdb -n notes
curl -s -H "Host: notes.local" http://localhost/ | jq
# optional: echo "127.0.0.1 notes.local" | sudo tee -a /etc/hosts  → then plain http://notes.local
```

### Config and secrets are injected

```bash
curl -s -H "Host: notes.local" http://localhost/ | jq .greeting      # from ConfigMap
kubectl exec -n notes deploy/notes-api -- printenv DB_USER            # from Secret
# change the greeting and roll out:
kubectl patch configmap notes-config -n notes --type merge -p '{"data":{"GREETING":"updated!"}}'
kubectl rollout restart deploy/notes-api -n notes
kubectl rollout status deploy/notes-api -n notes
```

### Data persists

```bash
curl -s -X POST -H "Host: notes.local" -H "Content-Type: application/json" \
  -d '{"text":"my first note on kubernetes"}' http://localhost/notes
kubectl delete pod postgres-0 -n notes          # kill the database
kubectl wait --for=condition=ready pod/postgres-0 -n notes --timeout=120s
curl -s -H "Host: notes.local" http://localhost/notes | jq     # note is still there
```

### Health checks protect traffic

```bash
kubectl scale statefulset postgres -n notes --replicas=0
kubectl get pods -n notes -w          # API Pods go 0/1 (not Ready) but do NOT restart
kubectl scale statefulset postgres -n notes --replicas=1
# they become Ready again on their own — liveness vs readiness in action
```

### Autoscaling works

```bash
# terminal 1
kubectl get hpa notes-api -n notes -w
# terminal 2: generate CPU load from inside the cluster
kubectl run load -n notes --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c 'while true; do wget -q -O- "http://notes-api/burn?ms=300" >/dev/null; done'
# replicas climb from 2 toward 6; stop the load and they return to 2 after ~2 minutes
```

### Monitoring is live

```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090 &
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80 &
# Prometheus: http://localhost:9090/targets → notes/notes-api should be UP
# Grafana:    http://localhost:3000  (admin / admin123)
```

In Grafana, create a dashboard with these panels (Explore → Prometheus → paste query):

| Panel | PromQL |
| --- | --- |
| Requests per second by route | `sum by (route) (rate(http_requests_total{job="notes-api"}[1m]))` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="notes-api"}[5m])))` |
| Error ratio | `sum(rate(http_requests_total{job="notes-api",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="notes-api"}[5m]))` |
| Replicas | `kube_deployment_status_replicas_available{namespace="notes",deployment="notes-api"}` |
| CPU per Pod | `sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="notes",container="api"}[1m]))` |
| Memory per Pod | `sum by (pod) (container_memory_working_set_bytes{namespace="notes",container="api"})` |

### Zero-downtime deploys

```bash
# change something in main.py (e.g. the /healthz message), then:
docker build -t notes-api:1.0.1 ./app
kind load docker-image notes-api:1.0.1 --name learn
kubectl set image deploy/notes-api -n notes api=notes-api:1.0.1
kubectl rollout status deploy/notes-api -n notes
kubectl rollout undo deploy/notes-api -n notes      # and back again
```

## Troubleshooting this project

| Symptom | Check |
| --- | --- |
| API Pods `0/1` forever | `kubectl logs -n notes deploy/notes-api` → "readiness failed". Is `postgres-0` Ready? Does the Secret exist? |
| `ErrImageNeverPull` / `ErrImagePull` | You forgot `kind load docker-image`, or the tag differs. |
| `CreateContainerConfigError` | Secret `notes-db` missing in namespace `notes`. |
| curl returns 404 | Missing `Host: notes.local` header, or ingress-nginx isn't running on the control-plane node. |
| HPA shows `<unknown>` | metrics-server not ready: `kubectl top pods -n notes`. |
| Target missing in Prometheus | ServiceMonitor `release: monitoring` label, Service port named `http`. |
| Postgres `CrashLoopBackOff` with permission errors | Check `fsGroup` and `PGDATA` subdirectory. Delete the PVC to start fresh (data loss!). |
