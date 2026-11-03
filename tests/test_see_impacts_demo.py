import contextlib
import copy
import io
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo/runner"))
import see_impacts_demo as demo


FIXTURES = ROOT / "payloads/see-impacts"
REFERENCE = json.loads((FIXTURES / "expected-integrated-lca.json").read_text())


class DemoApi:
    def __init__(self):
        self.calls = []
        self.stored = {}
        self.result = copy.deepcopy(REFERENCE)

    def __call__(self, base_url, path, payload=None, **kwargs):
        self.calls.append((path, payload, kwargs))
        if path.endswith("/schema"):
            return {"type": "object"}
        if path.endswith(":validate"):
            return {"passed": True, "results": [{"kind": "JsonSchema", "passed": True}]}
        if path == "/compute":
            if isinstance(payload["product_system"]["activity_references"], str):
                if kwargs.get("expected") != 422:
                    raise RuntimeError("The invalid request did not expect schema rejection")
                return {"detail": {"code": "MODEL_VALIDATION_FAILED"}}
            return copy.deepcopy(self.result)
        if path.endswith(":create"):
            parts = path.split("/")
            record = {
                "id": f"record-{len(self.stored)}", "model": parts[2],
                "version": parts[4].split(":")[0], "payload": copy.deepcopy(payload["payload"]),
            }
            self.stored[record["id"]] = record
            return copy.deepcopy(record)
        if path.endswith(":query"):
            record_id = payload["filter"]["where"][0]["value"]
            return {"records": [copy.deepcopy(self.stored[record_id])]}
        raise AssertionError(f"Unexpected API call: {path}")


