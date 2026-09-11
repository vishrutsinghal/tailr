from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from scripts import token_telemetry


class HostTokenTelemetryTests(unittest.TestCase):
    def test_records_exact_host_api_usage_as_one_run_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "response.json"
            output = root / "token-usage.jsonl"
            source.write_text(json.dumps({
                "id": "response-1",
                "usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
            }, indent=2), encoding="utf-8")
            result = token_telemetry.record_host(argparse.Namespace(
                task_id="start-1",
                variant="tailtrail",
                provider="openai",
                model="gpt-test",
                source=source.as_posix(),
                stage_id="implementation",
                timestamp=None,
                output=output.as_posix(),
                dry_run=False,
            ))

            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual("host_usage", result["mode"])
        self.assertEqual("tailtrail", saved["variant"])
        self.assertEqual(150, saved["usage"]["total_tokens"])
        self.assertEqual(120, saved["usage"]["input_tokens"])
        self.assertEqual(30, saved["usage"]["output_tokens"])
        self.assertEqual("implementation", saved["stage_id"])
        self.assertEqual("host_api_usage", saved["source"])

    def test_rejects_source_without_api_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "response.json"
            source.write_text('{"id":"response-without-usage"}', encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "No host/model API usage metadata"):
                token_telemetry.record_host(argparse.Namespace(
                    task_id="start-1",
                    variant="tailtrail",
                    provider="openai",
                    model="gpt-test",
                    source=source.as_posix(),
                    stage_id=None,
                    timestamp=None,
                    output=(root / "token-usage.jsonl").as_posix(),
                    dry_run=False,
                ))


if __name__ == "__main__":
    unittest.main()
