Title: Velero as Backup solution for Bare Metal Kubernetes 
Description: A guide for configuring Velero using AWS S3 as storage provider 
Summary: A guide for configuring Velero using AWS S3 as storage provider
Date: 2025-08-30 16:00
Author: Max Pfeiffer
Lang: en
Keywords: Velero, Kubernetes, Backup, Restore, AWS  
Image: https://max-pfeiffer.github.io/images/2025_08_11_harbor_single_node_kubernetes_cluster.png

I put together that [Harbor turnkey project](https://github.com/max-pfeiffer/harbor-turnkey) recently and are
running two Kubernetes clusters on my own hardware now. Murphy's Law: at some point I did not pay attention to the
Kubernetes context I was working on, and I screwed up some PersistentVolumes in one of my clusters. Silly thing.
I could live with the loss of that data. But the incident made me want to work on a backup solution for my Kubernetes
clusters which I did not prioritize on until now. Yeah, something bad needs to happen first. 😀

So what backup tool am I going to use? I was looking at [Veeam Kasten](https://www.veeam.com/products/cloud/kubernetes-data-protection.html),
[Velero](https://velero.io/) and [k8up](https://k8up.io/). I ditched [Veeam Kasten](https://www.veeam.com/products/cloud/kubernetes-data-protection.html)
as this is some commercial product, and it has some subscription-based licensing model. Spending money on that is not
an option for my home lab environment. Plus, I prefer OpenSource software in general.

[k8up](https://k8up.io/) just backups PersistentVolumes and not Kubernetes resources of a namespace or a whole cluster.
That would be ok for me as I have everything defined with infrastructure-as-code, so I could restore Kubernetes
resources that way. But as I experienced, it's a nice option to have everything restored in one go. [k8up](https://k8up.io/)
only offers the option to do a file-system-based backup using [Restic](https://restic.net/). It also has a rather small
community and just [800 stars on GitHub](https://github.com/k8up-io/k8up).

[Velero](https://velero.io/) offers to back up Kubernetes namespaces or whole Kubernetes clusters. So if disaster
strikes I like to have that option. Plus it offers multiple ways to backup PersistentVolumes:

1. [file-system-based backup](https://velero.io/docs/v1.17/file-system-backup/) with [Kopia](https://kopia.io/) (Restic is phased out)
2. [VolumeSnapshot](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)s or [VolumeGroupSnapshot](https://velero.io/docs/v1.17/volume-group-snapshots/)s

The snapshot option is particularly interesting to me because I run my own
[Ceph cluster for Kubernetes storage]({filename}/2024-12-26_ceph_cluster_with_raspberry_pi_5.md).
And the [Ceph CSI driver supports VolumeSnapshot and VolumeGroupSnapshot](https://github.com/ceph/ceph-csi?tab=readme-ov-file#support-matrix).
[Velero](https://velero.io/) is also widely used and has a much larger community than [k8up](https://k8up.io/). On
[GitHub it has 9.4k stars](https://github.com/vmware-tanzu/velero).

So I choose to use [Velero](https://velero.io/) eventually. In the first place I decided to go for the file-system-based
backup with Velero because doing snapshots with Ceph on my own infrastructure have one disadvantage: if my Ceph cluster
breaks down completely, data of the snapshots is also lost. This is very unlikely to happen but there is Murphy's Law. 😀
I will start playing a bit later with the snapshots after I secured my data.
