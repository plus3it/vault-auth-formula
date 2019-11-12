# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import json
import requests

log = logging.getLogger(__name__)

DEPS_INSTALLED = False
IMPORT_ERROR = ""
try:
    import hvac

    DEPS_INSTALLED = True
except ImportError as e:
    IMPORT_ERROR = e
    pass


def __virtual__():
    if DEPS_INSTALLED:
        return "vault-client"
    else:
        return False, "Missing required dependency. {}".format(IMPORT_ERROR)


def authenticated(
    name,
    auth_type,
    role,
    url=None,
    mount_point="aws",
    region="us-east-1",
    use_token=True,
    store_token=True,
    store_nonce=True,
):
    """Ensure that the ec2 instance has been authenticated with Vault

    Arguments:
        name {str} -- ID for state definition
        auth_type {str} -- The auth type will be used to authenticate with aws. Either `iam` or `ec2`
        role {str} -- Name of the role against which the login is being attempted

    Keyword Arguments:
        url {str} -- URL of the vault cluster, where the instance will authenticate and retrieve the client token (default: {None})
        mount_point {str} -- Path of the authentication method (default: {'aws'})
        region {str} -- Region where the instance is being deployed (default: {'us-east-1'})
        store_token {bool} -- Store the retrieved client_token to disk (default: {True})
        store_nonce {bool} -- Store the retrieved nonce toke to disk (default: {True})
        use_token {bool} -- if True, uses the token in the response received from the auth request to set the “token” attribute on the
        the `hvac.adapters.Adapter()` instance under the _adapater Client attribute (default: {True})

    Returns:
        dict -- The result of the state execution
    """
    auth_resp = {}
    iam_creds = {}
    ret = {"name": name, "comment": "", "result": "", "changes": {}}

    log.debug("Attempting to make an instance of the hvac.Client")
    vault_client = __utils__["vault-client.get_vault_client"](url)
    iam_creds = __utils__["vault-client.load_aws_ec2_role_iam_credentials"]()

    combined_args = {}
    base_args = {"role": role, "mount_point": mount_point, "use_token": True}

    log.debug("iam_creds: %s", json.dumps(iam_creds))

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
                "pkcs7": __utils__["vault-client.load_aws_ec2_pkcs7_string"](),
                "nonce": __utils__["vault-client.load_aws_ec2_nonce_from_disk"](),
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
        log.debug(
            "token_meta_nonce received back from auth_ec2 call: %s" % token_meta_nonce
        )
        __utils__["vault-client.write_aws_ec2_nonce_to_disk"](token_meta_nonce)
    else:
        log.warning("No token meta nonce returned in auth response.")
    # Write client token to file
    if store_token and "client_token" in auth_resp.get("auth", dict()):
        client_token = auth_resp["auth"]["client_token"]
        __utils__["vault-client.write_client_token_to_disk"](client_token)

    ret["result"] = True
    ret["changes"] = auth_resp

    return ret