class SeeDemoTests(unittest.TestCase):
    def run_scenario(self, mode, api):
        with patch.object(demo, "wait_ready"), patch.object(demo, "request_json", side_effect=api):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                demo.run(
                    mode, FIXTURES, ROOT / "compose/registry/catalog.json",
                    "http://core", "http://backend", "http://see", 1020,
                )
        return output.getvalue()

    def test_demo_computes_once_and_persists_all_three_record_types(self):
        api = DemoApi()
        output = self.run_scenario("demo", api)
        calculations = [call for call in api.calls if call[0] == "/compute" and call[2].get("expected", 200) == 200]
        self.assertEqual(len(calculations), 1)
        self.assertEqual(calculations[0][2]["timeout"], 1020)
        self.assertEqual(calculations[0][1]["model_versions"], {
            "product_system": "0.0.1", "lci_dataset": "0.0.1", "integrated_lca": "0.2.0",
        })
        self.assertEqual({record["model"] for record in api.stored.values()}, set(demo.MODELS))
        self.assertIn("All 25 indicators match", output)
        self.assertIn("Integrated LCA record ID:", output)
        self.assertEqual(sum(call[0].endswith(":query") for call in api.calls), 3)

    def test_validation_mode_never_runs_a_valid_calculation_or_stores_records(self):
        api = DemoApi()
        output = self.run_scenario("validate", api)
        calculations = [call for call in api.calls if call[0] == "/compute" and call[2].get("expected", 200) == 200]
        self.assertEqual(calculations, [])
        self.assertEqual(api.stored, {})
        self.assertIn("no calculation was run", output)
        validated = [call[0].split("/")[2] for call in api.calls if call[0].endswith(":validate")]
        self.assertEqual(validated, list(demo.MODELS))

    def test_reference_values_pass(self):
        self.assertEqual(len(demo.compare_results(copy.deepcopy(REFERENCE), REFERENCE)), 25)

    def test_readback_allows_only_floating_point_serialization_rounding(self):
        expected = {"flows": [{"value": 7.851902067493725e-08}]}
        actual = {"flows": [{"value": math.nextafter(expected["flows"][0]["value"], math.inf)}]}
        self.assertIsNone(demo.record_difference(expected, actual))

    def test_readback_rejects_small_flow_loss_and_material_changes(self):
        for expected, actual in ((1e-18, 0.0), (1.0, 1.00001), (True, 1), (10**18, 10**18 + 1)):
            with self.subTest(expected=expected, actual=actual):
                self.assertIsNotNone(demo.record_difference({"value": expected}, {"value": actual}))

    def test_readback_reports_the_changed_field_or_missing_structure(self):
        self.assertIn("$.flows[0].value", demo.record_difference(
            {"flows": [{"value": 1.0}]}, {"flows": [{"value": 2.0}]}
        ))
        self.assertIn("object fields differ", demo.record_difference({"value": 1}, {}))
        self.assertIn("array length differs", demo.record_difference([1], []))

    def test_missing_extra_duplicate_wrong_unit_value_or_method_is_rejected(self):
        for problem in ("missing", "extra", "duplicate", "unit", "value", "nan", "method"):
            with self.subTest(problem=problem):
                result = copy.deepcopy(REFERENCE)
                indicators = result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"]
                if problem == "missing":
                    indicators.pop()
                elif problem == "extra":
                    extra = copy.deepcopy(indicators[0])
                    extra["indicator_identifier"] = "unexpected indicator"
                    indicators.append(extra)
                elif problem == "duplicate":
                    indicators.append(copy.deepcopy(indicators[0]))
                elif problem == "unit":
                    indicators[0]["indicator_result"]["unit"] = "wrong unit"
                elif problem == "value":
                    indicators[0]["indicator_result"]["numeric_value"] *= 2
                elif problem == "nan":
                    indicators[0]["indicator_result"]["numeric_value"] = float("nan")
                else:
                    indicators[0]["method_version"] = "wrong method"
                with self.assertRaises(RuntimeError):
                    demo.compare_results(result, REFERENCE)

    def test_calculation_diagnostic_is_not_accepted_as_a_result(self):
        with self.assertRaisesRegex(RuntimeError, "No complete Integrated LCA result"):
            demo.compare_results({"status": "not_calculable", "diagnostic": {}}, REFERENCE)

    def test_validation_requires_a_passing_json_schema_report(self):
        for report in ({"passed": True, "results": []}, {"passed": False, "results": []},
                       {"passed": True, "results": [{"kind": "JsonSchema", "passed": False}]}):
            with self.subTest(report=report), patch.object(demo, "request_json", return_value=report):
                with self.assertRaisesRegex(RuntimeError, "did not pass HEX Core"):
                    demo.validate_record("http://core", "product-system", "0.0.1", {})

    def test_wrong_readback_payload_fails_the_demo(self):
        api = DemoApi()

        def wrong_readback(*args, **kwargs):
            response = api(*args, **kwargs)
            if args[1].endswith(":query"):
                response["records"][0]["payload"] = {}
            return response

        with self.assertRaisesRegex(RuntimeError, "read-back mismatch"):
            self.run_scenario("demo", wrong_readback)

    def test_wrong_calculation_result_is_not_stored(self):
        api = DemoApi()
        api.result["lca_analysis_instances"][0]["assessment_results"]["assessment_indicators"].pop()
        with self.assertRaisesRegex(RuntimeError, "indicator set differs"):
            self.run_scenario("demo", api)
        self.assertFalse(any(record["model"] == "integrated-lca" for record in api.stored.values()))

    def test_wrong_invalid_input_error_is_not_counted_as_schema_rejection(self):
        api = DemoApi()

        def wrong_rejection(*args, **kwargs):
            if args[1] == "/compute":
                return {"detail": {"code": "MODEL_VALIDATION_UNAVAILABLE"}}
            return api(*args, **kwargs)

        with self.assertRaisesRegex(RuntimeError, "not rejected by model validation"):
            self.run_scenario("validate", wrong_rejection)

    def test_unavailable_http_service_is_not_accepted_as_invalid_input(self):
        error = HTTPError("http://see/compute", 503, "Unavailable", {}, io.BytesIO(b'{}'))
        with patch.object(demo, "urlopen", side_effect=error):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                demo.request_json("http://see", "/compute", {}, expected=422)

    def test_network_failure_has_a_clear_error(self):
        with patch.object(demo, "urlopen", side_effect=URLError("connection refused")):
            with self.assertRaisesRegex(RuntimeError, "Could not reach POST /compute"):
                demo.request_json("http://see", "/compute", {})


if __name__ == "__main__":
    unittest.main()
