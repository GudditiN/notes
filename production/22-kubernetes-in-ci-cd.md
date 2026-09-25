---
description: "From git push to a verified rollout, with push and GitOps pipelines."
icon: code-branch
---

# 22. Kubernetes in CI/CD

{% hint style="info" %}
**Level:** Advanced · **Part:** Operating in production
{% endhint %}

## Simple explanation

A Kubernetes pipeline does four things: build and test the image, push it with an immutable tag, update the manifests (or Helm values) with that tag, and apply them to the cluster. There are two ways to do the last step.

| Model | How it works | Pros | Cons |
| --- | --- | --- | --- |
| **Push** (CI deploys) | GitHub Actions runs `helm upgrade` against the cluster. | Simple, one tool, familiar if you use Actions + CDK today. | CI needs cluster credentials; drift isn't corrected. |
| **Pull / GitOps** | CI commits the new tag to a config repo; Argo CD or Flux in the cluster syncs it. | Git is the single source of truth, auto drift correction, easy audit and rollback (git revert), no cluster creds in CI. | One more system to run. |

Start with push to learn the moving parts; move to GitOps when you have more than a couple of services or environments.

## Key concepts

| Concept | What it means |
| --- | --- |
| Immutable tags | Tag images with the git SHA. Never redeploy `latest`. |
| OIDC to AWS | GitHub Actions assumes an IAM role without stored keys; EKS access entries map that role to Kubernetes RBAC. |
| Environments | Separate namespaces or clusters per env, with promotion (dev → staging → prod) through PRs or approvals. |
| Verification | `helm --atomic --wait` or `kubectl rollout status`; fail the pipeline if the rollout doesn't become healthy. |
| Policy checks | Lint and validate before deploy: `helm lint`, `kubeconform`, `trivy`, Kyverno/Conftest. |

## Flow

<figure><img src="../.gitbook/assets/m15-diagram-1.svg" alt="Kubernetes in CI/CD: Flow"><figcaption></figcaption></figure>

## Example: GitHub Actions → local kind cluster (runs in CI, great for integration tests)

{% code title=".github/workflows/k8s-test.yaml" %}
```yaml
name: k8s-integration
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: helm/kind-action@v1
        with: { cluster_name: ci }
      - name: Build and load image
        run: |
          docker build -t myapp:${{ github.sha }} .
          kind load docker-image myapp:${{ github.sha }} --name ci
      - name: Validate manifests
        run: |
          helm lint ./chart
          helm template ./chart --set image.repository=myapp,image.tag=${{ github.sha }} \
            | docker run --rm -i ghcr.io/yannh/kubeconform:latest -strict -summary
      - name: Deploy
        run: |
          helm upgrade --install myapp ./chart \
            --set image.repository=myapp,image.tag=${{ github.sha }},image.pullPolicy=Never \
            --wait --timeout 3m
      - name: Smoke test
        run: |
          kubectl port-forward svc/myapp 8080:80 &
          sleep 3
          curl -fsS http://localhost:8080/healthz
      - name: Debug on failure
        if: failure()
        run: |
          kubectl get all -A
          kubectl describe pods
          kubectl logs -l app.kubernetes.io/name=myapp --tail=100
```
{% endcode %}

## Example: GitHub Actions → EKS (push model, OIDC, no stored keys)

{% code title=".github/workflows/deploy.yaml" %}
```yaml
name: deploy
on:
  push:
    branches: [main]
permissions:
  id-token: write        # for OIDC
  contents: read
env:
  AWS_REGION: ap-south-1
  ECR_REPO: myapp
  CLUSTER: prod-eks
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production                 # require manual approval in repo settings
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/github-deployer
          aws-region: ${{ env.AWS_REGION }}
      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2
      - name: Build and push
        run: |
          IMAGE=${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPO }}:${{ github.sha }}
          docker build -t $IMAGE .
          docker push $IMAGE
      - name: Scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPO }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: "1"
      - name: Deploy
        run: |
          aws eks update-kubeconfig --name $CLUSTER --region $AWS_REGION
          helm upgrade --install myapp ./chart -n prod \
            -f chart/values-prod.yaml \
            --set image.repository=${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPO }} \
            --set image.tag=${{ github.sha }} \
            --atomic --wait --timeout 5m
```
{% endcode %}

## Example: GitOps with Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl -n argocd port-forward svc/argocd-server 8443:443    # https://localhost:8443, user admin
```

{% code title="argocd-app.yaml" %}
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/GudditiN/myapp-config.git
    targetRevision: main
    path: charts/myapp
    helm:
      valueFiles: [values-prod.yaml]
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true        # delete resources removed from Git
      selfHeal: true     # undo manual kubectl edits
    syncOptions: [CreateNamespace=true]
```
{% endcode %}

CI's only job in GitOps: build, push, then update `image.tag` in `values-prod.yaml` via a commit or PR (or let Argo CD Image Updater do it).

## Hands-on exercises

{% stepper %}
{% step %}
Add the kind-based workflow to a repo with a Dockerfile and chart. Open a PR and watch it deploy and smoke-test inside CI.
{% endstep %}
{% step %}
Install Argo CD on your kind cluster, point an Application at a public repo with your chart, change `replicaCount` in Git and watch it sync.
{% endstep %}
{% step %}
Run `kubectl scale deploy myapp --replicas=9` with `selfHeal: true`. Argo CD reverts it within seconds.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **Deploying `:latest`** — nothing changes in the spec, so no rollout happens. Always use the SHA.
- **Pipeline "succeeds" but app is broken** — you didn't wait for rollout. Use `--atomic --wait` or `kubectl rollout status --timeout`.
- **EKS `Unauthorized` from CI** — the IAM role isn't mapped via an EKS access entry (or legacy `aws-auth` ConfigMap).
- **Argo CD shows OutOfSync forever** — a controller mutates a field (e.g. HPA changing replicas). Use `ignoreDifferences` for that field.
- **Secrets in the config repo** — use External Secrets or Sealed Secrets; GitOps repos are widely readable.
