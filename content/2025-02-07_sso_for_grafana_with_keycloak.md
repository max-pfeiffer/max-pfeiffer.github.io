Title: Single Sign On (SSO) with Grafana and Keycloak 
Description: A guide for configuring Single Sign On (SSO) for Grafana with Keycloak, contains also examples for OpenTofu    
Summary: A guide for configuring Single Sign On (SSO) for Grafana with Keycloak, contains also examples for OpenTofu
Date: 2025-02-07 16:00
Author: Max Pfeiffer
Lang: en
Keywords: Grafana, Keycloak, SSO, Single Sign On, Kubernetes
Image: https://max-pfeiffer.github.io/images/2025-02-07_keycloak_client_scopes_evaluate.png
original_url: blog/single-sign-on-sso-with-grafana-and-keycloak.html

I am running [Keycloak](https://www.keycloak.org/) as identity provider in my Kubernetes cluster because I want to have
Single Sign On (SSO) for all my applications I run there. In the last years the [Keycloak](https://www.keycloak.org/)
project matured quite a bit and became a capable and convenient solution. I am doing infrastructure as code
and installed it using [OpenTofu](https://opentofu.org/) and [my own Helm chart](https://github.com/max-pfeiffer/keycloak-postgresql-docker-helm)
into my Kubernetes cluster. Since version v26.0.0 [Keycloak](https://www.keycloak.org/) provides
[a nice option for automated provisioning by bootstrapping a confidential client]({filename}/2025-01-10_how_to_configure_keycloak_terraform_provider.md).

When I started to configure the SSO integration for Grafana, I noticed that the
[official Grafana documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/keycloak/)
is outdated. Both for the latest Grafana version and the latest Keycloak version. Following the instructions there
does not result in a working SSO configuration. So I decided to write that article as it might provide some value to
other persons starting the same endeavor. Here I focus on parts of the configuration which were outdated in the
[official Grafana documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/keycloak/)
or are complex and challenging.

## Mapping Keycloak users and roles to Grafana
For SSO you want to configure roles in Keycloak which are then mapped to the roles in Grafana accordingly.
[Grafana knows about these roles which result in different permissions](https://grafana.com/docs/grafana/latest/administration/roles-and-permissions/):

* GrafanaAdmin
* Admin
* Editor
* Viewer

You can assign these roles in Keycloak to users. And when the user signs in with SSO into Grafana, he then becomes
assigned the matching Grafana role and has the permissions which are configured in Grafana for this role.

### Roles in Keycloak
You need to be aware that there are two types of roles you can use in Keycloak:

* Realm roles
* Client roles

As the name already tells you, you can configure these roles either for realms or clients in their respective user
interface sections.

Following the above-mentioned naming convention, you can configure roles with these names in Keycloak:

* grafanaadmin
* admin
* editor
* viewer

Both types of roles will work. But you need to make sure that you have configured the mapper for each role type, so 
the roles are included in the JWT.

In recent versions of Keycloak, the standard way how Keycloak maps roles to JSON Web Tokens (JWT) did change. By default,
Keycloak does not map realm roles to the `roles` attribute anymore. They are mapped to `resource_access` and are nested
nowadays:
```json
{
  "resource_access": {
    "grafana": {
      "roles": [
        "grafanaadmin"
      ]
    }
  }
}
```
So you either want to change the way Keycloak maps the roles to the JWT or change the way Grafana parses the JWT claims.
Both is a bit tricky to do. 

### Grafana role mapping
The relevant [configuration option](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth/#configuration-options)
in Grafana is `role_attribute_path`. Grafana is using [JMESPath](https://jmespath.org/) expressions to extract the
roles from the string you specify in `role_attribute_path`. To match the new Keycloak default (see above) you want to
configure it like this:
```yaml
role_attribute_path: "contains(resource_access.grafana.roles[*], 'grafanaadmin') && 'GrafanaAdmin' || contains(resource_access.grafana.roles[*], 'admin') && 'Admin' || contains(resource_access.grafana.roles[*], 'editor') && 'Editor' || 'Viewer'"
```
For working out this or another custom solution I found the [JMESPath playground](https://play.jmespath.org/)
invaluable. There you can throw in your JSON claims from JWT and put together your own JMESPath expression. You get
direct feedback for the result right away.

### Keycloak JWT debugging
Keycloak provides nowadays an option to check on mappers and JWTs for a certain user in its own user interface.
This option is well hidden in the client configuration section: there you need to click the "Client scopes" tab. Then
select the "Evaluate" tab.

![2025-02-07_keycloak_client_scopes_evaluate.jpg]({static}/images/2025-02-07_keycloak_client_scopes_evaluate.png)

I personally found this a bit cumbersome to use and wanted to have something without UI which I can include in an
automated test flow. So I quickly wrote a [CLI tool to check on JWT claims](https://github.com/max-pfeiffer/keycloak-jwt-checker)
myself. Give it a try if you are sick of using the Keycloak UI. 😀

### ID Token claims
When creating a new client within Keycloak, per default the role claims are not added to the ID token. This is causing
Grafana role mapping to fail. So you need to make sure that your role mapper includes the roles in the ID token.
Otherwise, the login works, but your user's role always falls back to `Viewer`. The following screenshot shows a
**client** role mapper. Please note that the switch "Add to ID token" is active.

![2025-02-07_keycloak_client_scope_mapper.png]({static}/images/2025-02-07_keycloak_client_scope_mapper.png)

## Refresh token
When creating a new client within Keycloak, per default issuing a refresh token is configured. This is causing problems
if not configured correctly. First make sure that the Keycloak user that you want to sign in with has the
role `offline_access` so Keycloak actually issues a refresh token for this user. Otherwise, the login will
**fail completely**. In Grafana config you want to set `use_refresh_token = true`. That should do the trick.

## Single Logout
The [Grafana documentation for Single Logout](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/keycloak/#enable-single-logout)
does contain an outdated Keycloak URL. You want to use
`https://<PROVIDER_DOMAIN>/realms/<REALM_NAME>/protocol/openid-connect/logout?post_logout_redirect_uri=https%3A%2F%2F<GRAFANA_DOMAIN>%2Flogin`
for `signout_redirect_url`.

## Result
I installed Grafana with the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
Helm chart in my Kubernetes Cluster. So my values.yaml looks like this eventually (for the Grafana part):
```yaml
grafana:
  grafana.ini:
    server:
      domain: "grafana.lan"
      root_url: "https://grafana.lan"
    auth.generic_oauth:
      enabled: true
      name: Keycloak
      allow_sign_up: true
      client_id: <YOUR CLIENT ID>
      client_secret: <YOUR CLIENT SECRET>
      scopes: "openid email profile offline_access roles"
      auth_url: "https://keycloak.lan/realms/homelab/protocol/openid-connect/auth"
      token_url: "https://keycloak.lan/realms/homelab/protocol/openid-connect/token"
      api_url: "https://keycloak.lan/realms/homelab/protocol/openid-connect/userinfo"
      signout_redirect_url: "https://keycloak.lan/realms/homelab/protocol/openid-connect/logout?post_logout_redirect_uri=https%3A%2F%2Fgrafana.lan%2Flogin"
      email_attribute_path: email
      login_attribute_path: username
      name_attribute_path: full_name
      groups_attribute_path: groups
      role_attribute_path: "contains(roles[*], 'grafanaadmin') && 'GrafanaAdmin' || contains(roles[*], 'admin') && 'Admin' || contains(roles[*], 'editor') && 'Editor' || 'Viewer'"
      allow_assign_grafana_admin: true
      role_attribute_strict: true
      use_refresh_token: true
```
Currently, I am running Grafana on `grafana.lan` domain. Please note that I use a client role mapper which maps
directly to `roles` instead of `resource_access`.

## Automated Keycloak provisioning with OpenTofu
I configured Keycloak with [OpenTofu](https://opentofu.org/) using the [terraform-provider-keycloak](https://github.com/keycloak/terraform-provider-keycloak).
These are the resources I had to configure:
```terraform
resource "keycloak_openid_client" "grafana" {
  realm_id                     = keycloak_realm.homelab.id
  client_id                    = "grafana"
  name                         = "Grafana Client"
  enabled                      = true
  access_type                  = "CONFIDENTIAL"
  client_secret                = "yourclientsecret"
  standard_flow_enabled        = true
  implicit_flow_enabled        = false
  direct_access_grants_enabled = true
  use_refresh_tokens = true

  root_url  = "https://grafana.lan"
  admin_url = "https://grafana.lan"
  base_url  = "/applications"
  valid_redirect_uris = [
    "https://grafana.lan/login/generic_oauth"
  ]
  web_origins = [
    "https://grafana.lan"
  ]
  valid_post_logout_redirect_uris = [
    "https://grafana.lan/login"
  ]
}

resource "keycloak_openid_client_optional_scopes" "grafana_client_optional_scopes" {
  realm_id  = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id

  optional_scopes = []
}

resource "keycloak_openid_client_default_scopes" "grafana_client_default_scopes" {
  depends_on = [keycloak_openid_client_optional_scopes.grafana_client_optional_scopes]
  realm_id  = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id

  default_scopes = [
    "email",
    "offline_access",
    "profile",
    "roles",
  ]
}

resource "keycloak_role" "realm_homelab_role_grafanaadmin" {
  realm_id    = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id
  name        = "grafanaadmin"
  description = "Grafana Super Admin Role"
}

resource "keycloak_role" "realm_homelab_role_admin" {
  realm_id    = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id
  name        = "admin"
  description = "Grafana Admin Role"
}

resource "keycloak_role" "realm_homelab_role_editor" {
  realm_id    = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id
  name        = "editor"
  description = "Grafana Editor Role"
}

resource "keycloak_role" "realm_homelab_role_viewer" {
  realm_id    = keycloak_realm.homelab.id
  client_id = keycloak_openid_client.grafana.id
  name        = "viewer"
  description = "Grafana Viewer Role"
}

resource "keycloak_generic_protocol_mapper" "grafana_roles" {
  client_id       = keycloak_openid_client.grafana.id
  realm_id        = keycloak_realm.homelab.id
  name            = "roles"
  protocol        = "openid-connect"
  protocol_mapper = "oidc-usermodel-client-role-mapper"
  config = {
    "id.token.claim"                       = "true"
    "access.token.claim"                   = "true"
    "userinfo.token.claim"                 = "true"
    "claim.name"                           = "roles"
    "jsonType.label"                       = "String"
    "multivalued"                          = "true"
    "introspection.token.claim"            = "true"
    "usermodel.clientRoleMapping.clientId" = keycloak_openid_client.grafana.client_id
  }
}
```
