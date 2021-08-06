import datetime

import pytest

from main import Config, get_expiry


class TestConfig:
    @pytest.fixture
    def config(self):
        return Config(["roles/cloudscheduler.jobRunner"], ["test.user1@example.com"])

    class TestValidateRole:
        def test_false(self, config):
            assert config.validate_role("hoge") is False

        def test_true(self, config):
            assert config.validate_role("roles/cloudscheduler.jobRunner") is True

    class TestValidateExcludeMember:
        def test_false(self, config):
            assert config.validate_exclude_member("hoge") is False

        def test_true(self, config):
            assert config.validate_exclude_member("test.user1@example.com") is True

    def test_config_read(self, config):
        assert Config.read("config.yml") == config


@pytest.mark.freeze_time(datetime.datetime(2021, 8, 1, 12, 34))
def test_get_expiry():
    assert get_expiry(61) == datetime.datetime(
        2021, 8, 1, 13, 35, tzinfo=datetime.timezone.utc
    )
