---
description: "Data that survives Pod restarts, and when it shouldn't live in the cluster at all."
icon: hard-drive
---

# 14. Volumes and persistent storage

{% hint style="info" %}
**Level:** Intermediate · **Part:** Running real workloads
{% endhint %}

## Simple explanation

A container's filesystem is wiped every time it restarts. **Volumes** attach storage to a Pod. Some volumes live only as long as the Pod (scratch space); **persistent** volumes outlive Pods, so a database Pod can be rescheduled and find its data waiting.

Kubernetes separates *asking* for storage from *providing* it. Your app files a **PersistentVolumeClaim** (PVC) — "I need 10 GiB of fast disk". A **StorageClass** knows how to create that disk (an EBS gp3 volume on AWS, a local folder in kind) and produces a **PersistentVolume** (PV) bound to your claim.

## Key concepts

| Concept | What it means |
| --- | --- |
| emptyDir | Empty folder created with the Pod, deleted with it. Shared between containers in the Pod. Can be RAM-backed (`medium: Memory`). |
| hostPath | A folder on the node. Avoid in real apps — ties the Pod to one node and is a security risk. |
| PV | A piece of storage in the cluster (cluster-scoped). |
| PVC | A request for storage (namespaced). Pods reference PVCs, never PVs. |
| StorageClass | A "type" of storage with a provisioner, e.g. `ebs.csi.aws.com` with `type: gp3`. Enables dynamic provisioning. |
| Access modes | `ReadWriteOnce` (one node — EBS), `ReadWriteOncePod`, `ReadOnlyMany`, `ReadWriteMany` (many nodes — EFS, NFS). |
| Reclaim policy | `Delete` destroys the disk when the PVC is deleted; `Retain` keeps it. Use Retain for anything precious. |
| StatefulSet | Like a Deployment but Pods get stable names (`db-0`, `db-1`) and each gets its own PVC via `volumeClaimTemplates`. |
| CSI driver | Plugin that connects Kubernetes to a storage system (EBS CSI, EFS CSI). |

## Architecture / flow

<figure><img src="../.gitbook/assets/m7-diagram-1.svg" alt="Volumes and persistent storage: Architecture / flow"><figcaption></figcaption></figure>

## YAML examples

{% code title="emptydir.yaml" %}
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: shared-scratch
spec:
  containers:
    - name: writer
      image: busybox:1.36
      command: ["sh", "-c", "while true; do date >> /data/log.txt; sleep 5; done"]
      volumeMounts: [{ name: scratch, mountPath: /data }]
    - name: reader
      image: busybox:1.36
      command: ["sh", "-c", "tail -f /data/log.txt"]
      volumeMounts: [{ name: scratch, mountPath: /data }]
  volumes:
    - name: scratch
      emptyDir: {}
```
{% endcode %}

{% code title="pvc.yaml" %}
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: notes-data
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: standard      # kind's default; "gp3" on EKS
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notes
spec:
  replicas: 1                     # RWO volume → only one Pod can mount it
  strategy: { type: Recreate }    # avoid two Pods fighting over the disk during rollout
  selector: { matchLabels: { app: notes } }
  template:
    metadata: { labels: { app: notes } }
    spec:
      containers:
        - name: app
          image: busybox:1.36
          command: ["sh", "-c", "echo boot at $(date) >> /data/boots.txt; cat /data/boots.txt; sleep 3600"]
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: notes-data
```
{% endcode %}

{% code title="storageclass-aws-gp3.yaml" %}
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer   # create the disk in the AZ where the Pod lands
```
{% endcode %}

{% code title="statefulset-postgres.yaml" %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: pg
spec:
  clusterIP: None                 # headless: gives pg-0.pg DNS names
  selector: { app: pg }
  ports: [{ port: 5432 }]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pg
spec:
  serviceName: pg
  replicas: 1
  selector: { matchLabels: { app: pg } }
  template:
    metadata: { labels: { app: pg } }
    spec:
      containers:
        - name: postgres
          image: postgres:16
          env:
            - name: POSTGRES_PASSWORD
              value: devpassword  # use a Secret in real life (see project)
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports: [{ containerPort: 5432 }]
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:           # one PVC per replica: data-pg-0, data-pg-1...
    - metadata: { name: data }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 2Gi } }
```
{% endcode %}

## Important commands

```bash
kubectl get storageclass
kubectl get pv,pvc
kubectl describe pvc notes-data            # why is it Pending?
kubectl patch pvc notes-data -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'  # expand
kubectl exec -it pg-0 -- psql -U postgres
```

## Hands-on exercises

{% stepper %}
{% step %}
Apply `emptydir.yaml` and run `kubectl logs shared-scratch -c reader -f`. Two containers, one folder.
{% endstep %}
{% step %}
Apply `pvc.yaml`. Delete the notes Pod three times. Each new Pod's log shows every previous boot — the data persisted.
{% endstep %}
{% step %}
Deploy the Postgres StatefulSet, create a table, delete `pg-0`, and confirm the table is still there.
{% endstep %}
{% step %}
Delete the StatefulSet and notice the PVC `data-pg-0` remains. Kubernetes never deletes StatefulSet volumes automatically.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **PVC stuck `Pending`** — no default StorageClass, wrong `storageClassName`, or CSI driver not installed (EKS needs the EBS CSI add-on). With `WaitForFirstConsumer`, Pending is normal until a Pod uses it.
- **`Multi-Attach error`** — an RWO volume can't attach to two nodes. Use `replicas: 1` + `Recreate`, a StatefulSet, or RWX storage (EFS).
- **Pod stuck in another AZ** — EBS volumes are zonal. Keep node groups in every AZ your volumes use.
- **Running production databases in-cluster without a reason.** Managed Aurora/RDS gives backups, failover and patching for free. Run databases in Kubernetes only when you have operators and on-call experience for it.
- **`Permission denied` on mounted volume** — set `securityContext.fsGroup` so the volume is writable by the container's user.
