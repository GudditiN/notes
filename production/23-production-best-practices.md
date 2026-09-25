---
description: "A checklist distilled from outages, and what a real cluster on AWS looks like."
icon: rocket
---

# 23. Production best practices

{% hint style="info" %}
**Level:** Advanced · **Part:** Operating in production
{% endhint %}

## Simple explanation

Everything in Modules 8–22 works on a laptop. Production adds three concerns: **reliability** (survive node and zone failures, deploy without downtime), **security** (least privilege everywhere), and **operability** (upgrades, backups, cost). Most teams use a managed control plane (EKS, GKE, AKS) so they never touch etcd or the API server.

## Key concepts: the checklist

| Area | Do this |
| --- | --- |
| Workloads | Requests on every container; memory limit = request; ≥2 replicas; PDB; readiness + liveness (+ startup for slow apps); graceful SIGTERM handling; immutable image tags. |
| Spreading | `topologySpreadConstraints` across zones and nodes so one AZ failure doesn't take all replicas. |
| Images | Small base (distroless/alpine/slim), non-root user, vulnerability scan in CI, pull from private registry (ECR) with pull-through cache. |
| Security | Pod Security `restricted` where possible; per-app ServiceAccounts with IRSA/Pod Identity; no cluster-admin for humans day-to-day; default-deny NetworkPolicies; secrets from Secrets Manager via ESO; private API endpoint or IP allowlist. |
| Config | Everything in Git; Helm/Kustomize per environment; GitOps sync; no `kubectl edit` in prod. |
| Scaling | HPA on apps; Karpenter for nodes; right-size with VPA recommendations; Spot for stateless workloads with On-Demand fallback. |
| Data | Prefer managed databases (Aurora/RDS). If stateful in-cluster: StatefulSets, Retain reclaim policy, Velero backups tested by restoring. |
| Observability | Metrics + dashboards + alerts on golden signals; centralized logs; SLOs for key services. |
| Upgrades | Kubernetes releases every ~4 months, each supported ~14 months (EKS extended support costs extra). Upgrade one minor version at a time; check deprecated APIs with `pluto` or `kubent` first. |
| Cost | Requests drive node count — oversized requests waste money. Use Kubecost/OpenCost; one shared ALB via `group.name`; delete idle dev namespaces. |

## Reference architecture on AWS

<figure><img src="../.gitbook/assets/aws-reference-architecture.svg" alt="Reference production architecture on AWS EKS"><figcaption><p>Traffic flows top to bottom: Route 53 → ALB → Pods spread across three AZs → managed data stores. AWS services on the right are reached through IAM roles bound to Kubernetes ServiceAccounts, never stored keys.</p></figcaption></figure>

| Layer | AWS / Kubernetes piece | Why it's there |
| --- | --- | --- |
| Edge | Route 53, ACM, ALB (via AWS Load Balancer Controller) | DNS, TLS, one shared load balancer for many Ingresses |
| Compute | EKS managed control plane, Karpenter nodes in 3 AZs | No etcd to run; nodes sized and added per workload in seconds |
| Workloads | Deployments with HPA, PDB, topology spread | Survive a node or AZ loss; scale with load |
| Identity | IAM + Pod Identity / IRSA per ServiceAccount | Pods get AWS access without stored keys, like ECS task roles |
| Config and secrets | External Secrets Operator ← Secrets Manager | Secrets live in AWS, synced into the cluster, never in Git |
| Data | Aurora, ElastiCache outside the cluster | Managed backups, failover and patching |
| Delivery | GitHub Actions → ECR; Argo CD pulls from Git | Every change reviewed in Git; drift auto-corrected |
| Observability | Prometheus, Grafana, Fluent Bit → CloudWatch | Metrics, alerts and centralised logs |

## YAML example: production-grade Deployment fragment

{% code title="prod-deployment-fragment.yaml" %}
```yaml
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    rollingUpdate: { maxSurge: 25%, maxUnavailable: 0 }
  template:
    spec:
      serviceAccountName: api
      terminationGracePeriodSeconds: 45
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: { matchLabels: { app: api } }
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: { matchLabels: { app: api } }
      securityContext:
        runAsNonRoot: true
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: api
          image: 111122223333.dkr.ecr.ap-south-1.amazonaws.com/api:3f9c2ab
          resources:
            requests: { cpu: 250m, memory: 512Mi }
            limits:   { memory: 512Mi }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          startupProbe:   { httpGet: { path: /healthz, port: http }, periodSeconds: 5, failureThreshold: 30 }
          readinessProbe: { httpGet: { path: /ready,   port: http }, periodSeconds: 5 }
          livenessProbe:  { httpGet: { path: /healthz, port: http }, periodSeconds: 10, failureThreshold: 3 }
          lifecycle:
            preStop: { exec: { command: ["sleep", "10"] } }
```
{% endcode %}

## Creating an EKS cluster (for when you're ready to spend money)

```bash
# eksctl is the quickest learning path; in your real work, define it in CDK (aws-eks / eks-v2 constructs) or Terraform
eksctl create cluster --name learn-eks --region ap-south-1 \
  --version 1.31 --nodegroup-name default --node-type t3.medium \
  --nodes 2 --nodes-min 2 --nodes-max 4 --managed
aws eks update-kubeconfig --name learn-eks --region ap-south-1
kubectl get nodes

# ALWAYS clean up after practice — an idle EKS control plane is ~$73/month plus nodes
eksctl delete cluster --name learn-eks --region ap-south-1
```

## Important commands

```bash
kubectl get pods -A -o json | jq -r '.items[] | select(.spec.containers[].resources.requests == null) | .metadata.namespace + "/" + .metadata.name'  # Pods missing requests
kubectl get pdb -A
kubectl drain NODE --ignore-daemonsets --delete-emptydir-data   # safe node maintenance
kubectl uncordon NODE
pluto detect-helm -o wide                                       # deprecated APIs before an upgrade
```

## Hands-on exercises

{% stepper %}
{% step %}
Take your Module 19 Helm chart and apply every row of the checklist. Keep a list of what you changed.
{% endstep %}
{% step %}
On kind, `kubectl drain learn-worker --ignore-daemonsets` with and without a PDB. See how the PDB blocks evictions that would drop below `minAvailable`.
{% endstep %}
{% step %}
(Optional, costs a few dollars) Create an EKS cluster with eksctl, install the AWS Load Balancer Controller, deploy your chart with an ALB Ingress, then delete everything the same day.
{% endstep %}
{% endstepper %}

## Common mistakes

- **Single replica "because it's small"** — every node upgrade becomes an outage.
- **PDB with `minAvailable` equal to replicas** — node drains hang forever. Use `maxUnavailable: 1`.
- **Skipping upgrades** until the version is out of support, then needing to jump several versions under pressure.
- **Too many tiny clusters or one giant one.** A common shape: one prod cluster, one non-prod cluster with namespaces per environment.
- **Not testing restores.** A backup you've never restored is a hope, not a backup.
