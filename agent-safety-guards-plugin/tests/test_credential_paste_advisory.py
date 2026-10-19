"""Offline tests for hooks/credential_paste_advisory.py (ASG-P2-04).

All token-shaped strings below are synthetic: random-looking characters in the public
prefix formats, not real credentials.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
HOOK = HOOKS / "credential_paste_advisory.py"
spec = importlib.util.spec_from_file_location("cpa", HOOK)
cpa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpa)

FAKE = "Q7mZ2kLp9XvR4tYw8NbC3dFh6JsG1aKe"

SECRETS = [
    "my token is ghp_" + FAKE + "1234",
    "github_pat_" + FAKE + "_" + FAKE,
    "glpat-" + FAKE[:22],
    "xoxb-1234567890-" + FAKE[:12],
    "AKIA" + "ABCDEFGHIJKLMNOP",
    "AIza" + FAKE + "abc",
    "sk-" + FAKE,
    "sk-ant-" + FAKE,
    "Authorization: Bearer " + FAKE,
    "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
    "password=Hunter2!xyz",
    "api_key: '" + FAKE + "'",
    "connect with postgres://jane:S3cretPass@db.example.com:5432/app",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJqYW5lIn0.c2lnbmF0dXJlLXZhbHVlLXg",
    "here: " + FAKE + "Zx9" + FAKE[:8],
]

NOT_SECRETS = [
    "cherry-pick 3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39 onto main",
    "image digest sha256:" + "a" * 32 + "0123456789abcdef0123456789abcdef",
    "integrity sha512-" + "Zm9vYmFyYmF6cXV4" * 5 + "==",
    "rename task-sk-rename-function-in-module please",
    "see src/components/forms/inputs/TextFieldWithValidation2/index.tsx",
    "uuid 123e4567-e89b-12d3-a456-426614174000",
    "the password: required for login",
    "set password=<your-password> in .env",
    "api_key=${API_KEY}",
    "postgres://user:<password>@localhost/db",
    "a-very-long-kebab-case-branch-name-for-the-new-checkout-flow",
    "",
    "just a normal question about pytest fixtures",
]


@pytest.mark.parametrize("text", SECRETS)
def test_detects_secret_shapes(text):
    assert cpa.looks_like_secret(text)


@pytest.mark.parametrize("text", NOT_SECRETS)
def test_ignores_non_secrets(text):
    assert not cpa.looks_like_secret(text)


def run(payload=None, raw=None):
    data = raw if raw is not None else json.dumps(payload).encode("utf-8")
    env = {k: v for k, v in os.environ.items() if k != "HOOKLIB_DEBUG"}
    return subprocess.run([sys.executable, str(HOOK)], input=data, capture_output=True, env=env, timeout=20)


def test_emits_user_prompt_submit_context_without_the_value():
    secret = "ghp_" + FAKE + "1234"
    proc = run({"prompt": "use " + secret})
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "UserPromptSubmit"
    assert "COMPROMISED" in out["additionalContext"]
    assert secret.encode() not in proc.stdout
    assert FAKE.encode() not in proc.stdout


def test_silent_on_sha():
    proc = run({"prompt": "revert 3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39"})
    assert proc.returncode == 0 and proc.stdout == b""


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"\xff\xfe\x81"])
def test_fails_open(raw):
    proc = run(raw=raw)
    assert proc.returncode == 0 and proc.stdout == b""
