Title: Securing Prometheus and Alertmanager web UI with oauth2-proxy and Keycloak
Description: How to configure a secure login for your Prometheus and Alertmanger web UI with oauth2-proxy and Keycloak, contains configuration examples
Summary: How to configure a secure login for your Prometheus and Alertmanger web UI with oauth2-proxy and Keycloak, contains configuration examples
Date: 2025-02-28 12:00
Author: Max Pfeiffer
Lang: en
Keywords: Prometheus, Alertmanager, oauth2-proxy, Keycloak, SSO, Single Sign On, Kubernetes
Image: https://max-pfeiffer.github.io/images/2025-02-28_oauth2_proxy_simplified-architecture.svg
original_url: blog/securing-prometheus-and-alertmanager-web-ui-with-oauth2-proxy-and-keycloak.html

[Prometheus](https://prometheus.io/) and [Alertmanager](https://github.com/prometheus/alertmanager) come with a quite
useful web user interface. But other than [Grafana](https://grafana.com/) there is no build in mechanism for user
authentication or authorization. In an [earlier article]({filename}/2025-02-07_sso_for_grafana_with_keycloak.md) I was
covering that single sign on (SSO) configuration for [Grafana](https://grafana.com/) with [Keycloak](https://www.keycloak.org/).
A nice option to configure SSO for [Prometheus](https://prometheus.io/) and [Alertmanager](https://github.com/prometheus/alertmanager)
is to use the [oauth2-proxy project](https://github.com/oauth2-proxy/oauth2-proxy).

![2025-02-28_oauth2_proxy_simplified-architecture.svg]({static}/images/2025-02-28_oauth2_proxy_simplified-architecture.svg)
_Image source: [https://github.com/oauth2-proxy/oauth2-proxy/blob/master/docs/static/img/simplified-architecture.svg](https://github.com/oauth2-proxy/oauth2-proxy/blob/master/docs/static/img/simplified-architecture.svg)_

[oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy) offers two integration options: running it as reverse
proxy or as middleware. In a Kubernetes environment with an ingress controller, it makes much more sense to run it as
middleware and let it just handle the authentication challenges. How that works is well described in
[its official documentation](https://oauth2-proxy.github.io/oauth2-proxy/behaviour).

## Preliminary rulings
For doing the configuration, we need to do some decisions first:

1. ingress configuration for Prometheus and Altermanager: on what domains or URL paths would we like to run these applications
2. [oauth2-proxy integration](https://oauth2-proxy.github.io/oauth2-proxy/#architecture): reverse proxy or middleware (see above)
3. [oauth2-proxy session storage](https://oauth2-proxy.github.io/oauth2-proxy/configuration/session_storage): cookie or Redis

### Ingress configuration decision
It's quite common to run Prometheus and Alertmanager (and also Grafana) on a single monitoring domain with different
paths, i.e.:

* monitoring.yourcompany.com/prometheus
* monitoring.yourcompany.com/alertmanager
* monitoring.yourcompany.com/grafana

This is done for good reasons:

* you just need to have one domain for your cluster's monitoring
* that way you just need to configure and run a single instance of oauth2-proxy, oauth2-proxy is just not made for
  covering multiple domains with a single installation.
* permission configuration: permission concept for users is usually bound equally to the Kube-Prometheus stack applications
* it's convenient for users to access the different applications in this manner

So we will follow that common approach and use one domain and different URL paths for the applications.
We will set it up like this:

* monitoring.lan/prometheus
* monitoring.lan/alertmanager

### oauth2-proxy integration decision
In a Kubernetes environment you usually run an ingress controller handling the incoming network traffic. In my case,
I use the [ingress-nginx](https://github.com/kubernetes/ingress-nginx). There you have
[good options to forward authentication requests to oauth2-proxy using the `auth_request` directive](https://oauth2-proxy.github.io/oauth2-proxy/configuration/integration#configuring-for-use-with-the-nginx-auth_request-directive)
and use it as middleware. So we go for this option as it is very flexible and easy to configure with ingress
annotations.

### oauth2-proxy session storage decision
oauth2-proxy has two options for storing the session information for authenticated users: in a cookie or in
[Redis database](https://redis.io/). Actually [ingress-nginx](https://github.com/kubernetes/ingress-nginx) has problems
looping through large cookies in headers and requires some sophisticated configuration to make that work.
Storing the session information in [Redis database](https://redis.io/) is in overall a more solid solution and avoids
additional network payload. But it uses additional Kubernetes computing resources and consumes storage (if persisted).
But the Redis variant is easy and convenient to configure using the 
[Helm chart for oauth2-proxy](https://github.com/oauth2-proxy/manifests). So I decided to go with this solution.

## Keycloak configuration
I assume that you have a running [Keycloak](https://www.keycloak.org/) installation in your Kubernetes cluster. In an
earlier article, I was covering the [automated provisioning of Keycloak with OpenTofu]({filename}/2025-01-10_how_to_configure_keycloak_terraform_provider.md).
That might be interesting if you still need to set that up.

In Keycloak we need to configure:

* a role for resource authorization, let's call it `monitoring`
* a confidential client for oauth2-proxy
* an OpenID audience protocol mapper for that oauth2-proxy client 

A complete configuration for [OpenTofu](https://opentofu.org/) will look like this:
```terraform
resource "keycloak_openid_client" "oauth2_proxy" {
  realm_id                     = keycloak_realm.homelab.id
  client_id                    = "oauth2-proxy"
  name                         = "Oauth2 Proxy Client"
  enabled                      = true
  access_type                  = "CONFIDENTIAL"
  client_secret                = "yoursecret"
  standard_flow_enabled        = true
  direct_access_grants_enabled = false

  valid_redirect_uris = [
    "https://monitoring.lan/oauth2/callback"
  ]
  valid_post_logout_redirect_uris = [
    "+"
  ]
}

resource "keycloak_openid_audience_protocol_mapper" "oauth2_proxy" {
  client_id       = keycloak_openid_client.oauth2_proxy.id
  realm_id        = keycloak_realm.homelab.id
  name            = "audience-mapper"
  included_client_audience = keycloak_openid_client.oauth2_proxy.client_id
  add_to_access_token = true
  add_to_id_token = true
}

resource "keycloak_role" "realm_homelab_client_oauth2_proxy_role_alertmanager" {
  realm_id    = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.oauth2_proxy.id
  name        = "monitoring"
  description = "Grants access to monitoring"
}
```
After this configuration is done you can create a user and assign that `monitoring` role to him.

## Ingress controller configuration
We need to configure two separate ingresses for Prometheus and Alermanager. I installed these two applications using
the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) Helm chart. You can configure the ingress for both applications in the Helm chart
via the `values.yaml` file:
```yaml
alertmanager:
  alertmanagerSpec:
    externalUrl: "https://monitoring.lan/alertmanager"
  ingress:
    enabled: true
    ingressClassName: "nginx"
    annotations:
      cert-manager.io/issuer: step-issuer
      cert-manager.io/issuer-kind: StepClusterIssuer
      cert-manager.io/issuer-group: certmanager.step.sm
      nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
      nginx.ingress.kubernetes.io/auth-response-headers: Authorization
      nginx.ingress.kubernetes.io/auth-signin: https://$host/oauth2/start?rd=$escaped_request_uri
      nginx.ingress.kubernetes.io/auth-url: https://$host/oauth2/auth
      nginx.ingress.kubernetes.io/rewrite-target: /$2
    paths:
      - "/alertmanager(/|$)(.*)"
    pathType: Prefix
    hosts:
      - "monitoring.lan"
    tls:
      - secretName: "alertmanager-lan-tls"
        hosts:
          - "monitoring.lan"

prometheus:
  prometheusSpec:
    externalUrl: "https://monitoring.lan/prometheus"
  ingress:
    enabled: true
    ingressClassName: "nginx"
    annotations:
      cert-manager.io/issuer: step-issuer
      cert-manager.io/issuer-kind: StepClusterIssuer
      cert-manager.io/issuer-group: certmanager.step.sm
      nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
      nginx.ingress.kubernetes.io/auth-response-headers: Authorization
      nginx.ingress.kubernetes.io/auth-signin: https://$host/oauth2/start?rd=$escaped_request_uri
      nginx.ingress.kubernetes.io/auth-url: https://$host/oauth2/auth
      nginx.ingress.kubernetes.io/rewrite-target: /$2
    hosts:
      - "monitoring.lan"
    paths:
      - "/prometheus(/|$)(.*)"
    pathType: Prefix
    tls:
      - secretName: "prometheus-lan-tls"
        hosts:
          - "monitoring.lan"
```
There you see the ingress annotations for oauth2-proxy. Also, you get an idea how to use the
`nginx.ingress.kubernetes.io/rewrite-target` annotation to make that URL path configuration for both applications work.
Please note that `externalUrl` is an application-specific setting and specifies the path for the applications to run on.

## oauth2-proxy installation and configuration
There is a [Helm chart for oauth2-proxy](https://github.com/oauth2-proxy/manifests) which is well maintained by the
community. I used without any issues to install [oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy) in my
Kubernetes cluster.

The [Keycloak integration is well documented](https://oauth2-proxy.github.io/oauth2-proxy/configuration/providers/keycloak_oidc)
and straight forward. As you are actually doing the configuration in the `values.yaml` file for
[oauth2-proxy Helm chart](https://github.com/oauth2-proxy/manifests) you need to 'translate" `-` into `_` for the
configuration option keys [as also described in the docs](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview).

I ended up with this `values.yaml`:
```yaml
config:
  clientID: "oauth2_proxy_client_id"
  clientSecret: "oauth2_proxy_client_secret"
  configFile: |
    # Provider Config
    provider = "keycloak-oidc"
    provider_display_name = "Keycloak"
    redirect_url = "https://monitoring.lan/oauth2/callback"
    oidc_issuer_url = "https://keycloak.lan/realms/homelab"
    code_challenge_method = "S256"

    # Server Config
    reverse_proxy = true
    cookie_secure = true
    email_domains = [ "*" ]
    allowed_roles = [ "oauth2-proxy:monitoring" ]
    
    # Add root CA certificate
    provider_ca_files = [ "/etc/ssl/certs/root_ca_certificate" ]

extraVolumes:
  - name: root-ca
    secret:
      secretName: oauth-proxy-ca

extraVolumeMounts:
  - name: root-ca
    mountPath: "/etc/ssl/certs"
    defaultMode: 0440
    readOnly: true

redis:
  enabled: true
  global:
    redis:
      password: "oauth2_proxy_redis_password"
sessionStorage:
  type: redis
  redis:
    password: "oauth2_proxy_redis_password"

ingress:
  enabled: true
  className: "nginx"
  path: "/oauth2"
  pathType: Prefix
  hosts:
    - "monitoring.lan"
  annotations:
      cert-manager.io/issuer: step-issuer
      cert-manager.io/issuer-kind: StepClusterIssuer
      cert-manager.io/issuer-group: certmanager.step.sm
      nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
  tls:
   - secretName: oauth2-proxy-tls
     hosts:
       - "monitoring.lan"
```
Please note that I use [a custom certificate authority (CA)]({filename}/2025-01-20_bootstrap_certificate_authority_for_kubernetes.md)
here (`provider_ca_files`). For ingesting the root certificate I also added `extraVolumes` and `extraVolumeMounts`.
You will not need that unless you also use a custom CA for your Kubernetes cluster.

With this last step you should have a working oauth2-proxy installation and should be able to sign in with a user you
have configured in Keycloak. Don't forget to assign the `monitoring` role to that user. 