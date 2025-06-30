Title: Cost efficient dynamic DNS solution with AWS resources
Description: I build my own dynamic DNS solution using AWS resources and a my own dynamic-dns-update-client
Summary: I build my own dynamic DNS solution using AWS resources and a my own dynamic-dns-update-client
Date: 2025-06-27 20:00
Author: Max Pfeiffer
Lang: en
Keywords: Dynamic DNS, DNS, OpenWRT, Dynamic DNS Update Client, OpenTofu
Image: https://max-pfeiffer.github.io/blog/images/2025-06-27_simple_dynamic_dns_aws.png

For my home lab, I have the need to expose some services on the public internet. My current ISP does not offer
fixed IP addresses. So I was looking at some of the dynamic DNS providers out there. I did not feel like spending money
on it, and the free offerings look a bit shady. I happen to already have an AWS account for running
some workloads. So I was exploring the [Route 53](https://aws.amazon.com/de/route53/) and [Lambda](https://aws.amazon.com/lambda/)
offerings a bit and saw that I can build a dynamic DNS easily with low effort myself. And I like building stuff. 😀

## Dynamic DNS server
So the decision was made to build my own.
I jumped into it and created a new project on GitHub: [Simple Dynamic DNS with AWS](https://github.com/max-pfeiffer/simple-dynamic-dns-aws)

![2025-06-27_simple_dynamic_dns_aws.png]({static}/images/2025-06-27_simple_dynamic_dns_aws.png)

I created a little application which eats an HTTP requests with parameters containing dynamic DNS update
data. It then configures a domain you own on AWS with [Route 53 DNS service](https://aws.amazon.com/de/route53/).
This application is put in a Docker container which is then run via an [AWS Lambda](https://aws.amazon.com/lambda/)
function. That's basically it. I want my infrastructure to be fully declarative, so I choose to provision the AWS
resources with [OpenTofu](https://opentofu.org/). This makes it also very easy to install by anyone else as you just need to pull the
repo and create your own configuration: 
```shell
$ git pull https://github.com/max-pfeiffer/simple-dynamic-dns-aws.git
$ cd dynamic-dns-update-client/opentofu
$ cp credentials.auto.tfvars.example credentials.auto.tfvars
$ vim credentials.auto.tfvars
```
Then run a couple of [OpenTofu](https://opentofu.org/) commands:
```shell
$ tofu init
$ tofu plan
$ tofu apply
```
The Lambda function URL and API token are provided as output. As `api_token` is marked, as security-sensitive you need
to call for it specifically:
```shell
$ tofu output lambda_function_url
$ tofu output api_token
```
For updating the DNS entry for your domain just call your new Lambda function adding your `ip` and your `client_id`:
```shell
$ curl "https://uwigefgf8437rgeydbea2q40jedbl.lambda-url.eu-central-1.on.aws/?domain=www.example.com&ip=123.45.56.78&client_id=myrouter&token=78234rtgf438g7g43r4bfi3784fgh"
```

## Dynamic DNS Client
Most consumer grade routers offer an option in their web user interface to configure updates for a dynamic DNS provider.
In a lot of cases, this is not very flexible and bound to some commercial providers that are out there. If the provider
you are using is not supported, you are screwed.
On [OpenWRT](https://openwrt.org/) routers [configuration options are plentyful](https://openwrt.org/docs/guide-user/services/ddns/client),
but configuration is a nightmare, especially if you have some more exotic use case like I have.

![2025-06-27_dynamic_dns_update_client.png]({static}/images/2025-06-27_dynamic_dns_update_client.png)

So I decided to write a [dynamic-dns-update-client](https://github.com/max-pfeiffer/dynamic-dns-update-client) myself.
It's basically a companion project for [Simple Dynamic DNS with AWS](https://github.com/max-pfeiffer/simple-dynamic-dns-aws).
It's a little CLI tool written in Python that obtains your public IP address by different means and then updates the IP
address at the dynamic DNS provider using an HTTP request. You can run it locally on your machine,
on an [OpenWRT](https://openwrt.org/) router or on any other machine in your infrastructure. It requires:

* Python v3.11 or higher
* pip

You can pick from four methods for getting the public IP address:

* `openwrt_network`: on an OpenWRT device by calling OpenWRT specific functions
* `interface`: physical network interface to look for the public IP address (parses `ip` or `ifconfig` output)
* by calling one of the following IP address services using an HTTP GET request:
    * `ipify`: [https://www.ipify.org](https://www.ipify.org/)
    * `dyndns`: [https://help.dyn.com/remote-access-api/checkip-tool](https://help.dyn.com/remote-access-api/checkip-tool/)

This way you are quite flexible where you run it. You can install and run it on your router in front of your
infrastructure. Or you can run it on any device or in a container anywhere else in your IT infrastructure behind your
router when you use one of the two IP address services.

## Usage
Install it with pip:
```shell
$ pip install dynamic-dns-update-client
```

You can use it for calling your new Lamda function, which you created with [Simple Dynamic DNS with AWS](https://github.com/max-pfeiffer/simple-dynamic-dns-aws). 
Start playing around and use the `--dry-run` option to check how it works:
```shell
$ dynamic-dns-update-client https://uwigefgf8437rgeydbea2q40jedbl.lambda-url.eu-central-1.on.aws/ \
  --ip-address-url-parameter-name ip \
  --url-parameter domain=example.com \
  --url-parameter api-token=nd4u33huruffbn \
  --dry-run
Current IP address: 82.4.110.122
Dry run, no changes will be made.
Dynamic DNS provider URL: https://uwigefgf8437rgeydbea2q40jedbl.lambda-url.eu-central-1.on.aws/?ip-address=82.4.110.122&domain=example.com&api-token=nd4u33huruffbn
```

## OpenWRT installation/configuration
For installing and running [dynamic-dns-update-client](https://github.com/max-pfeiffer/dynamic-dns-update-client) on
your [OpenWRT](https://openwrt.org/) router, you need to install the Python v3 interpreter and pip. You need the
packages python3-light and python3-pip (and some MB of free space on your router). The packages can be installed via
Luci web interface or via SSH:
```shell
$ opkg install python3-light python3-pip
$ pip install dynamic-dns-update-client
```

If you want to use it on your [OpenWRT](https://openwrt.org/) router, just
[add a cron job](https://openwrt.org/docs/guide-user/base-system/cron) for it. DNS entries are cached. In my experience,
an update every 10 minutes is sufficient. It's also a good idea to leverage the `--cache-ip-address` option. This
minimizes the number of HTTP requests you send to the dynamic DNS server. If you happen to use my solution, AWS is
billing you for every Lambda function run. 

So a crontab entry for an [OpenWRT](https://openwrt.org/) router would look like this:
```shell
*/10 * * * *  dynamic-dns-update-client https://example.com --ip-address-provider openwrt_network --ip-address-url-parameter-name ip --url-parameter domain=example.com --url-parameter api-token=nd4u33huruffbn --cache-ip-address

```
