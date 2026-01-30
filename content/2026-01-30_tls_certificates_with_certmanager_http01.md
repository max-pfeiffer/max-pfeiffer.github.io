Title: Automating TLS Certificates with cert-manager and Gateway API using ACME HTTP01 Challenge
Description: Configuring automatic TLS certificate creation with cert-manger and the new Gateway API using the ACME HTTP01 challenge for my Kubernetes cluster 
Summary: Configuring automatic TLS certificate creation with cert-manger and the new Gateway API using the ACME HTTP01 challenge for my Kubernetes cluster
Date: 2026-01-30 12:00
Author: Max Pfeiffer
Lang: en
Keywords: Kubernetes, Gateway API, cert-manger, ACME, HTTP01
Image: https://max-pfeiffer.github.io/images/2026-01-14_switching_to_cilium_cni.png

For my non-production Kubernetes clusters [I was bootstrapping my own certificate authority]({filename}/2025-01-20_bootstrap_certificate_authority_for_kubernetes.md).
I am not too happy about that provisioning process as it is not fully automated currently, and you need to do add the
custom root CA wherever you need access to the cluster's resources. This is cumbersome and time-consuming.

As I also use AWS quite a bit, I noticed that registering certain domains is rather cheap there. With cheap, I mean
really cheap like 3$ a year. So I registered a couple domains there which I use for my Kubernetes clusters now.
I also like the option to manage all DNS settings for these domains with Route53 using OpenTofu. That way I can fully
automate the DNS setup for my Kubernetes clusters before I set up a cluster itself.

So I was looking in cert-manager docs how I could revise the creation of TLS certificates: there are good options to
[fully automate this with HTTP01 challenge using Ingress or Gateway API](https://cert-manager.io/docs/configuration/acme/http01/).
Another nice option would be using the DNS01 challenge with different DNS servers.
I saw that I can configure automated TLS certificate creation using the HTTP01 challenge only with Kubernetes resources
in my cluster without any external dependencies I choose to do that in the first place. The disadvantage of using the
HTTP01 challenge is that you cannot create wildcard TLS certificates with it. 

