# -*- coding: utf-8 -*-


import datetime
import requests
import urllib.request, urllib.parse, urllib.error
import os
import yaml
import argparse  

from datetime import timedelta, tzinfo
from functools import wraps

from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from validators import url
import google.auth
import googleapiclient.discovery
CLOUD_RM = 'https://cloudresourcemanager.googleapis.com/v1/projects'
ZERO = timedelta(0)

class UTC(tzinfo):
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return ZERO

utc = UTC()

def get_policy(project_id, version=3):
    credentials, project = google.auth.default()
    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
    )
    policy = (
        service.projects()
        .getIamPolicy(
            resource=project_id,
            body={"options": {"requestedPolicyVersion": version}},
        )
        .execute()
    )
    return policy


def set_policy(project_id, policy):
    credentials, project = google.auth.default()
    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
    )

    policy = (
        service.projects()
        .setIamPolicy(resource=project_id, body={"policy": policy})
        .execute()
    )

    return policy

def validate_exclude_members(member):
    with open(os.getenv('CONFIG_YAML_PATH')) as file:
        obj = yaml.safe_load(file)
        members = obj['exclude_members']

    exists = False
    for v in members:
        if v == member:
            exists = True

    return exists

def validate_role(role):
    with open(os.getenv('CONFIG_YAML_PATH')) as file:
        obj = yaml.safe_load(file)
        roles = obj['allow_roles']

    exists = False
    for v in roles:
        if v['role'] == role:
            exists = True

    return exists

def clear_confition(project):
    new_policy = {'policy': get_policy(project)}
    bindings = []
    for b in new_policy['policy']['bindings']:
        if 'condition' in b:
            if 'granted' in b['condition']['title']:
                continue

        bindings.append(b)

    new_policy['policy']['bindings'] = bindings
    new_policy['policy']['version'] = 3

    try:
        set_policy(project, new_policy['policy'])
    except (OAuth2Error, requests.HTTPError):
        print('Could not apply new policy')
        return

    return

def set_condition(period, project, user_or_group, account, access):
    """exclude_membersの場合は制限を受けない"""
    if validate_exclude_members(account) == False and validate_role(access) == False:
        raise Exception('{}は許可されていません。config.ymlを確認してください。'.format(access))

    expiry = (datetime.datetime.now(utc) + datetime.timedelta(
        minutes=period)).isoformat()

    new_policy = {'policy': get_policy(project)}

    new_policy['policy']['bindings'].append(
        {'condition': {
            'expression': 'request.time < timestamp("{}")'.format(expiry),
            'description': 'This is a temporary grant created by GithuｂActions',
            'title': 'granted by {}'.format(os.getenv('GITHUB_ACTOR'))},
        'members': ['{}:{}'.format(user_or_group,account)],
        'role': access})

    new_policy['policy']['version'] = 3

    try:
        set_policy(project, new_policy['policy'])
    except (OAuth2Error, requests.HTTPError):
        print('Could not apply new policy')
        return
    print("Great success, they'll have access in a minute!", 'success')
    return

def command_clear(args):
    clear_confition(os.getenv('IAM_PROJECT'))

def command_set(args):
    set_condition(int(os.getenv('IAM_PERIOD')), os.getenv('IAM_PROJECT'), "user", os.getenv('IAM_TARGET_ACCOUNT'), os.getenv('IAM_ACCESS'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_clear = subparsers.add_parser('clear')
    parser_clear.set_defaults(handler=command_clear)

    parser_set = subparsers.add_parser('set')
    parser_set.set_defaults(handler=command_set)

    args = parser.parse_args()
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()