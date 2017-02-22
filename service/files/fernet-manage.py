#!/usr/bin/env python

import argparse
import base64
import json
import logging
import os
import re
import six
import subprocess
import sys

import pykube

GLOBALS_PATH = '/etc/ccp/globals/globals.json'
FERNET_DIR = '/etc/keystone/fernet-keys/'

LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT = "%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATEFMT)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

def get_config():
    LOG.info("Getting global variables from %s", GLOBALS_PATH)
    with open(GLOBALS_PATH) as f:
        global_conf = json.load(f)
    return global_conf

def get_pykube_client():
    os.environ['KUBERNETES_SERVICE_HOST'] = 'kubernetes.default'
    config = pykube.KubeConfig.from_service_account()
    return pykube.HTTPClient(config)

def get_secret_definition(name):
    client = get_pykube_client()
    obj_dict = {
        'metadata': {
            'name': name,
            'namespace': NAMESPACE
        }
    }
    secret = pykube.Secret(client, obj_dict)
    return secret

def read_from_files():
    keys = filter(
        lambda name: os.path.isfile(FERNET_DIR + name) and re.match("^\d+$", name),
        os.listdir(FERNET_DIR)
    )
    data = {}
    for key in keys:
        with open(FERNET_DIR + key, 'r') as f:
            data[key] = f.read()
    if len(keys):
        LOG.debug("Keys read from files: %s", keys)
    else:
        LOG.warn("No keys were read from files.")
    return data

def get_keys_data():
    keys = PROVIDED_KEYS or read_from_files()
    return dict([(key, base64.b64encode(value.encode()).decode())
               for (key, value) in six.iteritems(keys)])

def write_to_files(data):
    for (key, value) in six.iteritems(data):
        with open(FERNET_DIR + key, 'w') as f:
            decoded_value = base64.b64decode(value).decode()
            f.write(decoded_value)
            LOG.debug("Key %s: %s", key, decoded_value)
    LOG.info("%s keys were written", len(data))

def set_globals():
    LOG.info("Setting up global variables")
    global NAMESPACE, SECRET_NAME, PROVIDED_KEYS
    config = get_config()

    NAMESPACE = config['namespace']
    LOG.debug("Namespace: %s", NAMESPACE)

    SECRET_NAME = config['keystone']['fernet_secret_name']
    LOG.debug("Secret name: %s", SECRET_NAME)

    PROVIDED_KEYS = None
    if 'fernet_keys' in config['keystone']:
        PROVIDED_KEYS = config['keystone']['fernet_keys']
        LOG.debug("Fernet keys: %s", PROVIDED_KEYS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['fernet_setup', 'fernet_rotate'])
    args = parser.parse_args()

    secret = get_secret_definition(SECRET_NAME)
    if not secret.exists():
        LOG.error("Secret '%s' does not exist.", SECRET_NAME)
        sys.exit(1)

    secret.reload()
    if not PROVIDED_KEYS:
        LOG.info("No fernet keys were provided in the config.")
        if args.command == 'fernet_rotate':
            LOG.info("Copying existing fernet keys from secret '%s' to %s.", SECRET_NAME, FERNET_DIR)
            write_to_files(secret.obj['data'])

        LOG.info("Executing 'keystone-manage %s --keystone-user=keystone --keystone-group=keystone' command.",
                 args.command)
        subprocess.call(['keystone-manage', args.command, '--keystone-user=keystone', '--keystone-group=keystone'])

    LOG.info("Updating data for '%s' secret.", SECRET_NAME)
    updated_keys = get_keys_data()
    secret.obj['data'] = None
    secret.update()
    secret.obj['data'] = updated_keys
    secret.update()
    LOG.info("%s fernet keys have been placed to secret '%s'", len(updated_keys), SECRET_NAME)
    LOG.debug("Placed keys: %s", updated_keys)
    LOG.info("Fernet keys %s has been completed", "rotation" if args.command == 'fernet_rotate' else "generation")

if __name__ == "__main__":
    set_globals()
    main()
