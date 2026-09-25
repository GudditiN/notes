---
description: "The tools you'll meet once the basics are second nature."
icon: flask
---

# 24. Advanced Kubernetes concepts

{% hint style="info" %}
**Level:** Advanced · **Part:** Operating in production
{% endhint %}

## Simple explanation

Kubernetes is extensible: you can teach it new object types and new controllers. Most "advanced" topics are either finer control over where Pods run, specialized workload types, or extensions built on Custom Resources. Read each section, run the example, and go deeper on the ones your job needs.

## 1. Scheduling control

| Concept | What it means |
| --- | --- |
| nodeSelector | Simplest: only run on nodes with a label. |
| Node affinity | Required or preferred rules on node labels (instance type, zone, arch). |
| Pod (anti-)affinity | Run near or away from other Pods (e.g. cache next to app; replicas on different nodes). |
| Taints & tolerations | A taint repels Pods from a node; only Pods that tolerate it can land there. Used for GPU nodes, dedicated tenants, Spot. |
| PriorityClass | Higher priority Pods can preempt lower ones when the cluster is full. |

{% code title="scheduling.yaml" %}
```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - { key: kubernetes.io/arch, operator: In, values: ["arm64"] }   # Graviton
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            topologyKey: kubernetes.io/hostname
            labelSelector: { matchLabels: { app: api } }
  tolerations:
    - { key: "dedicated", operator: "Equal", value: "batch", effect: "NoSchedule" }
```
{% endcode %}

```bash
kubectl taint nodes learn-worker2 dedicated=batch:NoSchedule
kubectl taint nodes learn-worker2 dedicated=batch:NoSchedule-    # remove
```

## 2. Other workload types

| Kind | Use for |
| --- | --- |
| DaemonSet | One Pod per node: log agents, node-exporter, CNI, security agents. |
| Job | Run to completion: DB migration, report generation. |
| CronJob | Scheduled Jobs: nightly cleanup, backups. |
| StatefulSet | Stable identity + per-Pod storage (Module 14). |

{% code title="cronjob.yaml" %}
```yaml
apiVersion: batch/v1
kind: CronJob
metadata: { name: nightly-report }
spec:
  schedule: "30 2 * * *"            # 02:30 every day, in the timeZone below
  timeZone: "Asia/Kolkata"          # without this, the controller uses its own timezone (usually UTC)
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 600
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: report
              image: busybox:1.36
              command: ["sh", "-c", "echo generating report at $(date)"]
```
{% endcode %}

```bash
kubectl create job manual-run --from=cronjob/nightly-report     # trigger now
```

## 3. Custom Resources and Operators

A **CustomResourceDefinition (CRD)** adds a new object type to the API (you've already used some: ServiceMonitor, ExternalSecret, Application). An **Operator** is a controller that watches that type and does the work, encoding human operational knowledge: CloudNativePG creates Postgres clusters with failover and backups from one `Cluster` object; cert-manager turns a `Certificate` into a renewed TLS Secret.

<figure><img src="../.gitbook/assets/m17-diagram-1.svg" alt="Advanced Kubernetes concepts: 3. Custom Resources and Operators"><figcaption></figcaption></figure>

{% code title="crd-example.yaml" %}
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: websites.demo.example.com
spec:
  group: demo.example.com
  names: { kind: Website, plural: websites, singular: website, shortNames: [ws] }
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                domain:   { type: string }
                replicas: { type: integer, minimum: 1 }
---
apiVersion: demo.example.com/v1
kind: Website
metadata: { name: blog }
spec: { domain: blog.local, replicas: 2 }
```
{% endcode %}

Apply it and `kubectl get ws` works — but nothing happens, because no controller exists yet. Writing one (with Kubebuilder or Operator SDK in Go, or kopf in Python) is the natural next project.

## 4. Gateway API

{% code title="httproute.yaml" %}
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: { name: shop }
spec:
  parentRefs: [{ name: public-gateway }]       # Gateway owned by platform team
  hostnames: ["shop.example.com"]
  rules:
    - matches: [{ path: { type: PathPrefix, value: /api } }]
      backendRefs:
        - { name: api-v1, port: 80, weight: 90 }  # built-in canary split
        - { name: api-v2, port: 80, weight: 10 }
```
{% endcode %}

## 5. Progressive delivery, service mesh, policy

| Concept | What it means |
| --- | --- |
| Argo Rollouts / Flagger | Canary and blue/green with automatic promotion or rollback based on Prometheus metrics. |
| Service mesh | Istio, Linkerd, Cilium: mTLS between services, retries, traffic splitting, per-request metrics without code changes. Adds complexity — adopt only for a clear need. |
| Policy engines | Kyverno or OPA Gatekeeper enforce rules at admission: "all images must come from ECR", "every Deployment needs requests". |
| eBPF | Cilium and friends use kernel eBPF for fast networking, NetworkPolicy and observability (Hubble). |
| Multi-cluster | Argo CD ApplicationSets, Cluster API for cluster lifecycle, multi-region failover. |

{% code title="kyverno-require-requests.yaml" %}
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: require-requests }
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-resources
      match: { any: [{ resources: { kinds: [Pod] } }] }
      validate:
        message: "CPU and memory requests are required."
        pattern:
          spec:
            containers:
              - resources:
                  requests: { cpu: "?*", memory: "?*" }
```
{% endcode %}

## Hands-on exercises

{% stepper %}
{% step %}
Taint `learn-worker2`, deploy 4 replicas, confirm they all land on `learn-worker`. Add a toleration and see them spread.
{% endstep %}
{% step %}
Create the CronJob with `schedule: "*/1 * * * *"` and watch Jobs appear each minute.
{% endstep %}
{% step %}
Apply the CRD and a `Website`. Run `kubectl explain website.spec`.
{% endstep %}
{% step %}
Install Kyverno via Helm, apply the policy, and try deploying a Pod without requests.
{% endstep %}
{% endstepper %}

## Common mistakes

- **Hard `required` anti-affinity** with more replicas than nodes → Pods stuck Pending. Prefer `preferred` or topology spread.
- **CronJob without `concurrencyPolicy: Forbid`** — slow runs overlap and pile up.
- **Deleting a CRD** deletes every object of that type in the cluster. Treat CRDs like database schemas.
- **Adopting a service mesh for mTLS alone** — check if your CNI (Cilium) or cloud networking already covers it.
