DEV_SOURCE_FILES := src/local_lambda_run.py src/test_sbn_sis.py
SOURCE_FILES := $(filter-out $(DEV_SOURCE_FILES),$(wildcard src/*.py))
PYTHON := python3.12
DEPENDENICES := astropy fsspec requests aiohttp Pillow pytest s3fs

# create .env from a copy of env.template
include .env

.PHONY: test deploy clean env
default: sbn-sis.zip

# WARNING! You must run this on a linux!
src/python:
	${PYTHON} -m venv --prompt=sbn-sis-lambda src/python
	. src/python/bin/activate && pip install ${DEPENDENICES}

test-venv:
	${PYTHON} -m venv --prompt=sbn-sis-lambda-testing test-venv
	. test-venv/bin/activate && pip install ${DEPENDENICES}

sbn-sis-dependencies.zip: src/python
	rm -f $@
	cd src && zip -r ../$@ python/lib/${PYTHON}/site-packages --exclude python/lib/${PYTHON}/site-packages/pip\* --exclude python/lib/${PYTHON}/site-packages/setuptools\*

sbn-sis.zip: ${SOURCE_FILES}
	rm -f $@
	cd src && zip ../$@ $(patsubst src/%,%,$^)

test: test-venv
	. test-venv/bin/activate && pytest src/ -v --durations=0

deploy: .env sbn-sis.zip
	aws lambda update-function-code \
		--function-name ${LAMBDA_FUNCTION_NAME} \
		--zip-file fileb://sbn-sis.zip

update-env-vars:
	aws lambda update-function-configuration \
    --function-name ${LAMBDA_FUNCTION_NAME} \
    --environment Variables="{S3_CACHE_BUCKET_NAME=${S3_CACHE_BUCKET_NAME}}"

deploy-dependencies: env sbn-sis-dependencies.zip
	aws lambda publish-layer-version \
		--layer-name ${LAMBDA_DEPENDENCIES_LAYER} \
		--zip-file fileb://sbn-sis-dependencies.zip

clean:
	cd src && rm -rf python
	rm -f sbn-sis.zip sbn-sis-dependencies.zip
