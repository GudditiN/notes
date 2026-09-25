---
description: "More Pods when busy, more nodes when Pods don't fit, fewer of both when quiet."
icon: arrows-up-down
---

# 20. Autoscaling

{% hint style="info" %}
**Level:** Intermediate → Advanced · **Part:** Operating in production
{% endhint %}

## Simple explanation

Kubernetes scales at two levels. **Pod autoscaling** changes how many copies of your app run (HPA) or how big each one is (VPA). **Node autoscaling** adds or removes machines when Pods can't be scheduled or nodes sit empty (Cluster Autoscaler, Karpenter). They work together: HPA creates Pods, some stay Pending for lack of room, the node autoscaler adds a node, the Pods land.

## Key concepts

| Concept | What it means |
| --- | --- |
| metrics-server | Collects CPU/memory from kubelets. Required for HPA on CPU/memory and `kubectl top`. |
| HPA | HorizontalPodAutoscaler: adjusts replicas to hit a target, e.g. 70% of *requested* CPU. |
| Formula | `desired = ceil(current × currentMetric / target)`. 4 Pods at 140% CPU with target 70% → 8 Pods. |
| Behavior | Scale-up/scale-down rate limits and stabilization windows to prevent flapping. |
| VPA | VerticalPodAutoscaler: recommends or sets requests. Use in "Off" (recommend) mode to right-size. |
| KEDA | Event-driven autoscaling on queue length (SQS, Kafka), cron, Prometheus queries; can scale to zero. |
| Cluster Autoscaler / Karpenter | Node scaling. Karpenter (AWS) picks instance types per workload and provisions in seconds. |
| PodDisruptionBudget | Limits how many Pods can be evicted at once during node scale-down or upgrades. |

## Flow

<figure><img src="../.gitbook/assets/m13-diagram-1.svg" alt="Autoscaling: Flow"><figcaption></figcaption></figure>

## Setup on kind

```bash
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
  --set 'args={--kubelet-insecure-tls}'        # needed on kind only
kubectl top nodes
```

## YAML examples

{% code title="php-apache.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: php-apache }
spec:
  selector: { matchLabels: { app: php-apache } }
  template:
    metadata: { labels: { app: php-apache } }
    spec:
      containers:
        - name: php-apache
          image: registry.k8s.io/hpa-example
          ports: [{ containerPort: 80 }]
          resources:
            requests: { cpu: 200m }     # HPA % is relative to this — REQUIRED
            limits:   { cpu: 500m }
---
apiVersion: v1
kind: Service
metadata: { name: php-apache }
spec:
  selector: { app: php-apache }
  ports: [{ port: 80 }]
```
{% endcode %}

{% code title="hpa.yaml" %}
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: php-apache }
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: php-apache
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 50 }
    - type: Resource
      resource:
        name: memory
        target: { type: Utilization, averageUtilization: 80 }
  behavior:
    scaleUp:
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]    # at most double every 30s
    scaleDown:
      stabilizationWindowSeconds: 300                                   # wait 5 min before shrinking
      policies: [{ type: Pods, value: 1, periodSeconds: 60 }]
```
{% endcode %}

{% code title="pdb.yaml" %}
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: php-apache }
spec:
  minAvailable: 1
  selector: { matchLabels: { app: php-apache } }
```
{% endcode %}

{% code title="keda-sqs.yaml" %}
```yaml
# KEDA: scale workers on SQS queue depth (0 when empty)
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: { name: worker }
spec:
  scaleTargetRef: { name: worker }
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.ap-south-1.amazonaws.com/111122223333/jobs
        queueLength: "10"          # 1 Pod per 10 messages
        awsRegion: ap-south-1
      authenticationRef: { name: keda-aws }
```
{% endcode %}

## Important commands

```bash
kubectl autoscale deploy php-apache --cpu-percent=50 --min=1 --max=10   # quick HPA
kubectl get hpa -w
kubectl describe hpa php-apache            # events show every scaling decision
kubectl top pods
kubectl get pdb
```

## Hands-on exercises

{% stepper %}
{% step %}
Install metrics-server, apply `php-apache.yaml` and `hpa.yaml`.
{% endstep %}
{% step %}
Generate load: `kubectl run load --image=busybox:1.36 --rm -it --restart=Never -- sh -c "while true; do wget -q -O- http://php-apache; done"`. In another terminal, `kubectl get hpa -w`. Watch replicas climb.
{% endstep %}
{% step %}
Stop the load. Notice scale-down waits 5 minutes (stabilization window).
{% endstep %}
{% step %}
Remove `resources.requests` and reapply. `kubectl describe hpa` shows it can't compute utilization. Put them back.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **HPA shows `<unknown>/50%`** — metrics-server missing, or containers have no CPU request.
- **HPA and a fixed `replicas:` in Git fight each other** — every deploy resets the count. Remove `replicas` from the Deployment once an HPA owns it (or let Helm omit it when autoscaling is on).
- **Flapping** — tune `behavior` and stabilization windows.
- **HPA and VPA both on CPU** for the same Deployment conflict. Use VPA in recommend mode only.
- **maxReplicas higher than the database can handle** — scaling the app can exhaust DB connections. Use a pooler (PgBouncer / RDS Proxy) and size max replicas with that in mind.
