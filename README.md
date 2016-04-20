# Keystone VOMS auth module

## Keystone Federation

Keystone includes support for [identity federation](http://specs.openstack.org/openstack/keystone-specs/api/v3/identity-api-v3-os-federation-ext.html) since the Juno release, however the support for using VOMS authentication works from Mitaka onwards (due to a limitation in the user names length for federation users in previous versions).

### Requirements

VOMS authentication requires Keystone to be run as a WSGI application behind an Apache server with [gridsite](https://github.com/CESNET/gridsite) support. GridSite is a set of extensions to the Apache 2.0 webserver, which support Grid security based on X.509 certificates.


#### Installation

GridSite is available from standard distribution repositories (EPEL, Debian) but not always in its most recent versions. EGI's UMD repository may be a better source, especially if you are part of EGI.

You also need EUgridPMA certificates installed on its standard location (/etc/grid-security/certificates) and the fetch-crl package properly working so as have the CRLs up to date.

Use these commands to install on Ubuntu:
```
# wget -q -O - https://dist.eugridpma.info/distribution/igtf/current/GPG-KEY-EUGridPMA-RPM-3 | apt-key add -
# echo "deb http://repository.egi.eu/sw/production/cas/1/current egi-igtf core" \
  | tee --append /etc/apt/sources.list.d/egi-cas.list
# apt-get update
# apt-get install ca-policy-egi-core fetch-crl gridsite
# fetch-crl
```

CentOS 7:
```
# curl -L http://repository.egi.eu/sw/production/cas/1/current/repo-files/EGI-trustanchors.repo > /etc/yum.repos.d/EGI-trustanchors.repo
# yum install ca-policy-egi-core fetch-crl gridsite
```

Once the packages are installed, run fetch-crl to get the latest CRLs:
```
# fetch-crl -v
```

#### Apache configuration

GridSite module is enabled by default once installed. 

Configure Keystone on Apache as usual and add SSL support to the Keystone Virtual Hosts (adapt the location of the certificate and key to your own installation):
```
  SSLEngine               on
  SSLCertificateFile      /etc/ssl/certs/hostcert.pem
  SSLCertificateKeyFile   /etc/ssl/private/hostkey.pem
  SSLCACertificatePath    /etc/grid-security/certificates
  SSLCARevocationPath     /etc/grid-security/certificates
  SSLVerifyClient         optional
  SSLVerifyDepth          10
  SSLProtocol             all -SSLv2
  SSLCipherSuite          ALL:!ADH:!EXPORT:!SSLv2:RC4+RSA:+HIGH:+MEDIUM:+LOW
  SSLOptions              +StdEnvVars +ExportCertData
```

### Configuration

- Enable federation and the mapped authentication in `keystone.conf` :

```
[auth]
# add here mapped
methods = external,password,token,mapped
# define mapped
mapped = keystone.auth.plugins.mapped.Mapped
...

[federation]
driver = sql 
...
```

- Create a new `voms` IdP in your Keystone (you must use V3 authentication for the commands to work):
```
$ openstack identity provider create voms
+-------------+-------+
| Field       | Value |
+-------------+-------+
| description | None  |
| enabled     | True  |
| id          | voms  |
| remote_ids  |       |
+-------------+-------+
```

- Create the rules to map VO users to your local Keystone groups and users. These rules are defined in a JSON file like the one below. **Be sure to use existing group in the mapping, otherwise Keystone will return an error 500 when trying to authenticate**. You can add as many mappings as you like in the file (e.g. for different VOs)
```
$ cat rules.json
[
    {
        "local": [
            {
                "user": {
                    "name": "{0}",
                    "type": "ephemeral"
                },
                "group": {
                    "id": "e1eeb432597d421cab67bb02f3cebadb"
                }
            }
        ],
        "remote": [
            {
                "type": "GRST_CRED_AURI_0"
            },
            {
                "type": "GRST_CRED_AURI_2",
                "any_one_of": [
                    "fqan:/dteam/.*"
                ],
                "regex": true
            }
        ]
    }
]
```
- Create the mapping in keystone:
```
$ openstack mapping create --rules rules.json voms
+-------+--------------------------------------------------------------------------------+
| Field | Value                                                                          |
+-------+--------------------------------------------------------------------------------+
| id    | voms                                                                           |
| rules | [{u'remote': [{u'type': u'GRST_CRED_AURI_0'}, {u'regex': True, u'type':        |
|       | u'GRST_CRED_AURI_2', u'any_one_of': [u'fqan:/dteam/.*']}], u'local':           |
|       | [{u'group': {u'id': u'e1eeb432597d421cab67bb02f3cebadb'}, u'user': {u'type':   |
|       | u'ephemeral', u'name': u'{0}'}}]}, {u'remote': [{u'type':                      |
|       | u'GRST_CRED_AURI_0'}, {u'regex': True, u'type': u'GRST_CRED_AURI_2',           |
|       | u'any_one_of': [u'fqan:/vo.lifewatch.eu/.*']}], u'local': [{u'group': {u'id':  |
|       | u'6c3acdb7150f4164b90e33d644b6f006'}, u'user': {u'type': u'ephemeral',         |
|       | u'name': u'{0}'}}]}]                                                           |
+-------+--------------------------------------------------------------------------------+
```

- Create the federated protocol in Keystone:
```
$ openstack federation protocol create --identity-provider voms --mapping voms mapped
+-------------------+--------+
| Field             | Value  |
+-------------------+--------+
| id                | mapped |
| identity_provider | voms   |
| mapping           | voms   |
+-------------------+--------+
```

- For each VO you want to support, you need to properly configure the `.lsc` files which determine the chain of trust of the VOMS server. For example for dteam VO you will need to have two files, one for each VOMS server, you can create them like this:
```
# mkdir -p /etc/grid-security/vomsdir/dteam
# cat > /etc/grid-security/vomsdir/dteam/voms.hellasgrid.gr.lsc << EOF
/C=GR/O=HellasGrid/OU=hellasgrid.gr/CN=voms.hellasgrid.gr
/C=GR/O=HellasGrid/OU=Certification Authorities/CN=HellasGrid CA 2006
EOF
# cat > /etc/grid-security/vomsdir/dteam/voms2.hellasgrid.gr.lsc << EOF
/C=GR/O=HellasGrid/OU=hellasgrid.gr/CN=voms2.hellasgrid.gr
/C=GR/O=HellasGrid/OU=Certification Authorities/CN=HellasGrid CA 2006 
EOF
```

## Authentication

Once your Keystone is configured, you can get an unscoped token by submitting a request to  `/OS-FEDERATION/identity_providers/voms/protocols/mapped/auth` with your proxy certificate:

```
$ curl -i --cert proxy https://keystonehost:5000/v3/OS-FEDERATION/identity_providers/voms/protocols/mapped/auth
HTTP/1.1 201 Created
Date: Wed, 20 Apr 2016 11:22:32 GMT
Server: Apache/2.4.6 (CentOS) OpenSSL/1.0.1e-fips mod_wsgi/3.4 Python/2.7.5 mod_gridsite/2.2.6
X-Subject-Token: gAAAAABXF2Z
Vary: X-Auth-Token
x-openstack-request-id: req-e1fda8fc-36b1-4723-9458-5dedb47e62fd
Content-Length: 454
Content-Type: application/json

{"token": {"issued_at": "2016-04-20T11:22:32.000000Z", "audit_ids": ["XhfzVChgTaGZAN-keP4s4w"], "methods": ["mapped"], "expires_at": "2016-04-20T12:22:32.639798Z", "user": {"OS-FEDERATION": {"identity_provider": {"id": "voms"}, "protocol": {"id": "mapped"}, "groups": [{"id": "e1eeb432597d421cab67bb02f3cebadb"}]}, "domain": {"id": "Federated", "name": "Federated"}, "id": "0dfabc73570b4a41a432aa1d3109c799", "name": "0dfabc73570b4a41a432aa1d3109c799"}}}
```

Token id will be returned at the `X-Subject-Token` header. With this token you can get the list of projects allowed to your user:
```
$ export KID="gAAAAABXF2Z"
$ curl -k -H 'x-auth-token: '$KID https://keystonehost:5000/v3/OS-FEDERATION/projects | python -mjson.tool
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   443  100   443    0     0   1669      0 --:--:-- --:--:-- --:--:--  1671
{
    "links": {
        "next": null,
        "previous": null,
        "self": "https://keystonehost:5000/v3/OS-FEDERATION/projects"
    },
    "projects": [
        {
            "description": "Demo Project",
            "domain_id": "307f0b7de7474b599cef6f27228929e2",
            "enabled": true,
            "id": "82dbda8",
            "is_domain": false,
            "links": {
                "self": "https://keystonehost:5000/v3/projects/82dbda8"
            },
            "name": "demo",
            "parent_id": "307f0b7de7474b599cef6f27228929e2"
        }
    ]
}
```

Finally you can get an scoped token by sumitting a POST request to `/auth/tokens` with a json body like this:
```
{
    "auth": {
        "identity": {
            "methods": [
                "token"
            ],
            "token": {
                "id": "<your token id>"
            }
        },
        "scope": {
            "project": {
                "id": "<your project ID>"
            }
        }
    }
}
```

For example:
```
$ curl -k -H 'x-auth-token: '$KID -H "Content-type: application/json" \
       -d '{ "auth": { "identity": { "methods": ["token"], "token": { "id": "gAAAAABXF2Z"}}, "scope": {"project": { "id": "82dbda8"}}}}' \
       https://keystonehost:5000/v3/auth/tokens
```

[Build Status]: https://travis-ci.org/IFCA/keystone-voms
[BS img]: https://travis-ci.org/IFCA/keystone-voms.png
