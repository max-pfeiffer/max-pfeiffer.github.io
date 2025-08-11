Title: Harbor on a Kubernetes Single Node Cluster using Talos Linux and Proxmox VE
Description: I build a turnkey solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Summary: I build a turnkey solution for Harbor running on a Kubernetes single node cluster using Talos Linux and Proxmox VE
Date: 2025-08-11 16:00
Author: Max Pfeiffer
Lang: en
Keywords: Harbor, Image Registry Cache, Kubernetes, Talos Linux, OpenTofu, Proxmox  
Image: 

While running and maintaining my Kubernetes cluster, I was facing a chicken-egg problem:
when updating/restarting Kubernetes nodes, I hit the image pull limit of different container registries regularly.
My applications in the cluster were not coming up any more causing a lot of issues. Also, I was experiencing latency
and long waiting times for pulling images from remote registries. So I was considering running some container image
cache locally.

It had to be solved outside my Kubernetes cluster because configuring an image cache is a Kubernetes node-specific
configuration depending on the container runtime and registry you use. So firing up an image cache in the already
existing Kubernetes cluster is pointless. 

When you run a large number of applications in your Kubernetes cluster, you will experience a wide diversity of image
registries being used. So this solution also needs to support caching multiple container registries.
The most common ones are:

* [Docker Hub](https://hub.docker.com/)
* [GitHub](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
* [Quay](https://quay.io/)

So just firing up a Docker registry on some other (virtual) machine will just not cut it. Looking around for some
more professional, cloud native solutions, I ended up sticking with [Harbor](https://goharbor.io/) eventually.
[Harbor supports a wide range of image registries.](https://goharbor.io/docs/2.4.0/install-config/harbor-compatibility-list/)
Plus, it's software with cloud native design and easily installed on Kubernetes using the
[provided Helm chart](https://github.com/goharbor/harbor-helm). There is also a
[terraform-provider-harbor](https://github.com/goharbor/terraform-provider-harbor) maintained by the project's community.

## Kubernetes Single Node Cluster
I want to have all my infrastructure as code (IaC). So I choose to deploy [Harbor](https://goharbor.io/) on a
Kubernetes installation because I can do installation and configuration of [Harbor](https://goharbor.io/) and it's
dependencies in a fully declarative way.
A great option is to use [Talos Linux](https://www.talos.dev/) as a base operating system, because you can install
and configure the Kubernetes installation declarative with it as well.
I decided against using [ArgoCD](https://argoproj.github.io/cd/) because I only wanted to run Harbor inside the cluster,
and it seemed to be an overkill to use it for just deploying a single application.  

## Design Decisions
As I want to build a standalone, turnkey solution, I had to make the following design decisions:

* IaC: every piece of infrastructure is declarative
  * Proxmox VE: installation of this hypervisor itself is a manual task, but everything else can be done fully
    declarative using APIs and a Terraform/OpenTofu provider 
  * Talos Linux/Kubernetes: both can be configured fully declarative using APIs and Terraform/OpenTofu providers
* Local storage for Kubernetes applications on the node: data storage needs to happen without other infrastructure
  dependencies like NFS or Ceph. Providing storage for a Kubernetes cluster can be rather complex if it needs to be
  highly available, and not everyone has a NFS share available or runs a Ceph cluster like me. So I choose to statically
  provision the volumes on the node with Talos Linux and configured
  [local PersistentVolumes](https://kubernetes.io/docs/concepts/storage/volumes/#local).
  This way it can be installed and run anywhere. Plus, I consider the data which will be stored here as
  ephemeral, as the container images can be easily pulled or reproduced again.
* Certificate authority (CA): bootstrapping and running a standalone CA is necessary to issue TLS certificates 

# Harbor Turnkey
The result of these decisions is my new [Harbor Turnkey project](https://github.com/max-pfeiffer/harbor-turnkey) on
GitHub.

## Using the Harbor Image Cache for Kubernetes Cluster 
The last step is to configure the image cache for your Kubernetes nodes. As this is specific to the container runtime
and registry you are using, I need to exclude instructions here. For those using Talos Linux for running their cluster,
this is straight forward and well documented.
