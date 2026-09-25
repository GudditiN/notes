---
description: "The one command you'll type thousands of times, and how to read what it tells you."
icon: terminal
---

# 10. kubectl basics

{% hint style="info" %}
**Level:** Beginner · **Part:** Kubernetes foundations
{% endhint %}

## Simple explanation

`kubectl` is a command-line client for the Kubernetes API. Every command follows the same shape: `kubectl <verb> <resource> <name> [flags]`. Learn a handful of verbs and they work on every resource type.

It reads connection details from `~/.kube/config` (the *kubeconfig*). That file lists **clusters**, **users** (credentials), and **contexts** (a cluster + user + default namespace). Switching context switches which cluster you're talking to, so always check it before running destructive commands.

## Key concepts

| Concept | What it means |
| --- | --- |
| Imperative | Direct commands: `kubectl create deployment web --image=nginx`. Fast for experiments, not repeatable. |
| Declarative | `kubectl apply -f file.yaml`. The file is the truth; re-running it is safe. Use this for anything real. |
| Output formats | `-o wide`, `-o yaml`, `-o json`, `-o jsonpath=...`, `-o name`. |
| Selectors | `-l app=web` filters by label; works with get, delete, logs. |
| Dry run | `--dry-run=client -o yaml` generates YAML without creating anything — the fastest way to write manifests. |

## Flow: how a command travels

<figure><img src="../.gitbook/assets/m3-diagram-1.svg" alt="kubectl basics: Flow: how a command travels"><figcaption></figcaption></figure>

## Important commands

| Goal | Command |
| --- | --- |
| List things | `kubectl get pods`, `kubectl get all`, `kubectl get pods -A` |
| Watch live | `kubectl get pods -w` |
| Details + events | `kubectl describe pod NAME` |
| Create/update from file | `kubectl apply -f app.yaml` (or a folder: `-f k8s/`) |
| Preview changes | `kubectl diff -f app.yaml` |
| Delete | `kubectl delete -f app.yaml`, `kubectl delete pod NAME` |
| Logs | `kubectl logs NAME`, `-f` to follow, `--previous` for crashed container, `-c CONTAINER` |
| Shell into container | `kubectl exec -it NAME -- sh` |
| Reach a Pod from laptop | `kubectl port-forward pod/NAME 8080:80` |
| Copy files | `kubectl cp NAME:/path/file ./file` |
| Generate YAML | `kubectl create deployment web --image=nginx --dry-run=client -o yaml` |
| Field docs | `kubectl explain deployment.spec.strategy` |
| Change namespace default | `kubectl config set-context --current --namespace=dev` |
| Resource usage | `kubectl top pods` (needs metrics-server, Module 20) |

## YAML example: generate, then edit

```bash
kubectl create deployment web --image=nginx:1.27 --replicas=2 \
  --dry-run=client -o yaml > web.yaml
kubectl apply -f web.yaml
kubectl get deploy web -o yaml | less     # see spec AND status

# jsonpath: pull just the Pod IPs
kubectl get pods -l app=web -o jsonpath='{.items[*].status.podIP}'

# custom columns
kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,IP:.status.podIP
```

## Hands-on exercises

{% stepper %}
{% step %}
Run a throwaway Pod: `kubectl run tmp --image=busybox:1.36 --rm -it --restart=Never -- sh`. Inside, run `nslookup kubernetes.default`. Exit and confirm the Pod is gone.
{% endstep %}
{% step %}
Generate a Deployment YAML with `--dry-run`, change replicas to 3, apply it, then use `kubectl diff` after changing the image tag.
{% endstep %}
{% step %}
Use `kubectl explain pod.spec --recursive | less` and find the field that sets a container's working directory.
{% endstep %}
{% step %}
Port-forward to one nginx Pod and open `http://localhost:8080`.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Wrong context.** Put the context in your shell prompt (kube-ps1) or check with `kubectl config current-context` before any `delete`.
- **"No resources found"** — you're in the wrong namespace. Add `-n NAMESPACE` or `-A`.
- **Mixing `create` and `apply`** on the same object causes "AlreadyExists" or lost fields. Pick `apply` for everything tracked in Git.
- **Reading only `get` output.** When something's wrong, the answer is almost always in the *Events* section at the bottom of `kubectl describe`.
