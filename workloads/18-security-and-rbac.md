---
description: "Who can do what in the cluster, and what your containers are allowed to do."
icon: shield-halved
---

# 18. Security and RBAC

{% hint style="info" %}
**Level:** Intermediate → Advanced · **Part:** Running real workloads
{% endhint %}

## Simple explanation

Every request to the API server goes through three gates: **authentication** (who are you?), **authorization** (are you allowed?), and **admission control** (is this object acceptable?). RBAC is the authorization part.

**RBAC** (role-based access control) has two halves: a **Role** lists permissions ("get, list pods"), and a **RoleBinding** grants that Role to a user, group, or **ServiceAccount** (the identity a Pod uses). Beyond RBAC, you also lock down containers (non-root, read-only filesystem) and network traffic between Pods.

## Key concepts

| Concept | What it means |
| --- | --- |
| Role / RoleBinding | Permissions within one namespace. |
| ClusterRole / ClusterRoleBinding | Cluster-wide permissions, or reusable roles bound per namespace. |
| ServiceAccount | Identity for Pods. Each namespace has `default`; create one per app instead. |
| Verbs | get, list, watch, create, update, patch, delete, deletecollection. |
| securityContext | Pod/container-level settings: runAsNonRoot, readOnlyRootFilesystem, drop capabilities. |
| Pod Security Admission | Built-in policy per namespace: `privileged`, `baseline`, `restricted`. |
| NetworkPolicy | Pod-level firewall. Needs a CNI that enforces it (Calico, Cilium; not kind's default kindnet). |
| IRSA / EKS Pod Identity | Map a ServiceAccount to an IAM role so Pods get AWS credentials without keys — the equivalent of an ECS task role. |

## Architecture / flow

<figure><img src="../.gitbook/assets/m11-diagram-1.svg" alt="Security and RBAC: Architecture / flow"><figcaption></figcaption></figure>

## YAML examples

{% code title="rbac-readonly.yaml" %}
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pod-reader
  namespace: dev
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: read-pods
  namespace: dev
rules:
  - apiGroups: [""]                  # "" = core group (pods, services, secrets)
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-reader-binding
  namespace: dev
subjects:
  - kind: ServiceAccount
    name: pod-reader
    namespace: dev
roleRef:
  kind: Role
  name: read-pods
  apiGroup: rbac.authorization.k8s.io
```
{% endcode %}

{% code title="ci-deployer.yaml" %}
```yaml
# Minimal permissions for a CI pipeline that deploys to one namespace
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { name: deployer, namespace: prod }
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["services", "configmaps"]
    verbs: ["get", "list", "create", "update", "patch"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses"]
    verbs: ["get", "list", "create", "update", "patch"]
```
{% endcode %}

{% code title="secure-pod.yaml" %}
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure
  labels:
    pod-security.kubernetes.io/enforce: restricted   # reject insecure Pods
---
apiVersion: v1
kind: Pod
metadata: { name: hardened, namespace: secure }
spec:
  automountServiceAccountToken: false   # app doesn't call the K8s API
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    fsGroup: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: app
      image: nginxinc/nginx-unprivileged:1.27
      ports: [{ containerPort: 8080 }]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      volumeMounts:
        - { name: tmp, mountPath: /tmp }   # writable scratch where the app needs it
  volumes:
    - { name: tmp, emptyDir: {} }
```
{% endcode %}

{% code title="networkpolicy.yaml" %}
```yaml
# Default deny all ingress in namespace, then allow web → api on 8080 only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: prod }
spec:
  podSelector: {}
  policyTypes: ["Ingress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-web-to-api, namespace: prod }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: { matchLabels: { app: web } }
      ports:
        - { protocol: TCP, port: 8080 }
```
{% endcode %}

## Important commands

```bash
kubectl auth can-i create deployments -n prod
kubectl auth can-i list secrets -n dev --as=system:serviceaccount:dev:pod-reader
kubectl auth can-i --list --as=system:serviceaccount:dev:pod-reader -n dev
kubectl get roles,rolebindings -n dev
kubectl get clusterrolebindings -o wide | grep cluster-admin     # who has god mode?
kubectl create token pod-reader -n dev                           # short-lived token for testing
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply `rbac-readonly.yaml`. Use `kubectl auth can-i` with `--as` to prove the ServiceAccount can list Pods but not delete them or read Secrets.
{% endstep %}
{% step %}
Apply `secure-pod.yaml`. Then try creating a plain `nginx:1.27` Pod in the `secure` namespace and read the rejection message.
{% endstep %}
{% step %}
Recreate your kind cluster with Calico (`networking.disableDefaultCNI: true` in kind config, then install Calico), apply the NetworkPolicies, and prove that only `app=web` Pods can reach `api`.
{% endstep %}
{% step %}
Scan an image: `trivy image nginx:1.27`. Compare with `nginx:1.27-alpine`.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Binding `cluster-admin` to CI or apps** "to make it work". Start from zero and add verbs until `Forbidden` errors stop — the error message names the exact verb and resource missing.
- **Forgetting the apiGroup** — Deployments are in `apps`, Ingresses in `networking.k8s.io`, Pods in `""`. Check with `kubectl api-resources`.
- **NetworkPolicy "doesn't work"** — your CNI doesn't enforce it. Policies are silently ignored.
- **Denying egress breaks DNS** — when you add egress policies, allow UDP/TCP 53 to kube-dns.
- **Read-only root filesystem breaks the app** — mount `emptyDir` at the paths it writes (`/tmp`, cache dirs).
- **Long-lived AWS keys in Secrets** — use IRSA or EKS Pod Identity instead.
