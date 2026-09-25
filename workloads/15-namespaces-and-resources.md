---
description: "Dividing a cluster between teams and environments, and stopping one app from starving the rest."
icon: layer-group
---

# 15. Namespaces and resource management

{% hint style="info" %}
**Level:** Intermediate · **Part:** Running real workloads
{% endhint %}

## Simple explanation

A **namespace** is a folder inside the cluster. Names must be unique within a namespace but can repeat across them, so `dev/api` and `staging/api` coexist. Namespaces are also where you attach permissions (RBAC), quotas and network policies.

**Requests and limits** tell Kubernetes how much CPU and memory a container needs. The scheduler uses *requests* to decide where a Pod fits. The kubelet enforces *limits*: exceed the CPU limit and you get throttled (slowed); exceed the memory limit and you get killed (`OOMKilled`).

## Key concepts

| Concept | What it means |
| --- | --- |
| CPU units | `1` = one vCPU. `250m` = a quarter of one (m = millicores). |
| Memory units | `128Mi`, `1Gi` (powers of 2). Beware `128M` vs `128Mi`, and never `128m` (that's millibytes). |
| QoS classes | **Guaranteed** (requests = limits for all), **Burstable** (some requests set), **BestEffort** (none — evicted first under pressure). |
| ResourceQuota | Caps total CPU/memory/objects in a namespace. |
| LimitRange | Default and min/max requests/limits for containers in a namespace. |
| Cluster-scoped | Some objects have no namespace: Nodes, PVs, StorageClasses, ClusterRoles, Namespaces themselves. |

## Architecture / flow

<figure><img src="../.gitbook/assets/m8-diagram-1.svg" alt="Namespaces and resource management: Architecture / flow"><figcaption></figcaption></figure>

{% hint style="info" %}
**Practical rule for requests and limits**

Set memory request = memory limit (memory can't be reclaimed, so over-committing causes OOM kills). Set a CPU request based on typical usage and usually *no* CPU limit, so the app can burst into idle CPU without throttling. Measure with `kubectl top` and adjust.
{% endhint %}

## YAML examples

{% code title="namespace-quota.yaml" %}
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    env: dev
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.memory: 8Gi
    pods: "30"
    services.loadbalancers: "0"     # no surprise cloud bills from dev
    persistentvolumeclaims: "5"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-defaults
  namespace: dev
spec:
  limits:
    - type: Container
      defaultRequest: { cpu: 100m, memory: 128Mi }   # applied if container sets none
      default:        { memory: 256Mi }              # default limit
      max:            { cpu: "2", memory: 2Gi }
```
{% endcode %}

{% code title="resources-example.yaml" %}
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hungry
  namespace: dev
spec:
  containers:
    - name: stress
      image: polinux/stress
      command: ["stress", "--vm", "1", "--vm-bytes", "200M", "--vm-hang", "1"]
      resources:
        requests: { cpu: 100m, memory: 128Mi }
        limits:   { memory: 128Mi }   # will be OOMKilled: uses 200M
```
{% endcode %}

## Important commands

```bash
kubectl get ns
kubectl create ns staging
kubectl get pods -n dev
kubectl config set-context --current --namespace=dev     # or: kubens dev
kubectl describe quota -n dev                            # used vs hard
kubectl describe limitrange -n dev
kubectl describe node learn-worker | grep -A8 "Allocated resources"
kubectl get pod hungry -n dev -o jsonpath='{.status.qosClass}'
kubectl delete ns dev                                    # deletes EVERYTHING inside it
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply the quota file. Create a Deployment in `dev` without resources and confirm the LimitRange filled them in (`kubectl get pod -o yaml`).
{% endstep %}
{% step %}
Scale that Deployment to 50 replicas. Run `kubectl get rs -n dev` and `kubectl describe rs` — the quota blocks Pod creation with a clear error.
{% endstep %}
{% step %}
Apply `resources-example.yaml`. Watch it reach `OOMKilled`. Raise the limit to 256Mi and it survives.
{% endstep %}
{% step %}
Request `cpu: 50` on a Pod. It stays Pending with "Insufficient cpu".
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **No requests set** — the scheduler packs Pods blindly, nodes get overloaded, and autoscaling (Module 20) can't work.
- **"failed quota: must specify limits.memory"** — a quota on limits forces every Pod to declare them. Add a LimitRange with defaults.
- **Tight CPU limits** cause mysterious latency from throttling even when nodes are idle. Check `container_cpu_cfs_throttled_periods_total` in Prometheus.
- **Namespace stuck `Terminating`** — a finalizer on some resource is waiting on a controller that's gone. Find it with `kubectl api-resources --verbs=list --namespaced -o name | xargs -n1 kubectl get -n NS --ignore-not-found`.
- Namespaces are *not* a security boundary by themselves. Add RBAC and NetworkPolicies.
