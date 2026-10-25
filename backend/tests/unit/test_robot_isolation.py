"""robot 子程序隔離：不帶金鑰、可改以另一個使用者執行。"""
import os

from src.core.config import get_settings
from src.core.security import CAPTCHA_SCOPE, decode_token
from src.services import execution_service as es


def test_command_unchanged_without_run_as_user(monkeypatch):
    monkeypatch.setattr(get_settings(), "robot_run_as_user", "")
    assert es._robot_command(["python", "-m", "robot", "x.robot"], timeout_sec=60) == ["python", "-m", "robot", "x.robot"]


def test_command_runs_as_other_user_with_timeout(monkeypatch):
    monkeypatch.setattr(get_settings(), "robot_run_as_user", "runner")
    cmd = es._robot_command(["python", "-m", "robot", "x.robot"], timeout_sec=60)
    assert cmd[:6] == ["sudo", "-n", "-E", "-H", "-u", "runner"]
    assert cmd[-7:] == ["timeout", "--kill-after=10", "60", "python", "-m", "robot", "x.robot"]


def test_shared_dir_only_opened_when_running_as_other_user(monkeypatch, tmp_path):
    d = tmp_path / "run"
    d.mkdir(mode=0o700)
    monkeypatch.setattr(get_settings(), "robot_run_as_user", "")
    es._make_shared_dir(str(d))
    assert d.stat().st_mode & 0o777 == 0o700
    monkeypatch.setattr(get_settings(), "robot_run_as_user", "runner")
    es._make_shared_dir(str(d))
    assert d.stat().st_mode & 0o777 == 0o777


def test_robot_env_has_captcha_token_but_no_secrets(monkeypatch):
    for key in ("JWT_SECRET_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "s" * 40)
    env = es._build_robot_env()
    assert not {"JWT_SECRET_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"} & env.keys()
    assert env["AUTOTEST_API_URL"] == get_settings().internal_api_url
    payload = decode_token(env["AUTOTEST_CAPTCHA_TOKEN"])
    assert payload["scope"] == CAPTCHA_SCOPE and "sub" not in payload
    assert payload["exp"] - payload["iat"] == 20 * 60
    assert os.environ.get("AUTOTEST_CAPTCHA_TOKEN") is None  # 不寫回後端自己的環境
