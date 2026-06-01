"""Validate an OpenAPI document against the OpenAPI 3.1 schema.

Usage:
    uv run --with openapi-spec-validator --with pyyaml python3 scripts/validate.py openapi.yaml
"""

import sys

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename


def main(path: str) -> int:
    spec, _ = read_from_filename(path)
    validate(spec)
    paths = len(spec.get("paths", {}))
    schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"OK: {path} is a valid OpenAPI 3.1 document "
          f"({paths} paths, {schemas} schemas)")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "openapi.yaml"
    raise SystemExit(main(target))
