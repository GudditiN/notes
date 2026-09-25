---
description: "Namespace, config, secrets, database, app, Ingress, autoscaling and monitoring."
icon: file-code
---

# 3. Write the Kubernetes manifests

## Step 4 — Namespace, config and secrets

{% code title="k8s/00-namespace.yaml" %}
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: notes
  labels:
    pod-security.kubernetes.io/enforce: baseline     # postgres image needs baseline
    pod-security.kubernetes.io/warn: restricted      # warns about anything not restricted-ready
```
{% endcode %}

{% code title="k8s/01-config.yaml" %}
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: notes-config
  namespace: notes
data:
  APP_ENV: "local"
  LOG_LEVEL: "info"
  GREETING: "hello from kubernetes"
  DB_HOST: "postgres"
  DB_PORT: "5432"
  DB_NAME: "notes"
  DB_POOL_MAX: "5"
```
{% endcode %}

The Secret is created by command, not committed to Git:

```bash
kubectl create secret generic notes-db -n notes \
  --from-literal=DB_USER=notes \
  --from-literal=DB_PASSWORD="$(openssl rand -hex 16)"
```

## Step 5 — PostgreSQL with persistent storage

{% code title="k8s/02-postgres.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: notes
  labels: { app: postgres }
spec:
  clusterIP: None
  selector: { app: postgres }
  ports:
    - name: postgres
      port: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: notes
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels: { app: postgres }
  template:
    metadata:
      labels: { app: postgres }
    spec:
      terminationGracePeriodSeconds: 60
      securityContext:
        fsGroup: 70                      # postgres user in the alpine image
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - { name: postgres, containerPort: 5432 }
          env:
            - name: POSTGRES_DB
              valueFrom: { configMapKeyRef: { name: notes-config, key: DB_NAME } }
            - name: POSTGRES_USER
              valueFrom: { secretKeyRef: { name: notes-db, key: DB_USER } }
            - name: POSTGRES_PASSWORD
              valueFrom: { secretKeyRef: { name: notes-db, key: DB_PASSWORD } }
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits:   { memory: 256Mi }
          readinessProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\""]
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 6
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
```
{% endcode %}

## Step 6 — The API Deployment and Service

{% code title="k8s/03-api.yaml" %}
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: notes-api
  namespace: notes
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notes-api
  namespace: notes
  labels: { app: notes-api }
spec:
  # no "replicas" field: the HPA owns the count (Module 20)
  revisionHistoryLimit: 5
  selector:
    matchLabels: { app: notes-api }
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  template:
    metadata:
      labels: { app: notes-api }
    spec:
      serviceAccountName: notes-api
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile: { type: RuntimeDefault }
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: { matchLabels: { app: notes-api } }
      containers:
        - name: api
          image: notes-api:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - { name: http, containerPort: 8000 }
          envFrom:
            - configMapRef: { name: notes-config }
            - secretRef:    { name: notes-db }          # DB_USER, DB_PASSWORD
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits:   { memory: 256Mi }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          startupProbe:
            httpGet: { path: /healthz, port: http }
            periodSeconds: 3
            failureThreshold: 20
          readinessProbe:
            httpGet: { path: /ready, port: http }
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          livenessProbe:
            httpGet: { path: /healthz, port: http }
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          lifecycle:
            preStop:
              exec: { command: ["sleep", "5"] }
          volumeMounts:
            - { name: tmp, mountPath: /tmp }
      volumes:
        - { name: tmp, emptyDir: {} }
---
apiVersion: v1
kind: Service
metadata:
  name: notes-api
  namespace: notes
  labels: { app: notes-api }
spec:
  selector: { app: notes-api }
  ports:
    - name: http              # named: the ServiceMonitor refers to it
      port: 80
      targetPort: http
```
{% endcode %}

## Step 7 — Ingress

{% code title="k8s/04-ingress.yaml" %}
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: notes
  namespace: notes
spec:
  ingressClassName: nginx
  rules:
    - host: notes.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: notes-api
                port: { name: http }
```
{% endcode %}

## Step 8 — Autoscaling and disruption budget

{% code title="k8s/05-autoscaling.yaml" %}
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: notes-api
  namespace: notes
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: notes-api
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 60 }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 120
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: notes-api
  namespace: notes
spec:
  maxUnavailable: 1
  selector:
    matchLabels: { app: notes-api }
```
{% endcode %}

## Step 9 — Monitoring and alerts

{% code title="k8s/06-monitoring.yaml" %}
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: notes-api
  namespace: notes
  labels:
    release: monitoring                   # matches the kube-prometheus-stack release name
spec:
  selector:
    matchLabels: { app: notes-api }
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: notes-api
  namespace: notes
  labels:
    release: monitoring
spec:
  groups:
    - name: notes-api
      rules:
        - alert: NotesApiHighErrorRate
          expr: |
            sum(rate(http_requests_total{job="notes-api",status=~"5.."}[5m]))
              / clamp_min(sum(rate(http_requests_total{job="notes-api"}[5m])), 1e-9) > 0.05
          for: 5m
          labels: { severity: warning }
          annotations:
            summary: "notes-api 5xx rate above 5%"
        - alert: NotesApiPodRestarting
          expr: increase(kube_pod_container_status_restarts_total{namespace="notes"}[15m]) > 3
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "{{ $labels.pod }} restarted more than 3 times in 15 minutes"
        - alert: NotesApiAtMaxReplicas
          expr: |
            kube_horizontalpodautoscaler_status_current_replicas{namespace="notes"}
              >= kube_horizontalpodautoscaler_spec_max_replicas{namespace="notes"}
          for: 15m
          labels: { severity: warning }
          annotations:
            summary: "HPA has been at max replicas for 15 minutes; raise the limit or add capacity"
```
{% endcode %}
