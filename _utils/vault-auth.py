# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import json
import requests
import os
import hvac

log = logging.getLogger(__name__)
__virtualname__ = "vault_auth"


TOKEN_ROOT_PATH = os.getenv("WP_VAULT_TOKEN_ROOT_PATH", "~")
TOKEN_FILE_NAME = os.getenv("WP_VAULT_TOKEN_FILE_NAME", ".vault-token")
TOKEN_NONCE_FILE_NAME = os.getenv(
    "WP_VAULT_TOKEN_NONCE_FILE_NAME", ".vault-token-meta-nonce"
)
EC2_METADATA_URL_BASE = "http://169.254.169.254"


def __virtual__():
    """
    Determine whether or not to load this module
    """
    return __virtualname__


def load_aws_ec2_role_iam_credentials(
    role_name=None, metadata_url_base=EC2_METADATA_URL_BASE
):
    """Requests an ec2 instance's IAM security credentials from the EC2 metadata service.

    Keyword Arguments:
        role_name {str} -- Name of the instance's role. (default: {None})
        metadata_url_base {str} -- IP address for the EC2 metadata service. (default: {EC2_METADATA_URL_BASE})

    Returns:
        [dict] -- unmarshalled JSON response of the instance's security credentials
    """

    if not role_name:
        role_name_url = "{base}/latest/meta-data/iam/security-credentials".format(
            base=metadata_url_base
        )
        response = requests.get(role_name_url)
        response.raise_for_status()
        role_name = response.text

    metadata_pkcs7_url = "{base}/latest/meta-data/iam/security-credentials/{role}".format(
        base=metadata_url_base, role=role_name,
    )
    log.debug("load_aws_ec2_role_iam_credentials connecting to %s" % metadata_pkcs7_url)
    response = requests.get(url=metadata_pkcs7_url)
    response.raise_for_status()
    security_credentials = response.json()
    return security_credentials


def load_aws_ec2_pkcs7_string(metadata_url_base=EC2_METADATA_URL_BASE):
    """Requests an ec2 instance's pkcs7-encoded identity document from the EC2 metadata service.

    Keyword Arguments:
        metadata_url_base {str} -- IP address for the EC2 metadata service. (default: {EC2_METADATA_URL_BASE})

    Returns:
        str -- Pkcs7-encoded identity document from the EC2 metadata service
    """

    metadata_pkcs7_url = "{base}/latest/dynamic/instance-identity/pkcs7".format(
        base=metadata_url_base
    )
    log.debug("load_aws_ec2_pkcs7_string connecting to %s", metadata_pkcs7_url)

    response = requests.get(url=metadata_pkcs7_url)
    response.raise_for_status()

    pcks7 = response.text.replace("\n", "")

    return pcks7


def load_aws_ec2_nonce_from_disk(
    token_root_path=TOKEN_ROOT_PATH, token_nonce_file_name=TOKEN_NONCE_FILE_NAME
):
    """Helper method to load a previously stored "token_meta_nonce" returned in the
    initial authorization AWS EC2 request from the current instance to our Vault service.

    Keyword Arguments:
        token_nonce_path {str} -- The full filesystem path to a file containing the instance's
        token meta nonce. (default: {TOKEN_NONCE_PATH})

    Returns:
        str -- A previously stored "token_meta_nonce"
    """
    token_nonce_path = os.path.expanduser(
        os.path.join(token_root_path, token_nonce_file_name)
    )
    log.debug(
        "Attempting to load vault token meta nonce from path: %s" % token_nonce_path
    )
    try:
        with open(token_nonce_path, "rb") as nonce_file:
            nonce = nonce_file.readline()
    except IOError:
        log.warning(
            "Unable to load vault token meta nonce at path: %s" % token_nonce_path
        )
        nonce = None

    log.debug("Nonce loaded: %s" % nonce)
    return nonce


def write_aws_ec2_nonce_to_disk(
    token_meta_nonce,
    token_root_path=TOKEN_ROOT_PATH,
    token_nonce_file_name=TOKEN_NONCE_FILE_NAME,
):
    """Helper method to store the current "token_meta_nonce" returned from authorization AWS EC2 request
    from the current instance to our Vault service.

    Arguments:
        token_meta_nonce {str} -- the actual nonce

    Keyword Arguments:
        token_nonce_path {str} -- the full filesystem path to a file containing the instance's
        token meta nonce. (default: {TOKEN_NONCE_PATH})
    """
    token_nonce_path = os.path.expanduser(
        os.path.join(token_root_path, token_nonce_file_name)
    )
    log.debug('Writing nonce "%s" to file "%s".', token_meta_nonce, token_nonce_path)
    write_value_to_disk(token_meta_nonce, token_nonce_path)


def write_client_token_to_disk(
    client_token, token_root_path=TOKEN_ROOT_PATH, token_file_name=TOKEN_FILE_NAME
):
    """Helper method to store the current "client_token" returned from authorization AWS EC2 request
    from the current instance to our Vault service.

    Arguments:
        client_token {str} -- The client token

    Keyword Arguments:
        token_path {str} -- The full filesystem path to a file containing the client token. (default: {TOKEN_PATH})
    """
    token_path = os.path.expanduser(os.path.join(token_root_path, token_file_name))
    log.debug('Writing "{0}" to file "{1}".'.format(client_token, token_path))
    write_value_to_disk(client_token, token_path)


def write_value_to_disk(value, path):
    with open(path, "w") as file:
        file.write(value)


def get_vault_client(url=None, verify_certs=False):
    """Instantiates a hvac / vault client.

    Keyword Arguments:
        url {str} -- Url of the vault cluster. Use vault url from pillar if no url is provided (default: {None})
        verify_certs {bool} -- A boolean to indicate whether TLS verification should be performed when sending requests to Vault (default: {False})

    Returns:
        hvac.Client -- An instance of the hvac.Client
    """
    log.debug("Retrieving a vault (hvac) client...")

    # Retrieves the vault url from pillar
    vault_url = url or __pillar__["vault"]["lookup"]["url"]
    vault_client = hvac.Client(url=vault_url, verify=verify_certs,)

    vault_client.token = hvac.utils.get_token_from_env()

    return vault_client
