---
description: "Every kubectl command from the course, in one place."
icon: list-check
---

# kubectl cheat sheet

| Task | Command |
| --- | --- |
| Current context | `kubectl config current-context` |
| Switch namespace | `kubectl config set-context --current --namespace=NS` |
| Everything in a namespace | `kubectl get all -n NS` |
| Pods on all namespaces, with nodes | `kubectl get pods -A -o wide` |
| Apply a folder | `kubectl apply -f k8s/` |
| Preview changes | `kubectl diff -f k8s/` |
| Generate YAML | `kubectl create deploy x --image=nginx --dry-run=client -o yaml` |
| Explain a field | `kubectl explain deploy.spec.template.spec.containers.resources` |
| Describe + events | `kubectl describe pod POD` |
| Recent events | `kubectl get events --sort-by=.lastTimestamp` |
| Logs (follow / previous) | `kubectl logs -f POD` / `kubectl logs POD --previous` |
| Shell | `kubectl exec -it POD -- sh` |
| Ephemeral debug container | `kubectl debug -it POD --image=nicolaka/netshoot --target=CONTAINER` |
| Port-forward | `kubectl port-forward svc/NAME 8080:80` |
| Scale | `kubectl scale deploy NAME --replicas=3` |
| Update image | `kubectl set image deploy/NAME CONTAINER=IMAGE:TAG` |
| Rollout status / undo / restart | `kubectl rollout status\|undo\|restart deploy/NAME` |
| Resource usage | `kubectl top pods --sort-by=cpu` |
| Permissions check | `kubectl auth can-i VERB RESOURCE --as=USER -n NS` |
| Decode a secret | `kubectl get secret S -o jsonpath='{.data.KEY}' \| base64 -d` |
| Node maintenance | `kubectl cordon\|drain\|uncordon NODE` |
| Throwaway debug Pod | `kubectl run tmp --image=busybox:1.36 --rm -it --restart=Never -- sh` |
| Helm install/upgrade | `helm upgrade --install REL CHART -n NS -f values.yaml --atomic --wait` |

## Where to go next

- **Certifications:** CKAD (developer focus) after Modules 8–20; CKA (administrator) after the whole course; CKS (security) later. They're hands-on exams, so the labs here are the right preparation.
- **Practice:** *killercoda.com* scenarios, and the "Kubernetes the Hard Way" guide to build a cluster by hand once.
- **Official docs:** kubernetes.io/docs — the Tasks section is excellent once you know the vocabulary.
- **Build:** move one of your real services onto EKS in a sandbox account using the capstone as a template.
