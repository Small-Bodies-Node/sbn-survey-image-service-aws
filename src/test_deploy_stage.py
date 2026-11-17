import base64
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

import deploy_stage as deployment


@pytest.fixture
def stage_repository(tmp_path):
    source = tmp_path / "src/lambda_function.py"
    source.parent.mkdir()
    source.write_text("# Current runtime source\n")
    with ZipFile(tmp_path / "sbn-sis.zip", "w") as archive:
        archive.write(source, "lambda_function.py")
    with ZipFile(tmp_path / "sbn-sis-dependencies.zip", "w") as archive:
        archive.writestr("python/pyavm/__init__.py", "# Dependency fixture\n")
    return tmp_path


def test_stage_release_preserves_other_layers_and_never_targets_production(
    stage_repository, monkeypatch, capsys
):
    other_before = "arn:aws:lambda:us-west-1:123456789012:layer:extension-before:1"
    other_after = "arn:aws:lambda:us-west-1:123456789012:layer:extension-after:2"
    layer_base = (
        "arn:aws:lambda:us-west-1:123456789012:layer:"
        "sbn-survey-image-service-dependencies-stage"
    )
    configuration = {
        "Name": deployment.STAGE_FUNCTION,
        "Runtime": "python3.12",
        "Architecture": "x86_64",
        "CachePrefix": "stage/",
        "Layers": [other_before, f"{layer_base}:1", other_after],
        "Revision": "before-release",
        "Hash": "previous-code",
    }
    calls = []
    # An inherited production deployment setting must not affect this helper.
    monkeypatch.setenv("LAMBDA_FUNCTION_NAME", "sbn-survey-image-service")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    def run(arguments, **kwargs):
        calls.append(arguments)
        assert arguments[arguments.index("--region") + 1] == "us-west-1"
        operation = arguments[arguments.index("lambda") + 1]
        if "--function-name" in arguments:
            assert (
                arguments[arguments.index("--function-name") + 1]
                == deployment.STAGE_FUNCTION
            )
        if operation == "publish-layer-version":
            assert arguments[arguments.index("--layer-name") + 1] == (
                deployment.STAGE_LAYER
            )
            response = {"LayerVersionArn": f"{layer_base}:2"}
        elif operation == "update-function-configuration":
            assert arguments[arguments.index("--revision-id") + 1] == ("before-release")
            assert arguments[arguments.index("--layers") + 1 :] == [
                other_before,
                f"{layer_base}:2",
                other_after,
            ]
            configuration["Revision"] = "after-layer"
            response = {}
        elif operation == "update-function-code":
            assert arguments[arguments.index("--revision-id") + 1] == "after-layer"
            configuration["Hash"] = base64.b64encode(
                hashlib.sha256((stage_repository / "sbn-sis.zip").read_bytes()).digest()
            ).decode()
            response = {}
        elif operation == "get-function-configuration":
            response = configuration
        else:
            assert operation == "wait"
            response = None
        return subprocess.CompletedProcess(
            arguments, 0, json.dumps(response) if response else "", ""
        )

    monkeypatch.setattr(deployment.subprocess, "run", run)
    deployment.deploy_stage(stage_repository)

    operations = [arguments[arguments.index("lambda") + 1] for arguments in calls]
    assert operations.count("wait") == 3
    assert operations.count("publish-layer-version") == 1
    assert operations.count("update-function-code") == 1
    assert deployment.STAGE_FUNCTION in capsys.readouterr().out


@pytest.mark.parametrize(
    "field,value",
    [
        ("Name", "sbn-survey-image-service"),
        ("CachePrefix", ""),
        ("Architecture", "arm64"),
        ("Runtime", "python3.11"),
    ],
)
def test_incompatible_stage_configuration_is_rejected_before_any_write(
    stage_repository, monkeypatch, field, value
):
    configuration = {
        "Name": deployment.STAGE_FUNCTION,
        "Runtime": "python3.12",
        "Architecture": "x86_64",
        "CachePrefix": "stage/",
    }
    configuration[field] = value

    def run(arguments, **kwargs):
        operation = arguments[arguments.index("lambda") + 1]
        assert operation in ("wait", "get-function-configuration")
        return subprocess.CompletedProcess(
            arguments, 0, json.dumps(configuration) if operation != "wait" else "", ""
        )

    monkeypatch.setattr(deployment.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="Stage must use"):
        deployment.deploy_stage(stage_repository)


def test_stale_application_is_rejected_before_contacting_aws(
    stage_repository, monkeypatch
):
    (stage_repository / "src/lambda_function.py").write_text("# Changed runtime\n")
    monkeypatch.setattr(
        deployment.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("AWS must not be called for a stale ZIP"),
    )
    with pytest.raises(RuntimeError, match="stale"):
        deployment.deploy_stage(stage_repository)


def test_stale_scientific_module_is_rejected_before_contacting_aws(
    stage_repository, monkeypatch
):
    source = stage_repository / "src/north_up_preview.py"
    source.write_text("# Previous renderer\n")
    with ZipFile(stage_repository / "sbn-sis.zip", "a") as archive:
        archive.write(source, source.name)
    source.write_text("# Updated renderer\n")
    monkeypatch.setattr(
        deployment.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("AWS must not be called for a stale ZIP"),
    )
    with pytest.raises(RuntimeError, match="stale"):
        deployment.deploy_stage(stage_repository)


def test_aws_failure_stops_before_uploading_code(stage_repository, monkeypatch):
    def run(arguments, **kwargs):
        assert arguments[arguments.index("lambda") + 1] == "wait"
        return subprocess.CompletedProcess(arguments, 255, "", "Stage update failed")

    monkeypatch.setattr(deployment.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="Stage update failed"):
        deployment.deploy_stage(stage_repository)


def test_wrapper_uses_repository_credentials_and_disables_profiles(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    wrapper = repository / "_deploy_stage"
    shutil.copy2(
        Path(deployment.__file__).resolve().parent.parent / "_deploy_stage",
        wrapper,
    )
    (repository / ".env").write_text(
        "AWS_ACCESS_KEY_ID=fixture-access\nAWS_SECRET_ACCESS_KEY=fixture-secret\n"
    )
    commands = tmp_path / "commands"
    commands.mkdir()
    python = commands / "python3"
    python.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        '[[ "$AWS_ACCESS_KEY_ID" == fixture-access ]]\n'
        '[[ "$AWS_SECRET_ACCESS_KEY" == fixture-secret ]]\n'
        '[[ -z "${AWS_SESSION_TOKEN:-}" ]]\n'
        '[[ -z "${AWS_PROFILE:-}" ]]\n'
        '[[ "$AWS_CONFIG_FILE" == /dev/null ]]\n'
        '[[ "$AWS_SHARED_CREDENTIALS_FILE" == /dev/null ]]\n'
    )
    python.chmod(0o755)
    environment = dict(os.environ)
    environment.update(
        PATH=f"{commands}:{environment['PATH']}",
        AWS_ACCESS_KEY_ID="inherited-access",
        AWS_SECRET_ACCESS_KEY="inherited-secret",
        AWS_SESSION_TOKEN="inherited-token",
        AWS_PROFILE="unwanted-profile",
    )

    result = subprocess.run(
        [str(wrapper)], env=environment, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
