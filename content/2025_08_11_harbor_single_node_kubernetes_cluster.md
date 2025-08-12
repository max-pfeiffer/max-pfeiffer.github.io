Title: Harbor on a Kubernetes Single Node Cluster using Talos Linux and Proxmox VE
Description: I built a turnkey solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Summary: I built a turnkey solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Date: 2025-08-11 16:00
Author: Max Pfeiffer
Lang: en
Keywords: Harbor, Image Registry Cache, Kubernetes, Talos Linux, OpenTofu, Proxmox  
Image: https://max-pfeiffer.github.io/images/2025_08_11_harbor_single_node_kubernetes_cluster.png

While running and maintaining my Kubernetes cluster, I was facing a chicken-egg problem:
when updating/restarting Kubernetes nodes, I hit the image pull limit of different container registries regularly.
My applications in the cluster were not coming up any more causing a lot of issues. Also, I was experiencing latency
and long transfer times for pulling images from remote registries. So I was considering running some image
cache locally.

It had to be solved outside my Kubernetes cluster because configuring an image cache is a Kubernetes node-specific
configuration depending on the container runtime and registry you use. So firing up an image cache in the already
existing Kubernetes cluster is pointless. 

When you run a large number of applications in your Kubernetes cluster, you will experience a wide diversity of image
registries being used. So this solution also needs to support caching multiple image registries.
The most common ones are:

