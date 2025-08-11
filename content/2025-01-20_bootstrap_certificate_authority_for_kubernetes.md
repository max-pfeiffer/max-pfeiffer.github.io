Title: How to Bootstrap a Certificate Authority in your Kubernetes Cluster 
Description: A guide for bootstrapping a certificate authority for issuing TLS certificates in a Kubernetes cluster   
Summary: A guide for bootstrapping a certificate authority for issuing TLS certificates in a Kubernetes cluster
Date: 2025-01-20 21:00
Author: Max Pfeiffer
Lang: en
Keywords: CA, certificate authority, Step CA, Step Issuer, cert-manager, bootstrap, Kubernetes, TLS
Image: https://max-pfeiffer.github.io/images/2025-01-20_bootstrap_certificate_authority.jpeg
original_url: blog/how-to-bootstrap-a-certificate-authority-in-your-kubernetes-cluster.html

In overall, I was a bit unhappy using self-signed TLS certificates in my home lab Kubernetes cluster. I found it
annoying to click away these warnings in my browser. Also, I ran into a couple of problems using self-signed
certificates for my [Keycloak](https://www.keycloak.org/) installation. When configuring SSO for
[ArgoCD](https://argoproj.github.io/cd/) and [Grafana](https://grafana.com/) I had to configure security overrides when
calling Keycloak OIDC endpoints for the authentication process. So I decided to create my owm certificate authority
eventually.

A friend recommended the solution from [Smallstep](https://smallstep.com/) to me. These guys provide
[Step CA](https://github.com/smallstep/certificates) which is a piece of software which issues TLS certificates
based on your own root certificate authority (CA). They also provide
[Step Issuer](https://github.com/smallstep/step-issuer) which is a Kubernetes [cert-manager](https://cert-manager.io)
[CertificateRequest](https://cert-manager.io/docs/usage/certificaterequest) controller that uses
[Step CA](https://github.com/smallstep/certificates).

![Smallstep GitHub Organisation]({static}/images/2025-01-20_bootstrap_certificate_authority.jpeg)

Installing [Step CA](https://github.com/smallstep/certificates) and [Step Issuer](https://github.com/smallstep/step-issuer)
und configuring Ingresses with it, I fell into a couple of traps. So that process was not as straight forward as I
 thought, and I spent a while on a working solution. So I guess it's worth sharing my experience with the public.

## Step CA
I was using the [Helm chart to install Step CA](https://artifacthub.io/packages/helm/smallstep/step-certificates).
As a first step you want to create your `values.yaml` file.
[Smallstep offers a CLI tool](https://github.com/smallstep/cli) which comes in handy here. It's quickly
[installed](https://smallstep.com/docs/step-cli/installation/) on your machine. You can generate your `values.yaml`
like so:
```shell
step ca init --helm > values.yaml
```
This will result in some interactive process where you need to enter the following configuration options:

1. Deployment Type: you want to select `Standalone` here
2. Name of the PKI: pick something that suits you
3. DNS names: here you need to have a FQDN for:
      1. cert-manager (mandatory): this needs to be some FQDN that your
         [internal Kubernetes DNS can resolve](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/),
         i.e. `step-certificates.security.svc.cluster.local` or `step-certificates.cert` **depending on the namespace you
         will install it into**
      2. the outside world: if you choose to offer that service on some public domain i.e. `ca.yourdomain.com`
4. IP and port: go with the default `:9000` or pick whatever matches your use case
5. First provisioner name: as we are aiming for cert-manager using it, `cert-manager` is probably a good choice
6. Password: when you generate one, it ends up base64encoded in that `values.yaml` file

Depending on how you conduct the installation process with Helm, you might want to remove the password and
certificates, keep it in your credential store and inject it later with your provisioning tool. I use
[OpenTofu](https://opentofu.org/) for this. A simple install using Helm CLI can be done like this:
```shell
helm repo add smallstep https://smallstep.github.io/helm-charts/
helm install step-certificates smallstep/certificates -f values.yaml --namespace security
```
Please be aware of the `security` namespace. This will result in Step Certificates being available under the FQDN
`step-certificates.security.svc.cluster.local` in your Kubernetes cluster. As you probably don't want to install and
run it in your default namespace, this is this first trap you can fall into.

### Results
Now check for ConfigMaps created by that Helm chart:
```shell
$ kubectl -n security get configmap
NAME                       DATA   AGE
kube-root-ca.crt           1      42h
step-certificates-certs    2      42h
step-certificates-config   4      42h
```
And have a closer look at that `step-certificates-certs` ConfigMap:
```shell
kubectl -n security get configmap step-certificates-certs -o yaml
```
Take note that includes the root_ca certificate. This will come in handy later.

Also check on the `step-certificates-config` ConfigMap:
```shell
kubectl -n security get configmap step-certificates-config -o yaml
```
Take note that it includes the configuration for the provisioner that we generated with the
[Step CLI tool]((https://github.com/smallstep/cli)) earlier. We will need that later to configure the
[Step Issuer](https://github.com/smallstep/step-issuer).

Check on the Secrets which were created by the Helm chart:
```shell
$ kubectl -n security get secret                                   
NAME                                      TYPE                                 DATA   AGE
sh.helm.release.v1.step-certificates.v1   helm.sh/release.v1                   1      42h
step-certificates-ca-password             smallstep.com/ca-password            1      42h
step-certificates-provisioner-password    smallstep.com/provisioner-password   1      42h
step-certificates-secrets                 smallstep.com/private-keys           2      42h
```
Take not that there is a secret containing the provisioner password `step-certificates-provisioner-password`. This
we also need to configure the [Step Issuer](https://github.com/smallstep/step-issuer).

## Step Issuer
Smallstep provides another [Helm chart to install Step Issuer](https://artifacthub.io/packages/helm/smallstep/step-issuer).
I wanted to have a ClusterIssuer for my Kubernetes Cluster. Fortunately, that Helm chart comes with a template to
create it. But for configuring it, we need the following seven values:

1. CA URL
2. CA Root certificate (base64 encoded)
3. Provisioner name
4. Provisioner Key ID (KID)
5. From the provisioner Secret (see above `step-certificates-provisioner-password`)
   1. Name of the Secret
   2. Key of the password in that Secret
   3. Namespace where that Secret lives

For extracting the necessary values, you need to have [jq](https://jqlang.github.io/jq/) installed. 

CA URL can be extracted from `step-certificates-config` ConfigMap (see above):
```shell
kubectl -n security get configmap step-certificates-config -o jsonpath="{.data['defaults\.json']}"  | jq -r '."ca-url"'
```

CA root certificate can be extracted from `step-certificates-certs` ConfigMap (see above) and encode it with base64:
```shell
kubectl -n security get configmap step-certificates-certs -o jsonpath="{.data['root_ca\.crt']}"  | base64
```

Extract provisioner name from `step-certificates-config` ConfigMap (see above) like so:
```shell
kubectl -n security get configmap step-certificates-config -o jsonpath="{.data['ca\.json']}"  | jq -r '.authority.provisioners[0].name'
```

Extract provisioner KID from `step-certificates-config` ConfigMap (see above) like so:
```shell
kubectl -n security get configmap step-certificates-config -o jsonpath="{.data['ca\.json']}"  | jq -r '.authority.provisioners[0].key.kid'
```

With the values you acquired, you can put together your `values.yaml` file for
[Step Issuer Helm chart](https://artifacthub.io/packages/helm/smallstep/step-issuer):
```yaml
stepClusterIssuer:
  create: true
  caUrl: "https://step-certificates.security.svc.cluster.local"
  caBundle: "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJvekNDQVVxZ0F3SUJBZ0lSQU5zTnFuNGNLb0JYN3RLMDFPU"
  provisioner:
    name: "cert-manager"
    kid: "KCE2Wd2sJB-3adZZpPueITNIe8KyXw0Om17-kDzZ_fQ"
    passwordRef:
      name: "step-certificates-provisioner-password"
      key: "password"
      namespace: "security"
```

Then use that `values.yaml` file to install Step Issuer in your Kubernetes cluster:
```shell
helm install step-issuer smallstep/step-issuer -f values.yaml --namespace security
```

### Results
Check the results after installation:
```shell
$kubectl get stepclusterissuer        
NAME          AGE
step-issuer   3d3h
```
So you should now have a StepClusterIssuer up and running. Please note that its name is **step-issuer** and not
**step-cluster-issuer**. You need that name to reference it later in the Ingress annotations. For some reason, I don't
understand the Helm chart does not provide any way to change that. Also check its status:
```shell
kubectl get stepclusterissuer step-issuer -o yaml
```
If there is any problem with it, you would see it in the output.

## cert-manager
You have your StepClusterIssuer up and running now. So cert-manger can use it for issuing TLS certificates. Dealing
with cert-manager Ingress annotations for external issuers is a bit tricky though. Please take note of [all the
warnings in official cert-manager documentation](https://cert-manager.io/docs/usage/ingress/#supported-annotations).
So you want to have the annotations part for an Ingress look like this:
```shell
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/issuer: step-issuer
    cert-manager.io/issuer-group: certmanager.step.sm
    cert-manager.io/issuer-kind: StepClusterIssuer
```
Please note that `cert-manager.io/issuer` refers to the name of the StepClusterIssuer `step-issuer` (see above).

## Import Root CA
You want to install your new root certificate in your systems trust store eventually. So browsers and other
applications can deal with TLS certificates issued based on that root certificate appropriately. So it makes sense to
put your new root certificate into a file i.e. `root-ca.pem` that you can use and share.

### Local Machines
[Step CLI tool](https://github.com/smallstep/cli) offers a [very convenient way to install the root certificate into
your local default trust store](https://smallstep.com/docs/step-cli/reference/certificate/install/index.html):
```shell
step certificate install root-ca.pem
```

### SSO with Keycloak for ArgoCD
ArgoCD offers [a nice configuration option for using custom root certificates](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/#configuring-a-custom-root-ca-certificate-for-communicating-with-the-oidc-provider):
```yaml
  oidc.config: |
    ...
    rootCA: |
      -----BEGIN CERTIFICATE-----
      ... encoded certificate data here ...
      -----END CERTIFICATE-----
```

### SSO with Keycloak and Grafana
Grafana is also offering [a configuration option for custom root certificates](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth/#configuration-options).
Please see `tls_client_ca` in that section.

## Related Articles

* [Single Sign On (SSO) with Grafana and Keycloak]({filename}/2025-02-07_sso_for_grafana_with_keycloak.md)
* [Securing Prometheus and Alertmanager web UI with oauth2-proxy and Keycloak]({filename}/2025-02-28_securing_prometheus_and_alertmanager_with_oauth2-proxy.md)