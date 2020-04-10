# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import json
import requests

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
        store_nonce {bool} -- Store the retrieved nonce token to disk (default: {True})
        use_token {bool} -- if True, uses the token in the response received from the auth request to set the “token” attribute on the
        the `hvac.adapters.Adapter()` instance under the _adapater Client attribute (default: {True})

    Returns:
        dict -- The result of the state execution
    """
    ret = {"name": name, "comment": "", "result": "", "changes": {}}

    log.debug("Attempting to make an instance of the hvac.Client")
    vault_client = __utils__["vault_auth.get_vault_client"](url)

    log.debug("Checking if instance is already authenticated")
    if not vault_client.is_authenticated():
        log.debug("Attempting to authenticate to vault")
        auth_resp = __salt__["vault_auth.authenticate"](
            auth_type,
            role,
            url=url,
            mount_point=mount_point,
            region=region,
            use_token=use_token,
            store_token=store_token,
            store_nonce=store_nonce,
        )
        ret["changes"] = auth_resp
    else:
        ret["comment"] = "Instance is already authenticated"

    ret["result"] = True

    return ret
