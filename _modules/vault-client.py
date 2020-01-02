# -*- coding: utf-8 -*-
from __future__ import absolute_import

import hvac
import logging

log = logging.getLogger(__name__)


def read_secret(path, key=None):
    """Retrieve secrets from vault cluster at a specified path
    Arguments:
        path {str} -- The path of the secret

    Keyword Arguments:
        key {str} -- A key of the returned secrets in vault (default: {None})

    Returns:
        string or dict -- The value of key at path in vault, or the entire secret
    """
    log.debug("Reading Vault secret for %s at %s", __grains__["id"], path)
    try:

        vault_client = __utils__["vault-client.get_vault_client"]()

        # Making request to Vault to retrieve the secrets at a specific path
        response = vault_client._adapter.get(url="v1/{}".format(path))

        if response.status_code != 200:
            response.raise_for_status()
        data = response.json()["data"]

        if key is not None:
            return data.get(key, None)
        return data
    except Exception as err:
        log.error("Failed to read secret! %s: %s", type(err).__name__, err)
        return None
