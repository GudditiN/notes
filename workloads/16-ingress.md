---
description: "One entry point that routes HTTP traffic by hostname and path."
icon: door-open
---

# 16. Ingress

{% hint style="info" %}
**Level:** Intermediate · **Part:** Running real workloads
{% endhint %}

## Simple explanation

An **Ingress** is a set of HTTP routing rules: "requests to `shop.example.com/api` go to the `api` Service, everything else to `web`". The rules do nothing by themselves. An **Ingress controller** (ingress-nginx, Traefik, AWS Load Balancer Controller) reads them and configures a real proxy or cloud load balancer. It also terminates TLS.

One Ingress controller + one load balancer can serve dozens of services, which is far cheaper than a LoadBalancer Service per app. On AWS, the AWS Load Balancer Controller turns each Ingress (or group of Ingresses) into an ALB — the same ALB you'd hand-build for ECS.

{% hint style="info" %}
**Gateway API**

The newer *Gateway API* (Gateway, HTTPRoute) is the successor to Ingress, with richer routing and role separation. Learn Ingress first because it's everywhere; look at Gateway API in Module 24.
{% endhint %}

## Key concepts

| Concept | What it means |
| --- | --- |
| IngressClass | Which controller handles this Ingress (`ingressClassName: nginx` or `alb`). |
| Host rules | Route by domain name (virtual hosting). |
| Path rules | `pathType: Prefix` (matches `/api/*`) or `Exact`. |
| TLS | References a `kubernetes.io/tls` Secret. cert-manager can create and renew it from Let's Encrypt automatically. |
| Annotations | Controller-specific options: rewrites, rate limits, body size, ALB settings. |

## Architecture / flow

<figure><img src="../.gitbook/assets/ingress-routing.svg" alt="How an Ingress routes HTTP traffic"><figcaption><p>① The request reaches one load balancer. ② It forwards to the Ingress controller. ③ The controller matches host and path against your Ingress rules. ④ The chosen Service sends it to a Ready Pod.</p></figcaption></figure>

<table data-view="cards"><thead><tr><th></th><th></th></tr></thead><tbody><tr><td><strong>Ingress object</strong></td><td>Just rules in YAML: which host and path go to which Service. It does nothing alone.</td></tr><tr><td><strong>Ingress controller</strong></td><td>A Pod (or cloud integration) that reads the rules and configures a real proxy or ALB.</td></tr><tr><td><strong>Services behind it</strong></td><td>Normal ClusterIP Services. The controller routes to their Ready endpoints.</td></tr></tbody></table>

## Install an Ingress controller on kind

```bash
kubectl apply -f https://kind.sigs.k8s.io/examples/ingress/deploy-ingress-nginx.yaml
kubectl wait -n ingress-nginx --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=120s
```

## YAML examples

{% code title="two-apps.yaml" %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: api }
spec:
  replicas: 2
  selector: { matchLabels: { app: api } }
  template:
    metadata: { labels: { app: api } }
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0
          args: ["-text=hello from api", "-listen=:5678"]
          ports: [{ containerPort: 5678 }]
---
apiVersion: v1
kind: Service
metadata: { name: api }
spec:
  selector: { app: api }
  ports: [{ port: 80, targetPort: 5678 }]
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: web }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0
          args: ["-text=hello from web", "-listen=:5678"]
          ports: [{ containerPort: 5678 }]
---
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  selector: { app: web }
  ports: [{ port: 80, targetPort: 5678 }]
```
{% endcode %}

{% code title="ingress.yaml" %}
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  rules:
    - host: shop.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service: { name: api, port: { number: 80 } }
          - path: /
            pathType: Prefix
            backend:
              service: { name: web, port: { number: 80 } }
```
{% endcode %}

{% code title="ingress-tls-certmanager.yaml" %}
```yaml
# Production: TLS from Let's Encrypt via cert-manager
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts: [shop.example.com]
      secretName: shop-tls           # cert-manager creates and renews this
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: web, port: { number: 80 } } }
```
{% endcode %}

{% code title="ingress-aws-alb.yaml" %}
```yaml
# EKS: AWS Load Balancer Controller creates an ALB
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-south-1:111122223333:certificate/abcd
    alb.ingress.kubernetes.io/group.name: shared-alb        # many Ingresses share one ALB
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
spec:
  ingressClassName: alb
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: web, port: { number: 80 } } }
```
{% endcode %}

## Important commands

```bash
kubectl get ingressclass
kubectl get ingress
kubectl describe ingress shop
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller
curl -H "Host: shop.local" http://localhost/api       # test without editing /etc/hosts
echo "127.0.0.1 shop.local" | sudo tee -a /etc/hosts  # or map the name permanently
```

## Hands-on exercises

{% stepper %}
{% step %}
Install ingress-nginx, apply `two-apps.yaml` and `ingress.yaml`. Curl `/` and `/api` with the Host header.
{% endstep %}
{% step %}
Add a second host, `admin.local`, that routes everything to `api`.
{% endstep %}
{% step %}
Create a self-signed cert with `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=shop.local"`, store it as a TLS Secret, add a `tls:` block and test with `curl -k https://shop.local`.
{% endstep %}
{% step %}
Scale `api` to 0 and curl `/api`. You get a 503 from nginx — learn to recognize it.
{% endstep %}
{% endstepper %}

## Common mistakes and troubleshooting

- **404 from the controller** — host or path doesn't match, or `ingressClassName` is missing so no controller picked it up.
- **503 Service Unavailable** — the backend Service has no Ready endpoints.
- **502 Bad Gateway** — endpoints exist but the app refuses the connection: wrong `targetPort` or app crashing.
- **Path rewrite surprises** — the app receives `/api/items`, not `/items`. Either make the app handle the prefix or use the controller's rewrite annotation.
- **ALB never appears on EKS** — AWS Load Balancer Controller not installed, IAM permissions missing, or subnets lack `kubernetes.io/role/elb` tags. Check the controller's logs.
