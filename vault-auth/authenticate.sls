{%- set vault = salt['pillar.get']('vault:lookup', {}) %}

# Attempt to authenticate the instance with vault using the values provided
# from the pillar
authenticate EC2 instance:
  vault_auth.authenticated:
    - auth_type: {{ vault.auth_type }}
    - url: {{ vault.url }}
    - role: {{ vault.role }}
    - mount_point: {{ vault.mount_point }}
