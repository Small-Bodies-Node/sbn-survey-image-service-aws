
SOURCE_FILES := src/lambda_function.py src/sbn_sis.py

# create .env from a copy of env.template
include .env

.PHONY: test deploy clean env
default: sbn-sis.zip

src/python:
	python3.11 -m venv --prompt=sbn-sis-lambda src/python
	. src/python/bin/activate && pip install astropy requests Pillow

sbn-sis-dependencies.zip: src/python
	rm -f $@
	cd src && zip -r ../$@ python/lib/python3.11/site-packages --exclude python/lib/python3.11/site-packages/pip\* --exclude python/lib/python3.11/site-packages/setuptools\*

sbn-sis.zip: $(SOURCE_FILES)
	rm -f $@
	cd src && zip ../$@ $(patsubst src/%,%,$^)

test:
	pytest src/

deploy: .env sbn-sis.zip
	aws lambda update-function-code \
		--function-name $(LAMBDA_FUNCTION_NAME) \
		--zip-file fileb://sbn-sis.zip

deploy-dependencies: env sbn-sis-dependencies.zip
	aws lambda publish-layer-version \
		--layer-name $(LAMBDA_DEPENDENCIES_LAYER) \
		--zip-file fileb://sbn-sis-dependencies.zip

clean:
	cd src && rm -rf python
	rm -f sbn-sis.zip sbn-sis-dependencies.zip
