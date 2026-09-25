---
description: "Push the project further, then tear it down."
icon: flag-checkered
---

# 5. Stretch goals and cleanup

## Stretch goals

{% stepper %}
{% step %}
Convert `k8s/` into a Helm chart with `values-dev.yaml` and `values-prod.yaml` (Module 19).
{% endstep %}
{% step %}
Add NetworkPolicies: only `notes-api` may reach `postgres` on 5432; only the ingress controller may reach `notes-api` (needs Calico or Cilium, Module 18).
{% endstep %}
{% step %}
Add a CronJob that runs `pg_dump` nightly to a second PVC (Module 24).
{% endstep %}
{% step %}
Write the GitHub Actions workflow from Module 22 that builds, loads into kind, deploys, and runs the Step 10 checks as a smoke test.
{% endstep %}
{% step %}
Install Argo CD and deploy the chart GitOps-style.
{% endstep %}
{% step %}
Deploy to EKS: swap the in-cluster Postgres for Aurora Serverless v2, the Secret for an ExternalSecret, the nginx Ingress for an ALB Ingress with an ACM cert, and add Karpenter. Delete it all the same day.
{% endstep %}
{% endstepper %}

## Clean up

```bash
kubectl delete namespace notes                 # app + DB (PVCs go too)
kind delete cluster --name learn               # everything
```
