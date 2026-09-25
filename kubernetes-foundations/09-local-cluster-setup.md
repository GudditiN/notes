---
description: "A real cluster on your laptop in five minutes, for free."
icon: laptop-code
---

# 9. Setting up a local Kubernetes cluster

{% hint style="info" %}
**Level:** Beginner · **Part:** Kubernetes foundations
{% endhint %}

## Simple explanation

You don't need a cloud account to learn. Several tools run a full Kubernetes cluster inside Docker containers or a small VM on your laptop. What you learn there transfers directly to EKS, GKE or AKS, because the API is identical.

## Key concepts: pick a tool

| Tool | Best for | Notes |
| --- | --- | --- |
| **kind** (Kubernetes in Docker) | This course, CI pipelines, multi-node testing | Each node is a Docker container. Starts in ~30 s. Used by Kubernetes' own CI. |
| minikube | Beginners who want add-ons with one command | `minikube addons enable ingress`, built-in dashboard. |
| k3d / k3s | Low RAM machines, edge devices | Lightweight Kubernetes distribution. |
| Docker Desktop | Quickest single-node start on Mac/Windows | Tick "Enable Kubernetes" in settings. Single node only. |

This course uses **kind** because it supports multiple nodes (needed to see scheduling in action) and is what you'll use in CI later.

## Flow

<figure><img src="../.gitbook/assets/m2-diagram-1.svg" alt="Setting up a local Kubernetes cluster: Flow"><figcaption></figcaption></figure>

## Step-by-step installation

### 1. Install kubectl

{% tabs %}

{% tab title="macOS" %}

```bash
brew install kubectl
```

{% endtab %}

{% tab title="Linux" %}

```bash
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

{% endtab %}

{% tab title="Windows" %}

```powershell
winget install -e --id Kubernetes.kubectl
```

{% endtab %}

{% endtabs %}

```bash
kubectl version --client
```

### 2. Install kind

{% tabs %}

{% tab title="macOS" %}

```bash
brew install kind
```

{% endtab %}

{% tab title="Linux" %}

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

{% endtab %}

{% tab title="Windows" %}

```powershell
winget install -e --id Kubernetes.kind
```

{% endtab %}

{% endtabs %}

```bash
kind version
```

### 3. Create a multi-node cluster ready for Ingress

{% code title="kind-config.yaml" %}
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: learn
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:        # lets localhost:80/443 reach the Ingress controller (Module 16)
      - containerPort: 80
        hostPort: 80
      - containerPort: 443
        hostPort: 443
  - role: worker
  - role: worker
```
{% endcode %}

```bash
kind create cluster --config kind-config.yaml
kubectl get nodes
```

Expected output (versions will differ):

```text
NAME                  STATUS   ROLES           AGE   VERSION
learn-control-plane   Ready    control-plane   60s   v1.31.0
learn-worker          Ready    <none>          40s   v1.31.0
learn-worker2         Ready    <none>          40s   v1.31.0
```

### 4. Useful quality-of-life setup

```bash
# shell completion + short alias (bash; use ~/.zshrc for zsh)
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc

# optional power tools
brew install k9s kubectx helm   # terminal UI, context/namespace switcher, package manager
```

## Important commands

```bash
kind get clusters                    # list kind clusters
kind delete cluster --name learn     # throw it away and start fresh
kind load docker-image myapp:dev --name learn   # copy a local image into the cluster
kubectl config get-contexts          # which clusters can kubectl talk to?
kubectl config use-context kind-learn
```

## Hands-on exercises

{% stepper %}
{% step %}
Create the 3-node cluster above. Run `docker ps` and notice each node is a container.
{% endstep %}
{% step %}
Run `kubectl get pods -A` and identify etcd, the API server, scheduler and CoreDNS.
{% endstep %}
{% step %}
Delete the cluster and recreate it. Time how long it takes. Getting comfortable destroying clusters is a core skill.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **`The connection to the server localhost:8080 was refused`** — kubectl has no context. Run `kubectl config use-context kind-learn` or recreate the cluster.
- **Nodes stuck `NotReady`** — usually Docker is out of memory. Give Docker Desktop at least 6 GB RAM.
- **Port 80 already in use** — another web server is running. Stop it or change `hostPort` to 8080/8443.
- **`ErrImagePull` for your local image** — kind can't see your laptop's Docker images. Run `kind load docker-image` first.
