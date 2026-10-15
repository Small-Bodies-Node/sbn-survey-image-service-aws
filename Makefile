.DEFAULT_GOAL := default

DEV_SOURCE_FILES := src/local_lambda_run.py src/deploy_stage.py $(wildcard src/test_*.py)
SOURCE_FILES := $(filter-out $(DEV_SOURCE_FILES),$(wildcard src/*.py))
PYTHON := python3.12
BUILD_PYTHON ?= python3
# Host-specific paths allow a Mac and a Linux container to share the checkout.
BUILD_VENV := .build-venv/$(shell uname -s)-$(shell uname -m)
DEPENDENCIES := astropy fsspec requests aiohttp Pillow pyavm
TEST_DEPENDENCIES := pytest

# Deployment settings are unnecessary when building or testing.
ifneq ($(filter deploy deploy-dependencies update-env-vars,$(MAKECMDGOALS)),)
# Create .env from a copy of env.template before deploying.
include .env
endif

.PHONY: default test deploy deploy-stage deploy-dependencies update-env-vars clean FORCE
FORCE:
default: sbn-sis.zip sbn-sis-dependencies.zip

# Native Lambda dependencies must be built on Linux for its architecture.
src/python:
	@test "$$(uname -s)" = Linux || { \
		echo "Build the dependency layer on Linux with Python 3.12 and the Lambda's CPU architecture." >&2; \
		echo "On macOS, make sbn-sis.zip can build the application ZIP only." >&2; \
		exit 1; \
	}
	${PYTHON} -m venv --prompt=sbn-sis-lambda src/python
	. src/python/bin/activate && pip install ${DEPENDENCIES}

# A success marker lets a failed installation retry on the next make run.
${BUILD_VENV}/.ready: Makefile
	${BUILD_PYTHON} -m venv --prompt=sbn-sis-build ${BUILD_VENV}
	${BUILD_VENV}/bin/python -m pip install setuptools_scm
	touch $@

src/_version.py: FORCE ${BUILD_VENV}/.ready
	${BUILD_VENV}/bin/python -m setuptools_scm -f json --force-write-version-files

test-venv:
	${PYTHON} -m venv --prompt=sbn-sis-lambda-testing test-venv
	. test-venv/bin/activate && pip install ${DEPENDENCIES} ${TEST_DEPENDENCIES}

sbn-sis-dependencies.zip: src/python src/_version.py
	rm -f $@
	cd src && zip -r ../$@ python/lib/${PYTHON}/site-packages \
		--exclude python/lib/${PYTHON}/site-packages/pip\* \
		--exclude python/lib/${PYTHON}/site-packages/setuptools\* \
		--exclude '*/__pycache__/*' '*.pyc' '*.pyo'

# Generate the version module before packaging, even on a fresh checkout.
sbn-sis.zip: src/_version.py ${SOURCE_FILES}
	rm -f $@
	cd src && zip ../$@ $(patsubst src/%,%,$^)

test: test-venv
	. test-venv/bin/activate && pytest src/ -v --durations=0

# Upload the Docker-built files without rebuilding them on the host.
deploy-stage:
	./_deploy_stage

deploy: .env
	@test -f sbn-sis.zip || { echo "Run ./_build x86_64 (or arm64) first." >&2; exit 1; }
	aws lambda update-function-code \
		--function-name ${LAMBDA_FUNCTION_NAME} \
		--zip-file fileb://sbn-sis.zip

update-env-vars:
	aws lambda update-function-configuration \
    --function-name ${LAMBDA_FUNCTION_NAME} \
    --environment Variables="{S3_CACHE_BUCKET_NAME=${S3_CACHE_BUCKET_NAME},S3_CSS_DATE_LIMIT=${S3_CSS_DATE_LIMIT}}"

deploy-dependencies: .env
	@test -f sbn-sis-dependencies.zip || { echo "Run ./_build x86_64 (or arm64) first." >&2; exit 1; }
	aws lambda publish-layer-version \
		--layer-name ${LAMBDA_DEPENDENCIES_LAYER} \
		--zip-file fileb://sbn-sis-dependencies.zip

clean:
	cd src && rm -rf python
	rm -f sbn-sis.zip sbn-sis-dependencies.zip
