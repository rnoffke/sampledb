# coding: utf-8
"""

"""

import base64
import binascii
import functools
import os

import flask
import flask_login

from . import logic
from .logic.authentication import login
from .models import Permissions, Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def object_permissions_required(required_object_permissions: Permissions):
    def decorator(func):
        @flask_login.login_required
        @functools.wraps(func)
        def wrapper(**kwargs):
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            if Objects.get_current_object(object_id) is None:
                return flask.abort(404)
            if not logic.permissions.object_is_public(object_id):
                user_id = flask_login.current_user.id
                user_object_permissions = logic.permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
                if required_object_permissions not in user_object_permissions:
                    # TODO: handle lack of permissions better
                    return flask.abort(403)
            return func(**kwargs)
        return wrapper
    return decorator


def load_environment_configuration(env_prefix):
    """
    Loads configuration data from environment variables with a given prefix.
    
    :return: a dict containing the configuration values
    """
    config = {
        key[len(env_prefix):]: value
        for key, value in os.environ.items()
        if key.startswith(env_prefix)
    }
    return config


def generate_secret_key(num_bits):
    """
    Generates a secure, random key for the application.
    
    :param num_bits: number of bits of random data in the secret key
    :return: the base64 encoded secret key
    """
    num_bytes = num_bits // 8
    binary_key = os.urandom(num_bytes)
    base64_key = base64.b64encode(binary_key).decode('ascii')
    return base64_key
