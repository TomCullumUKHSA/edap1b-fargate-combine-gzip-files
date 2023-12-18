"""Unit tests for loggingutil module.
"""

import ast
import io
import logging
import unittest

import loggingutil


class LoggingUtilTestCase(unittest.TestCase):
    """loggingutil module test case."""

    TARGET_OUTPUT_WITHOUT_LOCATION = {
        "APPLICATION_NAME": "TestApp",
        "APPLICATION_STAGE": "TestStage",
        "APPLICATION_VERSION": "0.0.0",
        "ENVIRONMENT_NAME": "test-env",
        "MESSAGE": "Test message",
        "SEVERITY": "INFO",
    }

    def setUp(self) -> None:
        self.stream = io.StringIO()
        loggingutil.setup_logging(
            application_name="TestApp",
            application_stage="TestStage",
            application_version="0.0.0",
            environment_name="test-env",
            stream=self.stream,
        )

    def test_extra_fields(self):
        """Test that extra fields get logged."""
        logging.info("Message", extra={"EXTRA_FIELD": "VALUE"})
        output_json: dict = ast.literal_eval(self.stream.getvalue())
        self.assertIn("EXTRA_FIELD", output_json)
        self.assertEqual(output_json["EXTRA_FIELD"], "VALUE")

    def test_main_logger_can_log_in_json_format(self):
        """Test that the main logger can log in json format."""
        logging.getLogger().info("Test message")

        output_json: dict = ast.literal_eval(self.stream.getvalue())
        # remove location since it will depend on local environemt (file path)
        location = output_json.pop("LOCATION")
        self.assertTrue("LINENO" in location)
        self.assertTrue(location["LINENO"] > 0)
        self.assertTrue("PATHNAME" in location)
        self.assertTrue(len(location["PATHNAME"]) > 0)
        self.assertEqual(
            output_json,
            self.TARGET_OUTPUT_WITHOUT_LOCATION,
        )

    def test_named_logger_can_log_in_json_format(self):
        """Test that a named logger can log in json format."""
        logging.getLogger("NAME").info("Test message")

        output_json: dict = ast.literal_eval(self.stream.getvalue())
        # remove location since it will depend on local environemt (file path)
        location = output_json.pop("LOCATION")
        self.assertTrue("LINENO" in location)
        self.assertTrue(location["LINENO"] > 0)
        self.assertTrue("PATHNAME" in location)
        self.assertTrue(len(location["PATHNAME"]) > 0)
        self.assertEqual(
            output_json,
            self.TARGET_OUTPUT_WITHOUT_LOCATION,
        )
