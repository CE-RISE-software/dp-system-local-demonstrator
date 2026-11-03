"""Run the PV scenario against the published services in the local demo stack."""

import argparse
import copy
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


MODELS = ("product-system", "lci-dataset", "integrated-lca")


def step(title):
    print(f"\n== {title} ==", flush=True)


def request_json(base_url, path, payload=None, *, expected=200, timeout=30, headers=None, quiet=False):
    method = "GET" if payload is None else "POST"
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    request = Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status, content = response.status, response.read()
    except HTTPError as error:
        status, content = error.code, error.read()
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach {method} {path}: {error}") from error
    if not quiet:
        print(f"{method} {path}: HTTP {status}", flush=True)
    if status != expected:
        raise RuntimeError(
            f"{method} {path} returned HTTP {status}, expected {expected}: "
            + content.decode(errors="replace")[:4000]
        )
    try:
        return json.loads(content)
    except (ValueError, UnicodeError) as error:
        raise RuntimeError(f"{method} {path} did not return valid JSON") from error


def wait_ready(base_url, path, timeout=180):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return request_json(base_url, path, quiet=True, timeout=20)
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


def validate_record(core_url, model, version, record):
    report = request_json(
        core_url, f"/models/{model}/versions/{version}:validate", {"payload": record}
    )
    results = report.get("results", []) if isinstance(report, dict) else []
    if (
        not isinstance(report, dict)
        or report.get("passed") is not True
        or not isinstance(results, list)
        or not any(isinstance(item, dict) and item.get("kind") == "JsonSchema" for item in results)
        or not all(isinstance(item, dict) and item.get("passed") is True for item in results)
    ):
        raise RuntimeError(f"{model} {version} did not pass HEX Core schema validation: {report}")


def indicator_map(result):
    try:
        instances = result["lca_analysis_instances"]
        if len(instances) != 1:
            raise ValueError("expected one analysis instance")
        indicators = instances[0]["assessment_results"]["assessment_indicators"]
        indexed = {item["indicator_identifier"]: item for item in indicators}
        if not indexed or len(indexed) != len(indicators):
            raise ValueError("empty or duplicate indicators")
        return indexed
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"No complete Integrated LCA result was returned: {result}") from error


def compare_results(result, expected):
    actual = indicator_map(result)
    reference = indicator_map(expected)
    if set(actual) != set(reference):
        raise RuntimeError("The calculated indicator set differs from the published reference")
    for identifier, item in actual.items():
        target = reference[identifier]
        for field in (
            "assessment_dimension", "assessment_method", "method_version",
            "calculation_model_or_factor_set_reference",
        ):
            if item.get(field) != target.get(field):
                raise RuntimeError(f"{identifier}: {field} differs from the reference")
        value = item["indicator_result"]["numeric_value"]
        expected_value = target["indicator_result"]["numeric_value"]
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not math.isclose(value, expected_value, rel_tol=1e-7, abs_tol=1e-12)
            or item["indicator_result"]["unit"] != target["indicator_result"]["unit"]
        ):
            raise RuntimeError(f"{identifier}: result or unit differs from the published reference")
    return actual


def record_difference(expected, actual, path="$"):
    if type(expected) in (int, float) and type(actual) in (int, float):
        # JSON round trips can change the final floating-point digits.
        if type(expected) is int and type(actual) is int:
            if expected == actual:
                return None
        elif math.isfinite(expected) and math.isfinite(actual) and math.isclose(
            expected, actual, rel_tol=1e-14, abs_tol=0.0
        ):
            return None
    elif not isinstance(expected, (dict, list)) and type(expected) is type(actual) and expected == actual:
        return None
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            return f"{path}: object fields differ"
        for key in expected:
            difference = record_difference(expected[key], actual[key], f"{path}.{key}")
            if difference:
                return difference
        return None
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return f"{path}: array length differs"
        for index, (left, right) in enumerate(zip(expected, actual)):
            difference = record_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
        return None
    return f"{path}: expected {str(expected)[:160]!r}, read back {str(actual)[:160]!r}"


def persist_and_read(core_url, model, version, record):
    created = request_json(
        core_url, f"/models/{model}/versions/{version}:create", {"payload": record},
        headers={"Idempotency-Key": f"demo-see-{uuid4()}"},
    )
    record_id = created.get("id") if isinstance(created, dict) else None
    if (
        not isinstance(record_id, str) or not record_id
        or created.get("model") != model or created.get("version") != version
    ):
        raise RuntimeError(f"HEX Core did not return the expected stored {model} record")
    query = request_json(
        core_url, f"/models/{model}/versions/{version}:query",
        {"filter": {"where": [{"field": "id", "op": "eq", "value": record_id}], "limit": 1, "offset": 0}},
    )
    records = query.get("records", []) if isinstance(query, dict) else []
    if len(records) != 1 or records[0].get("id") != record_id:
        raise RuntimeError(f"Stored {model} record did not match its read-back payload")
    difference = record_difference(record, records[0].get("payload"))
    if difference:
        raise RuntimeError(f"Stored {model} read-back mismatch at {difference}")
    print(f"Stored and read back {model}: {record_id}", flush=True)
    return record_id


