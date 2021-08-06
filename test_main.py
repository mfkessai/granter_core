import os

from main import validate_exclude_members, validate_role


def test_validate_role():
    os.environ["CONFIG_YAML_PATH"] = "config.yml"
    assert validate_role("hoge") == False
    assert validate_role("roles/cloudscheduler.jobRunner") == True


def test_validate_exclude_members():
    os.environ["CONFIG_YAML_PATH"] = "config.yml"
    assert validate_exclude_members("hoge") == False
    assert validate_exclude_members("test.user1@example.com") == True
