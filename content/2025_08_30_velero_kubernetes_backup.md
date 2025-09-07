Title: Velero as Backup solution for Bare Metal Kubernetes 
Description: A guide for configuring Velero using AWS S3 as storage provider 
Summary: A guide for configuring Velero using AWS S3 as storage provider
Date: 2025-08-30 16:00
Author: Max Pfeiffer
Lang: en
Keywords: Velero, Kubernetes, Backup, Restore, AWS  
Image: https://max-pfeiffer.github.io/images/2025_08_11_harbor_single_node_kubernetes_cluster.png

As I am running more and more stateful applications on my Kubernetes clusters, I saw the need to prioritize securing
their data. I am not concerned about the Kubernetes objects as I have defined everything with infrastructure-as-code
and can sync/restore everything almost effortlessly if something happens. My main concern is the data stored on
PersistentVolumes.

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
[Velero supports the main cloud providers out of the box and also has some community providers.](https://velero.io/docs/v1.17/supported-providers/)

So I choose to use [Velero](https://velero.io/) eventually. In the first place, I decided to go for the file-system-based
backup with Velero because doing snapshots with Ceph on my own infrastructure have one disadvantage: if my Ceph cluster
breaks down completely, data of the snapshots is also lost. This is very unlikely to happen but there is Murphy's Law. 😀
I will start playing a bit later with the snapshots after I secured my data.

## AWS Resources
As we want to use AWS S3 as storage provider, we need to create:

* S3 storage bucket
* IAM user credentials (access key ID and access key secret)

Creating an S3 storage bucket and user credentials rather straight forward: you can do that using the AWS web UI,
the AWS client or via OpenTofu (infrastructure-as-code) which I prefer. The process is also very well documented in
[the GitHub repo of the AWS plugin for Velero](https://github.com/vmware-tanzu/velero-plugin-for-aws#setup). So I will
not go into this further.

## Velero Installation and Configuration via CLI
Please be aware that Velero CLI tool expects Velero to be installed in `velero` namespace. You can use other namespaces, 
but then you need to use `--namespace` option for every CLI command or set the `VELERO_NAMESPACE` environment variable
to persist this setting. So for the sake of convenience we just create that `velero` namespace with
`pod-security.kubernetes.io/enforce` set to `priviledged`:
```shell
$ kubectl create namespace velero
$ kubectl label namespace velero pod-security.kubernetes.io/enforce=priviledged
```
The next step is to create the Secret containing the credentials for the AWS S3 storage bucket. Prepare a file
`aws-cred` containing your credentials in that format:
```shell
[default]
aws_access_key_id=<YOUR_ACCESS_KEY_ID>
aws_secret_access_key=<YOUR_ACCESS_KEY>
```
Then create a secret from that file:
```shell
$ kubectl -n velero create secret generic aws-s3 --from-file=cloud=./aws-cred
```
Prepare the `values.yaml` file for the installation with Helm:
```yaml
configuration:
  backupStorageLocation:
  - name: "aws-s3"
    provider: "aws"
    bucket: "your-storage-bucket-name"
    default: true
    accessMode: ReadWrite
    config:
      region: "your-aws-region"
  defaultVolumesToFsBackup: true
credentials:
  useSecret: true
  existingSecret: aws-s3
initContainers:
- name: velero-plugin-for-aws
  image: velero/velero-plugin-for-aws:v1.12.2
  imagePullPolicy: IfNotPresent
  volumeMounts:
  - mountPath: /target
    name: plugins
snapshotsEnabled: false
deployNodeAgent: true
```
You will need to adjust the yaml file to your personal needs:

* backupStorageLocation: add your storage bucket name and AWS region, please also note that this is set to be the default location
* defaultVolumesToFsBackup: this set the file system backup as default, [you need to add annotation to opt-out](https://velero.io/docs/v1.17/file-system-backup/#using-the-opt-out-approach)

We need to deploy the Velero node agent when we want to use the [file system backup](https://velero.io/docs/v1.17/file-system-backup/)
with `deployNodeAgent: true`. Also I disabled file system snapshots with `snapshotsEnabled: false` for now as this is
not the current focus.

We use Helm to install the application:
```shell
$ helm repo add
$ helm install velero --namespace velero --values values.yaml
```

## Velero installation with ArgoCD (GitOps)
For pursuing the GipOps approach with ArgoCD I am including also the manifest files. Using these would then be a
copy and paste job for your git repository. I am leaving open here how you are going to create the secret for the
AWS S3 storage bucket as there are a lot of options for GitOps secret handling.

### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: velero
  labels:
    pod-security.kubernetes.io/enforce: privileged
spec: {}
```

### Velero Application