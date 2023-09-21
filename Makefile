
SOURCE_FILES := src/lambda_function.py src/sbn_sis.py

.PHONY: deploy clean
default: sbn-sis.zip

src/python:
	python3.11 -m venv --prompt=sbn-sis-lambda src/python
	source src/python/bin/activate && pip install astropy requests

sbn-sis-dependencies.zip: src/python
	rm -f $@
	cd src && zip -r ../$@ python/lib/python3.11/site-packages

sbn-sis.zip: $(SOURCE_FILES)
	rm -f $@
	cd src && zip ../$@ $(patsubst src/%,%,$^)

# deploy: sbn-sis.zip
# 	aws lambda update-function-code \
# 		--function-name  sbn-sis \
# 		--zip-file fileb://sbn-sis.zip

clean:
	rm -f sbn-sis.zip sbn-sis-dependencies.zip
