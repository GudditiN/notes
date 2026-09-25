---
description: "What Kubernetes is, the problem it solves, and the parts inside a cluster."
icon: sitemap
---

# 8. Kubernetes fundamentals and architecture

{% hint style="info" %}
**Level:** Beginner · **Part:** Kubernetes foundations
{% endhint %}

{% hint style="success" %}
**Welcome to Part 2.** In Part 1 you learned to build images and run containers on one machine. Kubernetes runs those same images across many machines, and keeps them healthy for you.
{% endhint %}

## Simple explanation

A container (for example a Docker image running your API) packages an app with everything it needs. Running one container on one server is easy. Running 50 containers across 10 servers, restarting the ones that crash, rolling out new versions without downtime, and routing traffic to the healthy ones is hard. **Kubernetes (K8s)** is the system that does that work for you.

The core idea is **desired state**. You don't tell Kubernetes "start 3 containers". You write a file that says "there should always be 3 copies of this container running", hand it to the cluster, and Kubernetes keeps making reality match that file, forever. If a server dies, it notices that only 2 copies exist and starts a third somewhere else. This loop of *observe → compare → act* is called **reconciliation**, and every part of Kubernetes works this way.

{% hint style="info" %}
**Analogy**

Think of a thermostat. You set 22°C (desired state). The thermostat keeps measuring the room (actual state) and turns heating on or off until they match. Kubernetes controllers are thousands of tiny thermostats, one for each kind of thing you declare.
{% endhint %}

## Key concepts

| Concept | What it means |
| --- | --- |
| Cluster | A set of machines (nodes) managed as one unit by Kubernetes. |
| Node | One machine (VM or physical) in the cluster that runs your containers. |
| Control plane | The "brain": the components that store desired state and make decisions. |
| Pod | The smallest thing Kubernetes runs: one or more containers that share a network address and storage. |
| Object / resource | Anything you declare in YAML: Pod, Deployment, Service, Secret, and so on. |
| Manifest | A YAML file describing one or more objects. |
| Controller | A loop that watches one kind of object and makes reality match it. |
| Declarative | You describe *what* you want; Kubernetes figures out *how*. |

## Architecture

A cluster has two halves. The **control plane** holds the desired state and makes decisions. The **worker nodes** do the actual work of running containers. On EKS, GKE or AKS the cloud provider runs the control plane for you; you only manage nodes and workloads.

<figure><img src="../.gitbook/assets/cluster-architecture.svg" alt="Kubernetes cluster architecture: control plane and worker nodes"><figcaption><p>The control plane stores and decides. Worker nodes run your containers. Everything talks through the API server — components never talk to etcd or to each other directly.</p></figcaption></figure>

### Control plane: stores and decides

| Component | What it does | If it fails |
| --- | --- | --- |
| `kube-apiserver` | The only door into the cluster. Authenticates every request, checks RBAC, validates the object, saves it to etcd, and streams changes to watchers. | running apps keep running, but nothing can be changed or scheduled. |
| `etcd` | Key-value database holding every object's spec and status. Only the API server talks to it. | the cluster loses its memory. Back it up (managed for you on EKS). |
| `kube-scheduler` | Finds Pods with no node yet and picks the best node: enough free CPU and memory, matching affinity, tolerated taints. | new Pods stay Pending. |
| `controller-manager` | Dozens of reconcile loops (Deployment, ReplicaSet, Node, Job, EndpointSlice…) that make actual state match desired state. | crashed Pods aren't replaced, rollouts stop. |
| `cloud-controller-manager` | Calls the cloud provider to create load balancers, attach volumes, and label nodes with their zone. | new LoadBalancer Services and disks don't appear. |

### Worker node: runs your containers

| Component | What it does | If it fails |
| --- | --- | --- |
| `kubelet` | Agent on every node. Watches the API for Pods assigned to its node, tells the runtime to start them, runs probes, and reports status. | the node goes NotReady and its Pods are rescheduled elsewhere after ~5 minutes. |
| `container runtime` | containerd or CRI-O. Pulls images and runs containers. Any Docker-built image works. | containers on that node can't start. |
| `kube-proxy` | Programs iptables/IPVS rules so traffic to a Service IP lands on a healthy Pod. (Some CNIs like Cilium replace it.) | Service traffic from that node breaks. |
| `CNI plugin` | Gives every Pod an IP and connects Pods across nodes (AWS VPC CNI, Calico, Cilium). | Pods stay ContainerCreating or can't reach each other. |
| `Pods` | Your application containers, grouped. Disposable: they're replaced, never repaired. | — |

### What happens when you create a Deployment

