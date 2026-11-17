# SBN Survey Image Service AWS

## What's This?

This is a lambda function with S3-caching to retrieve FITS and JPEG images.  The function is intended to be served by AWS's Gateway API.  URLs requesting data take the following format:

```
https://HOST/api/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:703_20220122_2b_n32022_01_0003.arch?ra=107.10813&dec=30.84928&size=5arcmin&format=jpeg
```

It is used by [CATCH](https://catch.astro.umd.edu) and other services maintained by [SBN](https://pds-smallbodies.astro.umd.edu/) at [UMD](https://www.astro.umd.edu/).

## Overview

The AWS Lambda function:

1. Receives path and query parameters.
2. Formulate a unique file name based on the query.
3. Checks if a corresponding file exists within a data cache backed by an S3 bucket.
4. If the file exists, it is returned to the user.
5. If the file does not exist, then the data is retrieved from externally hosted services.
6. Images are converted to the user's requested format (e.g., JPEG or PNG).
7. The result is cached to S3 and returned to the user.

Catalina Sky Survey, NEAT, and Spacewatch data archived at `sbnarchive.psi.edu` are presently supported.

Requests from this service will have a User-Agent of "SBN Survey Image Service AWS {version}"

## North-up browse rendering

JPEG/PNG requests with both `align=true` and `renderer=north-up-v1` derive a
centered ICRS TAN view with north up and east left, retaining native
dimensions/scales and embedding the actual output WCS as AVM. Reprojection
uses 128-row tiles through the complete native WCS to limit Lambda memory.

The renderer parameter is an explicit opt-in used by the updated GUI. Requests
without that exact renderer version keep their existing rendering and cache
filenames, including older clients that already send `align=true`. Legacy
requests continue to ignore the alignment parameter. Opted-in browse requests
use `north-up-v1` cache names and sorted request parameters. For that version,
`align` must be `true` or `false`; omitting it defaults to `false`.

Scientific FITS requests retain their native pixels, legacy cache filename
algorithm, and deployed `Content-Type: image/fits`, even when renderer/alignment
parameters are present. This rollout does not require changing API Gateway's
FITS media type configuration.

Rebuild and attach the dependency layer containing `pyavm` before deploying the
new Lambda code. Adding it to the Makefile does not update an already attached
layer. Existing pre-alignment CloudFront filenames are bypassed by the updated
GUI; regenerated previews populate new cache keys. Deploy this service before
the GUI. See the GUI README for the complete rollout sequence.

Focused renderer/cache checks:

```bash
PYTHONPATH=src python -m pytest src/test_orientation.py
```

## Development notes

Create `.env` from `env.template` before deploying. Building does not require `.env` or AWS credentials.

### Stage deployment

Stage uses function `sbn-survey-image-service-stage` and dependency layer `sbn-survey-image-service-dependencies-stage` in `us-west-1`, with Python 3.12, x86_64, 2048 MiB memory, a 10-second timeout, and `S3_CACHE_KEY_PREFIX=stage/`. These runtime settings were copied from production during initial creation. The empty default cache prefix retains production's existing keys. Stage uses the existing cache bucket with separate object keys.

Initial creation is a one-time AWS CLI operator task: read production's configuration, create the stage function with its relevant runtime settings and existing execution role, preserve other attached layers, and replace the image-service dependency layer with the stage layer. No production function, API integration, or IAM policy is updated. Inspect the actual AWS configuration with `aws lambda get-function-configuration --function-name sbn-survey-image-service-stage --region us-west-1` after sourcing this repository's `.env`.

For subsequent stage releases, with AWS CLI installed and valid credentials in this repository's `.env`:

```bash
./_build x86_64
make deploy-stage
```

The stage wrapper sources `.env` in its own process and disables AWS profile-file lookup. The stage target publishes and attaches its own dependency layer, preserves other layers and their order, uploads the application ZIP, waits for updates, and checks the deployed code hash. It requires Python 3 on the deployment machine and always targets the named stage function. The existing production targets are separate.

Stage is invoked directly using AWS CLI; it has no public API endpoint. Publishing or testing stage does not switch production traffic. Inspect Lambda invocation results for `FunctionError` and the returned application's `statusCode`, since a successful CLI invocation alone does not establish a successful image request.

Live stage validation passed for Catalina and Spacewatch FITS, legacy JPEG, north-up JPEG/PNG with embedded WCS, and repeated cache hits. A NEAT sample exposed an existing AWS cutout-reader issue: its image and WCS are in extension 1, whereas the AWS reader selects the primary HDU. NEAT detector pixel-size keywords also require the WCS handling already present in the NON-aws service. The deployed production cutout implementation was verified to be identical; this needs a separate scientific-reader fix before relying on fresh NEAT cutouts from AWS.

### Deploying a new version

Start Docker Desktop or Colima, then check the function's architecture in the Lambda console. From this repository, build with the matching command:

```bash
./_build x86_64
# For an ARM64 Lambda, use ./_build arm64 instead.
```

Docker builds in the AWS Python 3.12 environment, checks that the handler imports, and writes `sbn-sis.zip` and `sbn-sis-dependencies.zip` into this directory. Your machine's Python version and CPU architecture do not determine the build. You need Docker with BuildKit and support for the selected platform; Docker Desktop provides this, while a Colima setup may need emulation when building for another architecture. No host Python installation is required for this workflow.

The dependency ZIP excludes generated Python bytecode (`__pycache__`, `.pyc`, and `.pyo`) to keep the direct upload small. Python source files, package data, and native libraries are included.

On Windows, use Bash for `_build`, or run `docker build --platform linux/amd64 --target artifacts --output . .` directly in this directory. Use `linux/arm64` for an ARM64 Lambda.

From your host terminal with the AWS CLI configured, publish the dependency layer:

```bash
make deploy-dependencies
```

Attach the returned `LayerVersionArn` to the Lambda function, preserving any other attached layers, and wait for the configuration update to finish. Publishing a layer does not attach it. Then upload the application code:

```bash
make deploy
```

These deployment targets upload the existing ZIPs without rebuilding them. Run `_build` again after changing code or dependencies. `make deploy` updates `$LATEST`; if production uses an alias pointing to a published version, publish a new version and update that alias too.

The User-Agent includes a version derived from Git tags and the checkout state using setuptools_scm inside Docker. For a tagged production release, tag the intended commit with `git tag vX.Y.Z` before building.

To update the github repository with the deployed version:
1. `git push`
2. `git push --tags`

To verify that the version is correctly set, test the function on the AWS console.  The result should include the version in the header under "User-Agent":

```json
{
  "headers": {
    "Content-Type": "image/fits",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "User-Agent": "SBN Survey Image Service AWS 1.0.1"
  }
}
```

### Testing

Unit tests are in the src/test_sbn_sis.py file.  They are designed to be run with `pytest src/`.  The tests can also be run with the Makefile, which will setup a virtual environment in the `test-venv` directory:

```bash
make test
```

### Misc

Test Lambda function:

```json
{
  "queryStringParameters": {
    "lid": "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch",
    "ra": 190.99166667,
    "dec": 23.92305556,
    "size": "5 arcmin",
    "format": "jpeg"
  }
}
```

Test API Gateway query string:

```
/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch?ra=190.99166667&dec=23.92305556&size=5arcmin&format=jpeg
```

Test API Gateway method:

lid: urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch
Query strings: ra=190.99166667&dec=23.92305556&size=5arcmin