def run(mode, payload_dir, catalog_path, core_url, backend_url, see_url, calculation_timeout):
    catalog = json.loads(catalog_path.read_text())
    versions = {entry["model"]: entry["version"] for entry in catalog["models"]}
    for model in MODELS:
        if not versions.get(model):
            raise RuntimeError(f"The registry catalog is missing {model}")
    system = json.loads((payload_dir / "product-system.json").read_text())
    inventory = json.loads((payload_dir / "lci-dataset.json").read_text())
    reference = json.loads((payload_dir / "expected-integrated-lca.json").read_text())
    flow = system["reference_flow_specification"]
    request = {
        "model_versions": {
            "product_system": versions["product-system"],
            "lci_dataset": versions["lci-dataset"],
            "integrated_lca": versions["integrated-lca"],
        },
        "product_system": system,
        "lci_datasets": [inventory],
        "functional_unit": {
            "reference_flow_identifier": flow["reference_flow_identifier"],
            "quantity": 1.0,
            "unit": flow["reference_flow_unit_reference"],
        },
    }

    step("Step 1: Wait for core, backend, and SEE")
    wait_ready(core_url, "/admin/ready")
    wait_ready(backend_url, "/health")
    wait_ready(see_url, "/capabilities")
    print("Core, backend, and SEE are ready.", flush=True)

    step("Step 2: Validate the published PV inputs through HEX Core")
    for model, record in (("product-system", system), ("lci-dataset", inventory)):
        schema = request_json(core_url, f"/models/{model}/versions/{versions[model]}/schema")
        if not isinstance(schema, dict) or not schema:
            raise RuntimeError(f"HEX Core did not return the {model} schema")
        validate_record(core_url, model, versions[model], record)

    step("Step 3: Reject a non-conforming input before calculation")
    invalid = copy.deepcopy(request)
    invalid["product_system"]["activity_references"] = "invalid"
    rejected = request_json(see_url, "/compute", invalid, expected=422)
    detail = rejected.get("detail") if isinstance(rejected, dict) else None
    if not isinstance(detail, dict) or detail.get("code") != "MODEL_VALIDATION_FAILED":
        raise RuntimeError(f"The invalid record was not rejected by model validation: {rejected}")
    print("Non-conforming Product System rejected by HEX Core validation.", flush=True)

    if mode == "validate":
        step("Step 4: Validate the saved reference output")
        validate_record(core_url, "integrated-lca", versions["integrated-lca"], reference)
        print("SEE readiness and record validation passed; no calculation was run.", flush=True)
        return

    step("Step 4: Persist and read back the validated input records")
    for model, record in (("product-system", system), ("lci-dataset", inventory)):
        persist_and_read(core_url, model, versions[model], record)

    step("Step 5: Calculate the PV impacts in one request")
    result = request_json(see_url, "/compute", request, timeout=calculation_timeout)

    step("Step 6: Compare every indicator with the published reference")
    indicators = compare_results(result, reference)
    print("Indicator\tValue\tUnit", flush=True)
    for identifier, indicator in indicators.items():
        value = indicator["indicator_result"]
        print(f"{identifier}\t{value['numeric_value']:.12g}\t{value['unit']}", flush=True)
    print(f"All {len(indicators)} indicators match the published reference.", flush=True)

    step("Step 7: Validate, persist, and read back the complete result")
    validate_record(core_url, "integrated-lca", versions["integrated-lca"], result)
    record_id = persist_and_read(core_url, "integrated-lca", versions["integrated-lca"], result)

    step("Success Summary")
    print(f"Calculated {len(indicators)} indicators for 1 {flow['reference_flow_unit_reference']}.")
    print(f"Integrated LCA record ID: {record_id}")
    print("Input validation, numerical comparison, output validation, and persistence passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("demo", "validate"))
    args = parser.parse_args()
    try:
        timeout = int(os.environ.get("SEE_REQUEST_TIMEOUT_SECS", "1020"))
        if timeout <= 0:
            raise ValueError("DEMO_SEE_TIMEOUT_SECS must be positive")
        run(
            args.mode, Path("/payloads/see-impacts"), Path("/config/registry/catalog.json"),
            os.environ.get("DEMO_BASE_URL", "http://hex-core-service:8080"),
            os.environ.get("DEMO_BACKEND_URL", "http://dp-storage-jsondb-service:8080"),
            os.environ.get("SEE_BASE_URL", "http://see-impacts-calculation-service:8080"),
            timeout,
        )
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"SEE demonstration failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