This sequence is worth memorising: almost every "why is my Pod stuck?" question maps to one step failing.

<figure><img src="../.gitbook/assets/deployment-lifecycle.svg" alt="Sequence of events when a Deployment is created"><figcaption><p>Nobody calls anybody directly: each component watches the API server for objects it cares about, acts, and writes the result back.</p></figcaption></figure>

1. **You apply the file.** kubectl sends the Deployment to the API server over HTTPS.
2. **The API server stores it.** After authentication, RBAC and validation, the desired state is written to etcd. kubectl returns immediately — the rest happens asynchronously.
3. **The Deployment controller reacts.** It sees a Deployment with no ReplicaSet and creates one for the current Pod template.
4. **The ReplicaSet controller reacts.** It sees 0 of 3 Pods and creates 3 Pod objects. They exist only as records, with no node assigned.
5. **The scheduler places them.** For each unassigned Pod it filters nodes that fit, scores them, and writes the chosen node name onto the Pod.
6. **The kubelet notices.** The kubelet on that node sees a Pod now assigned to it.
7. **Containers start.** The kubelet asks containerd to pull the image and start the containers, then begins running probes.
8. **Status flows back.** The kubelet reports Running and, once the readiness probe passes, Ready. Only then do Services send it traffic.

| Stuck at step | What you'll see |
| --- | --- |
| 2 | kubectl error: `Forbidden` (RBAC) or a validation message |
| 4 | Deployment exists, no Pods: `kubectl describe rs` shows quota or admission errors |
| 5 | Pod `Pending`: "Insufficient cpu", untolerated taint, unbound PVC |
| 7 | `ImagePullBackOff`, `CreateContainerConfigError`, `CrashLoopBackOff` |
| 8 | `Running` but `0/1` Ready: failing readiness probe |

### Coming from AWS ECS? A quick map

| ECS / AWS term | Kubernetes equivalent |
| --- | --- |
| Cluster | Cluster |
| Task definition | Pod spec (inside a Deployment) |
| Task | Pod |
| Service (desired count) | Deployment (replicas) |
| ALB target group + listener rules | Service + Ingress |
| Cloud Map / service discovery | Service DNS (`svc.namespace.svc.cluster.local`) |
| Task role (IAM) | ServiceAccount (+ IRSA / Pod Identity on EKS) |
| Secrets Manager / SSM params in task def | Secret / ConfigMap (or External Secrets Operator) |
| Service Auto Scaling | HorizontalPodAutoscaler |
| Container health check | Liveness / readiness / startup probes |
| Fargate capacity | Node group / Karpenter / EKS Fargate profile |

The biggest mental shift: in ECS, AWS runs the control plane invisibly and gives you a fixed set of features. In Kubernetes the control plane is an open API, and almost everything (ingress, autoscaling, secrets sync, certificates) is a pluggable controller you choose and install.

## Important commands

```bash
kubectl cluster-info                 # where is the API server?
kubectl get nodes -o wide            # list machines in the cluster
kubectl get pods -n kube-system      # see control-plane and system Pods
kubectl api-resources                # every object type the cluster understands
kubectl explain pod.spec.containers  # built-in docs for any field
```

## YAML example: anatomy of every manifest

{% code title="anatomy.yaml" %}
```yaml
apiVersion: v1          # API group/version the object belongs to
kind: Pod               # what type of object
metadata:               # identity: name, namespace, labels, annotations
  name: hello
  labels:
    app: hello
spec:                   # desired state — what YOU want
  containers:
    - name: web
      image: nginx:1.27
# status:               # actual state — written by Kubernetes, never by you
```
{% endcode %}

Every object has these four top-level fields. `spec` is your wish; `status` is Kubernetes reporting back.

## Hands-on exercises

{% stepper %}
{% step %}
Draw the architecture diagram above on paper from memory. Label what breaks if each component disappears.
{% endstep %}
{% step %}
Write a one-paragraph explanation of "desired state vs actual state" as if to a non-engineer.
{% endstep %}
{% step %}
After Module 9, run `kubectl get pods -n kube-system` and match each Pod name to a component in the table.
{% endstep %}
{% endstepper %}

## Common mistakes and tips

- **Thinking of Pods as servers.** Pods are disposable. They get new IPs every time they restart. Never SSH into them to "fix" something; fix the YAML and re-apply.
- **Using Kubernetes when you don't need it.** For one or two small services, ECS Fargate, Cloud Run or a single VM is simpler. Kubernetes pays off with many services, multi-cloud needs, or a platform team.
- **Editing live objects by hand.** Changes made with `kubectl edit` are lost the next time someone applies the YAML. Keep YAML in Git as the source of truth.
