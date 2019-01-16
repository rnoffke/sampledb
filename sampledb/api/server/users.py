# coding: utf-8
"""
RESTful API for iffSamples
"""

from flask_restful import Resource

from .authentication import http_basic_auth
from ...logic import errors, users

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def user_to_json(user: users.User):
    return {
        'user_id': user.id,
        'name': user.name
    }


class User(Resource):
    @http_basic_auth.login_required
    def get(self, user_id: int):
        try:
            user = users.get_user(user_id=user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": "user {} does not exist".format(user_id)
            }, 404
        return user_to_json(user)


class Users(Resource):
    @http_basic_auth.login_required
    def get(self):
        return [user_to_json(user) for user in users.get_users()]
