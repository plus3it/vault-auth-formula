# vault-formula

This project uses a [SaltStack](http://saltstack.com/community/) [formula](https://docs.saltstack.com/en/latest/topics/development/conventions/formulas.html) to automatically authenticate the EC2 instance to an existing [Hashicorp Vault](https://www.hashicorp.com/products/vault) cluster.

This formula uses data externalized via the SaltStack "[Pillar](https://docs.saltstack.com/en/latest/topics/pillar/)"
feature. See the sections below for the data required to be present within the
supporting pillar.


## vault

```yaml
vault:
  lookup:
    url: https://vault.zyx.net
    role: vault-client-auth-iam
    auth_type: iam or ec2
    mount_point: 'aws'
    
```
