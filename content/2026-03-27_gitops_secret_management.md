Title: Managing Kubernetes Secrets the GitOps Way with External Secrets Operator 
Description: Configuring External Secrets Operator in a Kubernetes Cluster    
Summary: Configuring External Secrets Operator in a Kubernetes Cluster
Date: 2026-03-27 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Kubernetes, GitOps, Secret, External Secrets Operator
Image: https://max-pfeiffer.github.io/images/2026-03-23_valheim_dedicated_server_with_docker.png

As a professional DevOps engineer I used a couple of different approaches for maintaining [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
in Kubernetes clusters in the past. Ranging from

* keeping them in an external secret store and adding them manually to the cluster
* over storing them encrypted in a git repo and kind of applying them in some kind of automated way
* to using Operators syncing Secrets with external Secret stores automatically 

The first two options were rather cumbersome and had security flaws.
As things are evolving constantly and I want to improve my secret management for the Kubernetes clusters at home,
I was looking recently at the current state of secret management solutions. Reading the
[ArgoCD documentation about secrets management](https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/)
I learned about their recommendations. I also did some further research to check what new solutions are out there.

## Secret Management Solutions
So what you want to do nowadays is destination cluster secret management. This way ArgoCD does not need to deal with 
[Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) itself, instead the Secret handling is done by
another [Operator](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/) especially dedicated to this task.
The usage of an external secrets management solution like [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
or [Hashicorp Vault](https://www.hashicorp.com/de/products/vault) has a couple of advantages:

* RBAC for secrets
* secure and encrypted location for your secrets
* versioning of secrets
* automatic secret rotation
* audit and monitoring of secret usage
* users do not have to deal with secret encryption

Plus in bigger companies dedicated teams usually run the secret management solution. They don't need to have
Kubernetes know how.

You can say that there are roughly three groups of [Operators](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
which deal with Secrets differently. 

1. Operators encrypting Secrets with keys stored inside the Kubernetes cluster, i.e. [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
2. Operators syncing Secrets with external Secret stores automatically, i.e. [External Secrets Operator](https://external-secrets.io/latest/) or [Vault Secrets Operator](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/vso)
3. CSI driver syncing Secrets with external Secret stores automatically and store them in [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/) i.e. [Kubernetes Secrets Store CSI Driver](https://github.com/kubernetes-sigs/secrets-store-csi-driver)

## Sealed Secrets
Using [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) you need two components:

1. the cluster-side operator
2. the client-side `kubeseal` CLI tool 

The `kubeseal` utility uses asymmetric crypto to encrypt secrets that only the controller can decrypt.
These encrypted secrets are encoded in a `SealedSecret` [Custom Resource](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/),
which you can see as a recipe for creating a secret. These `SealedSecret` are then safe to check into your git
repository.

This approach has some severe disadvantages. Users need to install and use the `kubeseal` CLI tool. For this you need
to have direct cluster access with the operator exposed for the `kubeseal` CLI tool. This is undesirable especially when
you run a multi tenant Kubernetes cluster. Also, the whole workflow for managing the secrets (CRUD operations) is
manually done in the first place. This is cumbersome and time consuming.
As you need to backup 


## External Secret Operators

## Kubernetes Secrets Store CSI Driver

In this video they do a demo for [External Secrets Operator](https://external-secrets.io/latest/) and the [Kubernetes Secrets Store CSI Driver](https://github.com/kubernetes-sigs/secrets-store-csi-driver).
This way you get a rough idea how they work and what the key differences are.

<iframe width="560" height="315" src="https://www.youtube.com/embed/EW25WpErCmA?si=M6q71U4xJ407Hjy5" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>


## Configuring External Secrets Operator

