---
description: "How Kubernetes runs your containers and keeps the right number alive."
icon: cubes
---

# 11. Pods, ReplicaSets, and Deployments

{% hint style="info" %}
**Level:** Beginner · **Part:** Kubernetes foundations
{% endhint %}

## Simple explanation

A **Pod** wraps one or more containers that always run together on the same node and share an IP address. Most Pods have one container. On its own a Pod is fragile: if it dies or its node dies, nothing brings it back.

A **ReplicaSet** says "keep N identical Pods running". It counts Pods with matching labels and creates or deletes until the count is right.

A **Deployment** manages ReplicaSets for you, and adds versioned rollouts: change the image, and it creates a new ReplicaSet, scales it up while scaling the old one down, and can roll back. *You will almost always create Deployments, never bare Pods or ReplicaSets.*

## Key concepts

| Concept | What it means |
| --- | --- |
| Labels | Key/value tags on objects (`app: web`). Controllers find "their" Pods through labels. |
| Selector | The label query a controller uses. A Deployment's `selector` must match its Pod template labels. |
| Pod template | The blueprint inside a Deployment used to stamp out Pods. |
| Rolling update | Default strategy: replace Pods gradually. Tuned by `maxSurge` and `maxUnavailable`. |
| Recreate | Alternative strategy: kill all old Pods, then start new ones (brief downtime; needed when two versions can't coexist). |
| Pod lifecycle | Pending → ContainerCreating → Running → Succeeded/Failed. Container states: Waiting, Running, Terminated. |
| Init containers | Run to completion before the main containers start (e.g. wait for DB, run migrations). |
| Sidecar | A helper container in the same Pod (log shipper, proxy). |

## Architecture / flow

<figure><img src="../.gitbook/assets/m4-diagram-1.svg" alt="Pods, ReplicaSets, and Deployments: Architecture / flow"><figcaption></figcaption></figure>

During a rolling update with `maxSurge: 1` and `maxUnavailable: 0`, Kubernetes starts one v2 Pod, waits until it's Ready, removes one v1 Pod, and repeats. Capacity never drops.

## YAML examples

{% code title="pod.yaml" %}
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
  labels:
    app: web
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```
{% endcode %}

{% code title="deployment.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 3
  revisionHistoryLimit: 5            # old ReplicaSets kept for rollback
  selector:
    matchLabels:
      app: web                       # MUST match template labels below
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                    # at most 1 extra Pod during rollout
      maxUnavailable: 0              # never drop below 3 ready Pods
  template:
    metadata:
      labels:
        app: web
    spec:
      initContainers:
        - name: wait-a-bit
          image: busybox:1.36
          command: ["sh", "-c", "echo preparing; sleep 2"]
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:                 # explained in Module 15 — always set them
            requests: { cpu: 50m, memory: 64Mi }
            limits:   { memory: 128Mi }
```
{% endcode %}

## Important commands

```bash
kubectl apply -f deployment.yaml
kubectl get deploy,rs,pods -l app=web
kubectl scale deploy web --replicas=5
kubectl set image deploy/web nginx=nginx:1.27-alpine   # triggers a rollout
kubectl rollout status deploy/web
kubectl rollout history deploy/web
kubectl rollout undo deploy/web                        # back to previous revision
kubectl rollout undo deploy/web --to-revision=2
kubectl rollout restart deploy/web                     # restart all Pods (e.g. after Secret change)
kubectl rollout pause deploy/web / resume deploy/web
kubectl annotate deploy/web kubernetes.io/change-cause="bump to alpine"   # shows in history
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply `pod.yaml`, then `kubectl delete pod web-pod`. Notice it does not come back.
{% endstep %}
{% step %}
Apply `deployment.yaml`. In a second terminal run `kubectl get pods -w`. Delete one Pod and watch the ReplicaSet replace it within seconds.
{% endstep %}
{% step %}
Run `kubectl get pods -o wide` and see Pods spread across `learn-worker` and `learn-worker2`.
{% endstep %}
{% step %}
Change the image to `nginx:does-not-exist`. Watch the rollout stall (old Pods keep serving because `maxUnavailable: 0`). Fix with `kubectl rollout undo`.
{% endstep %}
{% step %}
Label trick: `kubectl label pod ONE_POD_NAME app=debug --overwrite`. The ReplicaSet no longer counts it and creates a replacement. You've "quarantined" a Pod for debugging.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ImagePullBackOff` / `ErrImagePull` | Typo in image, tag missing, private registry without credentials | `kubectl describe pod` → Events. Add `imagePullSecrets` for private registries. |
| `CrashLoopBackOff` | App exits on start (bad config, missing env, failed DB connect) | `kubectl logs POD --previous` |
| `Pending` forever | No node has enough CPU/memory, or scheduling rules can't be met | Events will say "Insufficient cpu". Lower requests or add nodes. |
| `selector does not match template labels` | Labels differ between `selector` and `template.metadata.labels` | Make them identical. Note: selector is immutable after creation. |
| `OOMKilled` | Container exceeded memory limit | Raise limit or fix the leak. |

- Using the `:latest` tag. Kubernetes can't tell a new version apart and rollbacks become meaningless. Use immutable tags (git SHA or semver).
