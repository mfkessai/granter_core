import argparse
import copy
import datetime
import os
from dataclasses import dataclass
from typing import List

import google.auth
import googleapiclient.discovery
import requests
import yaml
from oauthlib.oauth2.rfc6749.errors import OAuth2Error


@dataclass
class Config:
    allow_roles: List[str]
    exclude_members: List[str]

    def validate(self, member, role):
        if member not in self.exclude_members and role not in self.allow_roles:
            raise Exception(f"{role}は許可されていません。config.ymlを確認してください。")

    @staticmethod
    def read(file) -> "Config":
        with open(file) as f:
            obj = yaml.safe_load(f)
        return Config(
            allow_roles=[allow_roles["role"] for allow_roles in obj["allow_roles"]],
            exclude_members=obj["exclude_members"],
        )


def fetch_policy(project_id: str, version=3):
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


def set_policy(project_id: str, policy):
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


def remove_condition_bindings(bindings):
    return [
        b
        for b in bindings
        if "condition" not in b or "granted" not in b["condition"]["title"]
    ]


def clear_condition(project: str):
    new_policy = fetch_policy(project)

    new_policy["bindings"] = remove_condition_bindings(new_policy["bindings"])
    new_policy["version"] = 3

    try:
        set_policy(project, new_policy)
    except (OAuth2Error, requests.HTTPError):
        print("Could not apply new policy")
        return

    return


def get_expiry(minutes: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=minutes
    )


def get_binding(
    expiry: datetime.datetime, user_or_group: str, account: str, access: str, actor: str
):
    return {
        "condition": {
            "expression": f'request.time < timestamp("{expiry.isoformat()}")',
            "description": "This is a temporary grant created by Github Actions",
            "title": f"granted by {actor}",
        },
        "members": [f"{user_or_group}:{account}"],
        "role": access,
    }


def add_binding(policy, binding):
    new_policy = copy.deepcopy(policy)

    new_policy["bindings"].append(binding)
    new_policy["version"] = 3

    return new_policy


def set_condition(
    period: int,
    project: str,
    user_or_group: str,
    account: str,
    access: str,
    config_file: str,
    actor: str,
):
    """exclude_membersの場合は制限を受けない"""
    config = Config.read(config_file)
    config.validate(member=account, role=access)

    expiry = get_expiry(period)
    binding = get_binding(
        expiry=expiry,
        user_or_group=user_or_group,
        account=account,
        access=access,
        actor=actor,
    )
    policy = fetch_policy(project)
    new_policy = add_binding(policy=policy, binding=binding)

    try:
        set_policy(project, new_policy)
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
            config_file=os.getenv("CONFIG_YAML_PATH"),
            actor=os.getenv("GITHUB_ACTOR"),
        )
