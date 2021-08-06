import argparse
import datetime
import os
from dataclasses import dataclass
from typing import List

import google.auth
import googleapiclient.discovery
import requests
import yaml
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

CLOUD_RM = "https://cloudresourcemanager.googleapis.com/v1/projects"


@dataclass
class Config:
    allow_roles: List[str]
    exclude_members: List[str]

    def validate_exclude_member(self, member):
        return member in self.exclude_members

    def validate_role(self, role):
        return role in self.allow_roles

    @staticmethod
    def read(file) -> "Config":
        with open(file) as f:
            obj = yaml.safe_load(f)
        return Config(
            allow_roles=[allow_roles["role"] for allow_roles in obj["allow_roles"]],
            exclude_members=obj["exclude_members"],
        )


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


def clear_condition(project):
    new_policy = {"policy": get_policy(project)}
    bindings = []
    for b in new_policy["policy"]["bindings"]:
        if "condition" in b:
            if "granted" in b["condition"]["title"]:
                continue

        bindings.append(b)

    new_policy["policy"]["bindings"] = bindings
    new_policy["policy"]["version"] = 3

    try:
        set_policy(project, new_policy["policy"])
    except (OAuth2Error, requests.HTTPError):
        print("Could not apply new policy")
        return

    return


def get_expiry(minutes: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=minutes
    )


def set_condition(period, project, user_or_group, account, access):
    """exclude_membersの場合は制限を受けない"""
    config = Config.read(os.getenv("CONFIG_YAML_PATH"))
    if not config.validate_exclude_member(account) and not config.validate_role(access):
        raise Exception("{}は許可されていません。config.ymlを確認してください。".format(access))

    expiry = get_expiry(period).isoformat()

    new_policy = {"policy": get_policy(project)}

    new_policy["policy"]["bindings"].append(
        {
            "condition": {
                "expression": 'request.time < timestamp("{}")'.format(expiry),
                "description": "This is a temporary grant created by Github Actions",
                "title": "granted by {}".format(os.getenv("GITHUB_ACTOR")),
            },
            "members": ["{}:{}".format(user_or_group, account)],
            "role": access,
        }
    )

    new_policy["policy"]["version"] = 3

    try:
        set_policy(project, new_policy["policy"])
    except (OAuth2Error, requests.HTTPError):
        print("Could not apply new policy")
        return
    print("Great success, they'll have access in a minute!", "success")
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices={"clear", "set"})

    args = parser.parse_args()
    if args.target == "clear":
        clear_condition(os.getenv("IAM_PROJECT"))
    if args.target == "set":
        set_condition(
            period=int(os.getenv("IAM_PERIOD")),
            project=os.getenv("IAM_PROJECT"),
            user_or_group="user",
            account=os.getenv("IAM_TARGET_ACCOUNT"),
            access=os.getenv("IAM_ACCESS"),
        )