* [Docker Hub](https://hub.docker.com/)
* [GitHub](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
* [Quay](https://quay.io/)

So just firing up a Docker registry on some other (virtual) machine will just not cut it. Looking around for some
more professional, cloud native solutions, I ended up sticking with [Harbor](https://goharbor.io/) eventually.
[Harbor supports a wide range of image registries.](https://goharbor.io/docs/2.4.0/install-config/harbor-compatibility-list/)
Plus, it's a software with cloud native design and is easily installed on Kubernetes using the
[provided Helm chart](https://github.com/goharbor/harbor-helm). There is also a
[terraform-provider-harbor](https://github.com/goharbor/terraform-provider-harbor) maintained by the project's members.

![2025_08_11_harbor_single_node_kubernetes_cluster.png]({static}/images/2025_08_11_harbor_single_node_kubernetes_cluster.png)

## Kubernetes Single Node Cluster
I want to have all my infrastructure as code (IaC). So I choose to deploy [Harbor](https://goharbor.io/) on a
Kubernetes installation because I can do installation and configuration of [Harbor](https://goharbor.io/) and it's
dependencies in a fully declarative way.
A great option is to use [Talos Linux](https://www.talos.dev/) as a base operating system, because you can install
and configure the Kubernetes installation declarative with it as well.
I decided against using [ArgoCD](https://argoproj.github.io/cd/) because I only wanted to run Harbor inside the cluster,
and it seemed to be an overkill to use it for just deploying a single application.  

## Design Decisions
As I want to build a declarative, standalone, turnkey solution, I had to make the following design decisions:

* IaC: every piece of infrastructure is declarative
  * Proxmox VE: installation of this hypervisor itself is a manual task, but everything else can be done fully
    declarative using APIs and a [Terraform/OpenTofu provider](https://github.com/Telmate/terraform-provider-proxmox) 
  * Talos Linux/Kubernetes: both can be configured fully declarative using APIs and
    [Terraform/OpenTofu providers](https://github.com/siderolabs/terraform-provider-talos)
* Local storage for Kubernetes applications on the node: data storage needs to happen without other infrastructure
  dependencies like NFS or Ceph. Providing storage for a Kubernetes cluster can be rather complex if it needs to be
  highly available, and not everyone has a NFS share available [or runs a Ceph cluster like me]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md).
  So I choose to statically provision the volumes on the node with Talos Linux and configured
  [local PersistentVolumes](https://kubernetes.io/docs/concepts/storage/volumes/#local).
  This way it can be installed and run anywhere. Plus, I consider the data which will be stored here as
  ephemeral, as the container images can be easily pulled or reproduced again.
* Certificate authority (CA): bootstrapping and running a standalone CA is necessary to issue TLS certificates when
  deploying this in your local network environment only

# Harbor Turnkey
The result of these decisions is my new [Harbor Turnkey project](https://github.com/max-pfeiffer/harbor-turnkey) on
GitHub. It's meant to be used in a homelab, dev or test environment as it is not run on a highly available Kubernetes
installation and does not use highly available storage. But it can also easily be extended to support that.
I put together a solution which you can install on your Proxmox VE hypervisor using [OpenTofu](https://opentofu.org/)
in a couple of minutes. It requires:

* [Proxmox VE](https://www.proxmox.com/en/products/proxmox-virtual-environment/overview) with some resources available
  (default: 2 CPUs, 8GB RAM, 275GB disk space)
* [OpenTofu installed locally](https://opentofu.org/docs/intro/install/)
* [Step CLI installed locally](https://smallstep.com/docs/step-cli/installation/)
* Docker Hub account

Just follow the instructions in the [repository documentation](https://github.com/max-pfeiffer/harbor-turnkey),
and you will have your own image cache up and running in no-time.

Currently only caching Docker Hub and GitHub image registries are supported as this is what I mainly use. It's easy to
add other image repositories or other functionality. I would be grateful to receive pull requests if you do.

Overall, I would be happy to receive some feedback. Perhaps not everyone needs to have an own CA for issuing TLS
certificates when you run Harbor under a FQDN and uses [Let's Encrypt](https://letsencrypt.org/). A lot of things
could be made optional or more configurable.

## Using the Harbor Image Cache for your Kubernetes Cluster 
The last step is to configure the image cache for your Kubernetes nodes. As this is specific to the container runtime
and registry you are using, I need to exclude overall instructions here as this is going too far. For those using Talos
Linux for running their cluster, [this is straight forward and well documented](https://www.talos.dev/v1.10/talos-guides/configuration/pull-through-cache/#using-harbor-as-a-caching-registry).

An example machine configuration for Talos linux for using the Harbor image cache would look like this:
```yaml
  registries:
    mirrors:
      docker.io:
        endpoints:
          - https://harbor.local/v2/docker-hub-cache
        overridePath: true
      ghcr.io:
        endpoints:
          - https://harbor.local/v2/github-cache
        overridePath: true
    config:
      harbor.local:
        tls:
            ca: |
              -----BEGIN CERTIFICATE-----
              MIIBljCCAT2gAwIBAgIQSWXB5E3zSqrayTeeY0+17zAKBggqhkjOPQQDAjAqMQ8w
              DQYDVQQKEwZIYXJib3IxFzAVBgNVBAMTDkhhcmJvciBSb290IENBMB4XDTI1MDgx
              MTA5MjAwNFoXDTM1MDgwOTA5MjAwNFowKjEPMA0GA1UEChMGSGFyYm9yMRcwFQYD
              VQQDEw5IYXJib3IgUm9vdCBDQTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABNZ0
              n6lg9KUfFtZbKMxi6+FJeZamv0+cXsD/WCQlynyB8p0+CThqk5NTXU2ih90ifWTn
              PrJN8pZqmkZlHaOvb8ujRTBDMA4GA1UdDwEB/wQEAwIBBjASBgNVHRMBAf8ECDAG
              AQH/AgEBMB0GA1UdDgQWBBR5k8DjpQM5BgHSvITdMYhmJYXsCDAKBggqhkjOPQQD
              AgNHADBEAiBRJ4fWVxh36Jsy1ZAIBeJrgxR0PnWLGxgwW7GSeWMl5wIgQMhU7+03
              Qbe4oasc6VbesYbouqb1R0mjTUxGPlIvxn0=
              -----END CERTIFICATE-----
```
