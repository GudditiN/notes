---
description: "Packaging, templating, and versioning your Kubernetes YAML."
icon: box-open
---

# 19. Helm

{% hint style="info" %}
**Level:** Intermediate · **Part:** Running real workloads
{% endhint %}

## Simple explanation

By now one app is a Deployment, Service, Ingress, ConfigMap, Secret, HPA… and you need slightly different versions for dev and prod. **Helm** is Kubernetes' package manager. A **chart** is a folder of YAML templates plus a `values.yaml` of defaults. You install a chart with your own values and get a **release** that Helm tracks, upgrades and rolls back as a unit.

You'll use Helm two ways: installing other people's software (ingress-nginx, cert-manager, Prometheus) and packaging your own apps.

## Key concepts

| Concept | What it means |
| --- | --- |
| Chart | The package: `Chart.yaml`, `values.yaml`, `templates/`. |
| Values | Inputs. Override with `-f values-prod.yaml` or `--set image.tag=abc`. |
| Release | One installed instance of a chart, with revision history. |
| Repository | Where charts are published (HTTP repo or OCI registry like ECR/GHCR). |
| Templates | Go templates: `{{ .Values.x }}`, `{{ include }}`, `if`, `range`, `toYaml`. |
| Hooks | Run Jobs at points in the lifecycle, e.g. DB migration `pre-upgrade`. |
| Kustomize | The alternative: patch plain YAML per environment without templates (`kubectl apply -k`). Many teams use Helm for third-party apps and Kustomize for their own. |

## Flow

<figure><img src="../.gitbook/assets/m12-diagram-1.svg" alt="Helm: Flow"><figcaption></figcaption></figure>

## Using public charts

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm search repo ingress-nginx
helm show values ingress-nginx/ingress-nginx > nginx-defaults.yaml   # read before installing!

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

## Your own chart

```bash
helm create myapp          # scaffold; then trim what you don't need
tree myapp
# myapp/
#   Chart.yaml
#   values.yaml
#   templates/
#     _helpers.tpl  deployment.yaml  service.yaml  ingress.yaml  hpa.yaml  NOTES.txt
```

{% code title="myapp/values.yaml" %}
```yaml
replicaCount: 2
image:
  repository: ghcr.io/gudditin/myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent
service:
  port: 80
  targetPort: 3000
env:
  LOG_LEVEL: info
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits:   { memory: 256Mi }
ingress:
  enabled: true
  className: nginx
  host: myapp.local
```
{% endcode %}

{% code title="myapp/templates/deployment.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "myapp.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}  # restart on config change
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.service.targetPort }}
          envFrom:
            - configMapRef:
                name: {{ include "myapp.fullname" . }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```
{% endcode %}

{% code title="myapp/templates/configmap.yaml" %}
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "myapp.fullname" . }}
data:
  {{- range $k, $v := .Values.env }}
  {{ $k }}: {{ $v | quote }}
  {{- end }}
```
{% endcode %}

{% code title="myapp/values-prod.yaml" %}
```yaml
replicaCount: 4
env:
  LOG_LEVEL: warn
resources:
  requests: { cpu: 250m, memory: 512Mi }
  limits:   { memory: 512Mi }
ingress:
  host: myapp.example.com
```
{% endcode %}

## Important commands

```bash
helm lint ./myapp
helm template myapp ./myapp -f myapp/values-prod.yaml      # render locally, inspect output
helm upgrade --install myapp ./myapp -n dev --create-namespace --set image.tag=abc123 --atomic --wait
helm list -A
helm history myapp -n dev
helm rollback myapp 2 -n dev
helm get values myapp -n dev
helm get manifest myapp -n dev
helm uninstall myapp -n dev
helm package ./myapp && helm push myapp-0.1.0.tgz oci://ghcr.io/gudditin/charts
```

## Hands-on exercises

{% stepper %}
{% step %}
Install ingress-nginx via Helm into a fresh kind cluster instead of the raw manifest.
{% endstep %}
{% step %}
Run `helm create myapp`, add the ConfigMap template above, and install it with nginx as the image.
{% endstep %}
{% step %}
Upgrade with `--set replicaCount=3`, then again with a broken image and `--atomic`. Helm rolls back automatically.
{% endstep %}
{% step %}
Render with and without `values-prod.yaml` and diff the output.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Indentation errors** in rendered YAML — use `nindent`, and always run `helm template` before installing.
- **"cannot re-use a name that is still in use"** — use `helm upgrade --install` everywhere so the same command works for first install and updates.
- **Release stuck `pending-upgrade`** — a previous run was interrupted. `helm rollback` to the last good revision.
- **Installing charts without reading values** — defaults may create public LoadBalancers or skip persistence. Always `helm show values` first.
- **Pinning nothing** — use `--version` for third-party charts so upgrades are deliberate.
