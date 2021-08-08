import datetime

import pytest

from main import (
    Config,
    add_binding,
    get_binding,
    get_expiry,
    remove_condition_bindings,
    set_condition,
)


class TestConfig:
    @pytest.fixture
    def config(self):
        return Config(["roles/cloudscheduler.jobRunner"], ["test.user1@example.com"])

    class TestValidate:
        @pytest.mark.parametrize(
            "member,role",
            [
                ("hoge", "roles/cloudscheduler.jobRunner"),
                ("test.user1@example.com", "hoge"),
                ("test.user1@example.com", "roles/cloudscheduler.jobRunner"),
            ],
        )
        def test_not_exclude_member_and_role(self, config, member, role):
            assert config.validate("hoge", "roles/cloudscheduler.jobRunner") is None

        def test_not_exclude_member_and_not_role(self, config):
            with pytest.raises(Exception, match="hogeは許可されていません。config.ymlを確認してください。"):
                config.validate("hoge", "hoge")

    def test_config_read(self, config):
        assert Config.read("config.yml") == config


@pytest.mark.freeze_time(datetime.datetime(2021, 8, 1, 12, 34))
def test_get_expiry():
    assert get_expiry(61) == datetime.datetime(
        2021, 8, 1, 13, 35, tzinfo=datetime.timezone.utc
    )


@pytest.fixture
def binding():
    return {
        "condition": {
            "expression": f'request.time < timestamp("2021-08-01T12:34:00+00:00")',
            "description": "This is a temporary grant created by Github Actions",
            "title": f"granted by actor",
        },
        "members": [f"user:test.user1@example.com"],
        "role": "roles/cloudscheduler.jobRunner",
    }


def test_remove_condition_bindings(binding):
    assert remove_condition_bindings(
        [binding, {}, {"condition": {"title": "aaa"}}]
    ) == [{}, {"condition": {"title": "aaa"}}]


def test_get_binding(binding):
    assert (
        get_binding(
            expiry=datetime.datetime(2021, 8, 1, 12, 34, tzinfo=datetime.timezone.utc),
            user_or_group="user",
            account="test.user1@example.com",
            access="roles/cloudscheduler.jobRunner",
            actor="actor",
        )
        == binding
    )


def test_add_binding(binding):
    binding_init = {
        "members": [
            "serviceAccount:example@my-project.iam.gserviceaccount.com",
        ],
        "role": "roles/iam.serviceAccountKeyAdmin",
    }
    policy = {
        "bindings": [binding_init],
        "etag": "xxxxx",
        "version": 1,
    }

    assert add_binding(policy=policy, binding=binding) == {
        "bindings": [binding_init, binding],
        "etag": "xxxxx",
        "version": 3,
    }


class TestSetCondition:
    def test_raise(self):
        with pytest.raises(Exception, match="hogeは許可されていません。config.ymlを確認してください。"):
            set_condition(
                period=60,
                project="project",
                user_or_group="user",
                account="hoge",
                access="hoge",
                config_file="config.yml",
                actor="actor",
            )

    @pytest.mark.parametrize(
        "account,access",
        [
            ("hoge", "roles/cloudscheduler.jobRunner"),
            ("test.user1@example.com", "hoge"),
            ("test.user1@example.com", "roles/cloudscheduler.jobRunner"),
        ],
    )
    def test_ok(self, mocker, capfd, account, access):
        policy = {
            "bindings": [],
            "etag": "xxxxx",
            "version": 1,
        }
        mocker.patch("main.get_policy", return_value=policy)
        mocker.patch("main.set_policy", return_value=None)

        set_condition(
            period=60,
            project="project",
            user_or_group="user",
            account="hoge",
            access="roles/cloudscheduler.jobRunner",
            config_file="config.yml",
            actor="actor",
        )
        out, err = capfd.readouterr()
        assert out == "Great success, they'll have access in a minute! success\n"
