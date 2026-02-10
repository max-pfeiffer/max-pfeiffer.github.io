Title: Automating TLS Certificates with cert-manager and Gateway API using ACME HTTP01 Challenge
Description: Configuring automatic TLS certificate generation with cert-manger and the new Gateway API using the ACME HTTP01 challenge for my Kubernetes clusters 
Summary: Configuring automatic TLS certificate generation with cert-manger and the new Gateway API using the ACME HTTP01 challenge for my Kubernetes clusters
Date: 2026-02-10 18:00
Author: Max Pfeiffer
Lang: en
Keywords: Kubernetes, Gateway API, cert-manger, ACME, HTTP01
Image: https://max-pfeiffer.github.io/images/2026-02-10_tls_certificates_with_certmanager_http01.png

For my non-production Kubernetes clusters [I was bootstrapping my own certificate authority]({filename}/2025-01-20_bootstrap_certificate_authority_for_kubernetes.md).
I am not too happy about that provisioning process as it is not fully automated currently, and you need to add the
custom root CA wherever you need access to the cluster's resources. This is cumbersome and time-consuming.

As I also use AWS quite a bit, I noticed that registering certain domains is rather cheap there. With cheap, I mean
really cheap like 3$ a year. So I registered a couple domains there which I use for my Kubernetes clusters now.
I also like the option to manage all DNS settings for these domains with [Route53](https://aws.amazon.com/de/route53/)
using OpenTofu. That way I can fully automate the DNS setup for my Kubernetes clusters before I set up a cluster itself.

So I was looking in [cert-manager](https://cert-manager.io/) docs how I could revise the creation of TLS certificates:
there are good options to [fully automate this with HTTP01 challenge using Ingress or Gateway API](https://cert-manager.io/docs/configuration/acme/http01/).
Another nice option would be using the DNS01 challenge with different DNS servers.
I saw that I can configure automated TLS certificate generation using the HTTP01 challenge with Kubernetes resources
in my cluster without any external dependencies. So I choose to do that in the first place. The disadvantage of using
the HTTP01 challenge is that you cannot create wildcard TLS certificates with it. 

[cert-manager](https://cert-manager.io/) offers the option to configure doing the HTTP01 challenge
[using an Ingress solver](https://cert-manager.io/docs/configuration/acme/http01/#configuring-the-http01-ingress-solver)
or [a Gateway API solver](https://cert-manager.io/docs/configuration/acme/http01/#configuring-the-http-01-gateway-api-solver).
As [I did switch my clusters to Cilium and Gateway API already]({filename}/2026-01-14_switching_to_cilium_cni.md)
I choose to go for the Gateway API solver option. Please be aware that Ingress API is already frozen and the
[official recommendation is to use Gateway API nowadays](https://kubernetes.io/docs/concepts/services-networking/ingress/).
So going for the Ingress solver is not really an option any more.

## HTTP01 Challenge
The HTTP01 challenge with Gateway API works like this:

![2026-02-10_tls_certificates_with_certmanager_http01.png]({static}/images/2026-02-10_tls_certificates_with_certmanager_http01.png)

The complete process is as rather complex:

1. You create a Certificate resource requesting a TLS certificate for a domain.
2. cert-manager detects the request and creates an ACME Order with the ACME server (e.g. Let’s Encrypt).
3. The ACME server returns an HTTP-01 Challenge for the domain.
4. cert-manager creates a temporary solver Pod that can serve the challenge response.
5. cert-manager creates a temporary Service pointing to the solver Pod.
6. cert-manager creates a temporary HTTPRoute that:
      * Matches /.well-known/acme-challenge/*
      * Forwards traffic to the solver Service
      * Attaches to the configured Gateway
7. DNS resolves the domain to the Gateway’s IP, and HTTP traffic reaches the Gateway.
8. The Gateway routes the ACME challenge request to the solver Pod via the HTTPRoute.
9. The ACME server performs an HTTP GET on the challenge URL and receives the expected response.
10. The ACME server validates the challenge and issues the TLS certificate.
11. cert-manager retrieves the certificate and stores it in a Kubernetes TLS Secret.
12. cert-manager deletes the temporary solver Pod, Service, and HTTPRoute.
13. The Gateway references the TLS Secret and starts serving HTTPS with the issued certificate.


## Configuration
In contrast, the configuration of the Kubernetes resources for this process is rather simple.

In the first place you need to install cert-manger with Gateway API feature gate enabled. If you use the
[official Helm chart]() just add this to your `values.yaml`:
```yaml
extraArgs:
  - "--enable-gateway-api"
```

As you usually do not allow any non-HTTPS traffic to your cluster, I would consider it as good practice to have a
special Gateway that specifically deals with these ACME challenges only. The only HTTPRoutes allowed to are the ones
for the HTTP01 solver Pod/Service in cert-manager namespace. So you would configure a Gateway like this:
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: acme
  namespace: network
spec:
  gatewayClassName: cilium
  addresses:
  - type: IPAddress
    value: 192.168.10.96
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            kubernetes.io/metadata.name: cert-manager
```
And route the incoming traffic for port 80 only to the specific IP address that you configured for it. You might also
need to adjust to your namespace and GatewayClass setup for the Gateway configuration.

A ClusterIssuer using this Gateway would be configured like this:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-http01
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your@example.email
    privateKeySecretRef:
      name: letsencrypt-http01-cluster-issuer-account-key
    solvers:
      - http01:
          gatewayHTTPRoute:
            parentRefs:
              - name: acme
                namespace: network
                sectionName: http
                kind: Gateway
```

That's basically all what you need to configure to be able to issue TLS certificates. Which I think is really great.
You could then create TLS certificates by configuring a Certificate resource like this in `network` namespace for
instance:
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd
  namespace: network
spec:
  secretName: your-secret-name
  issuerRef:
    name: letsencrypt-http01
    kind: ClusterIssuer
  dnsNames:
  - "example.org"
```
Please be aware that you need to have the DNS resolution for `example.org` configured in the first place. DNS and
routing for incoming network traffic on port 80 need to be configured so that requests for this domain will hit your
Gateway which you configured resolving these ACME challenges.

You can find a full working example in [the `argocd` section](https://github.com/max-pfeiffer/proxmox-talos-opentofu/tree/main/argocd)
of my turnkey Kubernetes cluster project.