# api-contract — spec validation and typed client generation.
# The OpenAPI spec (openapi.yaml) is the single source of truth.
# Requires: uv (Python tooling) and npx/node (TypeScript tooling).

SPEC := openapi.yaml
PY_OUT := clients/python/gym_api_client/models.py
TS_OUT := clients/typescript/schema.ts

.PHONY: all validate gen gen-python gen-typescript clean

all: validate gen

# Validate the spec against the OpenAPI 3.1 schema.
validate:
	uv run --quiet --with openapi-spec-validator --with pyyaml \
		python3 scripts/validate.py $(SPEC)

gen: gen-python gen-typescript

# Python models for the bot (pydantic v2), regenerated into the installable
# gym-api-client package. The async httpx wrapper (client.py) is hand-maintained
# on top of these models and is NOT regenerated.
gen-python:
	mkdir -p $(dir $(PY_OUT))
	uv run --quiet --with "datamodel-code-generator[http]" datamodel-codegen \
		--input $(SPEC) \
		--input-file-type openapi \
		--output $(PY_OUT) \
		--output-model-type pydantic_v2.BaseModel \
		--target-python-version 3.11 \
		--use-standard-collections \
		--output-datetime-class datetime \
		--use-union-operator

# TypeScript types for web/admin/miniapp.
gen-typescript:
	mkdir -p $(dir $(TS_OUT))
	npx --yes openapi-typescript@7 $(SPEC) -o $(TS_OUT)

clean:
	rm -f $(PY_OUT) $(TS_OUT)
