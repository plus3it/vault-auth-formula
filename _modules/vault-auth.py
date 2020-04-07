# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import json

log = logging.getLogger(__name__)
__virtualname__ = "vault_auth"

DEPS_INSTALLED = False
IMPORT_ERROR = ""
try:
    import hvac

    DEPS_INSTALLED = True
except ImportError as e:
    IMPORT_ERROR = e
    pass


def __virtual__():
    """
    Determine whether or not to load this module
    """
    if DEPS_INSTALLED:
        return __virtualname__
    else:
        return False, "Missing required dependency. {}".format(IMPORT_ERROR)


def authenticate(
    auth_type,
    role,
    url=None,
    mount_point="aws",
    region="us-east-1",
    use_token=True,
    store_token=True,
    store_nonce=True,
):
    """Authenticate the ec2 instance to Vault

    Arguments:
        auth_type {str} -- The auth type will be used to authenticate with aws. Either `iam` or `ec2`
        role {str} -- Name of the role against which the login is being attempted

    Keyword Arguments:
        url {str} -- URL of the vault cluster, where the instance will authenticate and retrieve the client token (default: {None})
        mount_point {str} -- Path of the authentication method (default: {'aws'})
        region {str} -- Region where the instance is being deployed (default: {'us-east-1'})
        store_token {bool} -- Store the retrieved client_token to disk (default: {True})
        store_nonce {bool} -- Store the retrieved nonce token to disk (default: {True})
        use_token {bool} -- if True, uses the token in the response received from the auth request to set the “token” attribute on the
        the `hvac.adapters.Adapter()` instance under the _adapater Client attribute (default: {True})

    Returns:
        dict -- The result of the state execution
    """
    auth_resp = {}
    iam_creds = {}

    log.debug("Attempting to make an instance of the hvac.Client")
    vault_client = __utils__["vault_auth.get_vault_client"](url)
    iam_creds = __utils__["vault_auth.load_aws_ec2_role_iam_credentials"]()

    combined_args = {}
    base_args = {"role": role, "mount_point": mount_point, "use_token": use_token}

    funcs = {
        "iam": {
            "login": vault_client.auth.aws.iam_login,
            "params": {
                "access_key": iam_creds.get("AccessKeyId"),
                "secret_key": iam_creds.get("SecretAccessKey"),
                "session_token": iam_creds.get("Token"),
                "header_value": None,
                "region": region,
            },
        },
        "ec2": {
            "login": vault_client.auth.aws.ec2_login,
            "params": {
                "pkcs7": __utils__["vault_auth.load_aws_ec2_pkcs7_string"](),
                "nonce": __utils__["vault_auth.load_aws_ec2_nonce_from_disk"](),
            },
        },
    }

    # Combining the params
    combined_args.update(base_args)
    combined_args.update(funcs[auth_type]["params"])

    auth_resp = funcs[auth_type]["login"](**combined_args)

    if store_nonce and "metadata" in auth_resp.get("auth", dict()):
        token_meta_nonce = auth_resp["auth"]["metadata"].get("nonce")
    if token_meta_nonce is not None:
        __utils__["vault_auth.write_aws_ec2_nonce_to_disk"](token_meta_nonce)
    else:
        log.warning("No token meta nonce returned in auth response.")
    # Write client token to file
    if store_token and "client_token" in auth_resp.get("auth", dict()):
        client_token = auth_resp["auth"]["client_token"]
        __utils__["vault_auth.write_client_token_to_disk"](client_token)

    return auth_resp


def read_secret(path, key=None, url=None):
    """Retrieve secrets from vault cluster at a specified path
    Arguments:
        path {str} -- The path of the secret

    Keyword Arguments:
        key {str} -- A key of the returned secrets in vault (default: {None})
        url {str} -- URL for the vault server (default: {None})

    Returns:
        string or dict -- The value of key at path in vault, or the entire secret
    """
    log.debug("Reading Vault secret for %s at %s", __grains__["id"], path)

    vault_client = __utils__["vault_auth.get_vault_client"](url)

    if not vault_client.is_authenticated():
        raise Exception("Instance is not authenticated. Need to authenticate first")

    # Making request to Vault to retrieve the secrets at a specific path
    response = vault_client._adapter.get(url="v1/{}".format(path))

    if response.status_code != 200:
        response.raise_for_status()
    data = response.json()["data"]

    if key is not None:
        return data.get(key, None)
    return data
