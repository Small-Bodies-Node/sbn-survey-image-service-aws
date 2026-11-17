import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from zipfile import ZipFile

STAGE_FUNCTION = "sbn-survey-image-service-stage"
STAGE_LAYER = "sbn-survey-image-service-dependencies-stage"
STAGE_REGION = "us-west-1"


def deploy_stage(repository: Path | None = None) -> None:
    """Deploy existing ZIPs to stage using AWS CLI; never target production.

    Initial creation is a one-time operator task documented in the README.
    This function handles subsequent releases and keeps other attached layers.
    """
    repository = repository or Path(__file__).resolve().parent.parent
    code_zip = repository / "sbn-sis.zip"
    layer_zip = repository / "sbn-sis-dependencies.zip"
    for archive in (code_zip, layer_zip):
        if not archive.is_file():
            raise RuntimeError("Build both ZIPs first with ./_build x86_64.")
        if archive.stat().st_size > 50 * 1024**2:
            raise RuntimeError(f"{archive.name} exceeds the direct-upload limit.")
    with ZipFile(code_zip) as archive:
        for filename in archive.namelist():
            # Git regenerates version metadata inside the Docker build.
            if filename.endswith(".py") and filename != "_version.py":
                if (
                    archive.read(filename)
                    != (repository / "src" / filename).read_bytes()
                ):
                    raise RuntimeError(
                        "The application ZIP is stale; rebuild before deploying."
                    )

    def aws(operation: str, *arguments: str) -> dict[str, Any]:
        result = subprocess.run(
            [
                "aws",
                "--region",
                STAGE_REGION,
                "--no-cli-pager",
                "--output",
                "json",
                "lambda",
                operation,
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "AWS CLI operation failed.")
        return json.loads(result.stdout) if result.stdout.strip() else {}

    # Fetch only deployment fields; do not print environment secrets.
    query = (
        "{Name:FunctionName,Runtime:Runtime,Architecture:Architectures[0],"
        "Layers:Layers[].Arn,Revision:RevisionId,Hash:CodeSha256,"
        "CachePrefix:Environment.Variables.S3_CACHE_KEY_PREFIX}"
    )
    target = ("--function-name", STAGE_FUNCTION)
    aws("wait", "function-updated", *target)
    configuration = aws("get-function-configuration", *target, "--query", query)
    if (
        configuration["Name"] != STAGE_FUNCTION
        or configuration["Runtime"] != "python3.12"
        or configuration["Architecture"] != "x86_64"
        or configuration.get("CachePrefix") != "stage/"
    ):
        raise RuntimeError(
            "Stage must use Python 3.12, x86_64, and cache prefix stage/."
        )
    published = aws(
        "publish-layer-version",
        "--layer-name",
        STAGE_LAYER,
        "--zip-file",
        f"fileb://{layer_zip}",
        "--compatible-runtimes",
        "python3.12",
        "--compatible-architectures",
        "x86_64",
    )
    new_layer = published["LayerVersionArn"]
    # Replace our layer in place to preserve the merge order of other layers.
    layers = [
        new_layer if f":layer:{STAGE_LAYER}:" in arn else arn
        for arn in configuration.get("Layers") or []
    ]
    if new_layer not in layers:
        layers.append(new_layer)
    aws(
        "update-function-configuration",
        *target,
        "--revision-id",
        configuration["Revision"],
        "--layers",
        *layers,
    )
    aws("wait", "function-updated", *target)
    configuration = aws("get-function-configuration", *target, "--query", query)
    aws(
        "update-function-code",
        *target,
        "--revision-id",
        configuration["Revision"],
        "--zip-file",
        f"fileb://{code_zip}",
    )
    aws("wait", "function-updated", *target)
    configuration = aws("get-function-configuration", *target, "--query", query)
    expected_hash = base64.b64encode(hashlib.sha256(code_zip.read_bytes()).digest())
    if configuration["Hash"] != expected_hash.decode():
        raise RuntimeError("Stage's deployed code hash does not match the local ZIP.")
    print(f"Deployed {STAGE_FUNCTION} in {STAGE_REGION}.")
    print(f"Dependency layer: {new_layer}")


if __name__ == "__main__":
    try:
        deploy_stage()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        sys.exit(str(error))
