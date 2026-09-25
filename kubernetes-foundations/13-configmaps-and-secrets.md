---
description: "Keeping configuration out of your images."
icon: sliders
---

# 13. ConfigMaps and Secrets

{% hint style="info" %}
**Level:** Beginner → Intermediate · **Part:** Kubernetes foundations
{% endhint %}

## Simple explanation

Build an image once and run it in dev, staging and prod with different settings. **ConfigMaps** hold non-sensitive config (log level, feature flags, whole config files). **Secrets** hold sensitive values (passwords, API keys, TLS certs). Both can be injected as environment variables or mounted as files.

{% hint style="warning" %}
**Secrets are not encrypted by default**

Kubernetes Secret values are only base64-encoded, which anyone can decode. Real protection comes from RBAC (who can read Secrets), encryption at rest in etcd (enabled by default on EKS with KMS envelope encryption available), and never committing plain Secret YAML to Git.
{% endhint %}

## Key concepts

| Concept | What it means |
| --- | --- |
| env / valueFrom | Inject one key as one environment variable. |
| envFrom | Inject every key in a ConfigMap/Secret as env vars. |
| Volume mount | Each key becomes a file. Mounted files update automatically (~1 min) when the object changes; env vars do not. |
| Secret types | `Opaque` (generic), `kubernetes.io/tls`, `kubernetes.io/dockerconfigjson` (registry login). |
| stringData | Write Secret values as plain text in YAML; Kubernetes encodes them for you. |
| immutable | `immutable: true` prevents edits and reduces API load for large clusters. |
| External Secrets Operator | Syncs from AWS Secrets Manager / SSM / Vault into Kubernetes Secrets. The production answer. |

## Flow

<figure><img src="../.gitbook/assets/m6-diagram-1.svg" alt="ConfigMaps and Secrets: Flow"><figcaption></figcaption></figure>

## YAML examples

{% code title="configmap.yaml" %}
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "info"
  FEATURE_NEW_CHECKOUT: "true"
  app.properties: |               # a whole file as one key
    cache.ttl=300
    retries=3
```
{% endcode %}

{% code title="secret.yaml" %}
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:                       # plain text here; stored base64-encoded
  DB_PASSWORD: "s3cr3t-change-me"
  API_KEY: "abc123"
```
{% endcode %}

{% code title="deployment-using-config.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 1
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
        - name: api
          image: busybox:1.36
          command: ["sh", "-c", "env | sort; cat /config/app.properties; sleep 3600"]
          envFrom:
            - configMapRef:
                name: app-config          # every key becomes an env var
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secret
                  key: DB_PASSWORD
            - name: POD_NAME              # bonus: Downward API
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          volumeMounts:
            - name: config-files
              mountPath: /config
              readOnly: true
      volumes:
        - name: config-files
          configMap:
            name: app-config
            items:
              - key: app.properties
                path: app.properties
```
{% endcode %}

### Production pattern: External Secrets Operator with AWS Secrets Manager

{% code title="external-secret.yaml" %}
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-sm
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-south-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa   # bound to an IAM role via IRSA / Pod Identity
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-sm
    kind: SecretStore
  target:
    name: app-secret                    # Kubernetes Secret it creates
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: prod/api/db
        property: password
```
{% endcode %}

## Important commands

```bash
kubectl create configmap app-config --from-literal=LOG_LEVEL=debug --from-file=app.properties
kubectl create secret generic app-secret --from-literal=DB_PASSWORD=s3cr3t
kubectl create secret docker-registry regcred --docker-server=ghcr.io \
  --docker-username=USER --docker-password=TOKEN
kubectl create secret tls web-tls --cert=tls.crt --key=tls.key
kubectl get secret app-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo
kubectl rollout restart deploy/api        # pick up changed env vars
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply the three files. Run `kubectl logs deploy/api` and find each value.
{% endstep %}
{% step %}
Change `LOG_LEVEL` in the ConfigMap and re-apply. Check env inside the Pod (`kubectl exec deploy/api -- env | grep LOG`) — unchanged. Now edit `app.properties` in the ConfigMap, wait a minute, and `cat /config/app.properties` — changed. Now you know why rollouts are needed.
{% endstep %}
{% step %}
Decode your Secret with the jsonpath command. Reflect on why RBAC matters.
{% endstep %}
{% step %}
Reference a key that doesn't exist and observe `CreateContainerConfigError`.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`CreateContainerConfigError`** — referenced ConfigMap/Secret or key doesn't exist, or it's in another namespace (they must be in the same namespace as the Pod). Add `optional: true` only if the value really is optional.
- **Committing Secret YAML to Git.** Use External Secrets, Sealed Secrets, or SOPS instead.
- **Unquoted YAML values.** `ENABLED: true` and `PORT: 8080` fail in ConfigMaps — all values must be strings. Quote them.
- **Using `data:` with plain text.** `data` expects base64. Use `stringData` for plain text.
- **Config changed but app didn't notice.** Add a checksum annotation (Helm does this, Module 19) or run `rollout restart`.
