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
