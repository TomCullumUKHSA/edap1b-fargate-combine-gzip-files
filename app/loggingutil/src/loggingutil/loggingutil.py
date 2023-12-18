"""Utility module to setup proper logging.
"""
import logging
from typing import Optional

from pythonjsonlogger import jsonlogger


# global variables needed for logging
_APPLICATION_NAME: Optional[str] = None
_APPLICATION_STAGE: Optional[str] = None
_APPLICATION_VERSION: Optional[str] = None
_ENVIRONMENT_NAME: Optional[str] = None


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """A custom formatter that meets detailed design requirements."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # move some fields to match UKHSA log format
        log_record["MESSAGE"] = log_record.pop("message", None)
        log_record["SEVERITY"] = log_record.pop("levelname", None)

        # add some common fields
        log_record["APPLICATION_NAME"] = _APPLICATION_NAME
        log_record["APPLICATION_STAGE"] = _APPLICATION_STAGE
        log_record["APPLICATION_VERSION"] = _APPLICATION_VERSION
        log_record["ENVIRONMENT_NAME"] = _ENVIRONMENT_NAME

        # log location
        log_record["LOCATION"] = {
            "PATHNAME": log_record.pop("pathname", None),
            "LINENO": log_record.pop("lineno", None),
        }


def setup_logging(
    application_name: str,
    application_stage: str,
    application_version: str,
    environment_name: str,
    stream=None,
) -> None:
    """ "Setup project logging parameters.

    Args:
        application_name (str): The application name.
        application_stage (str): Application stage (i.e.: "ingest2raw").
        application_version (str): Application version (i.e.: "1.0.0").
        environment_name (str): Environment name (i.e.: "dev").
        stream (optional): Stream to output logs to. Defaults to stderr.
    """

    global _APPLICATION_NAME, _APPLICATION_STAGE, _APPLICATION_VERSION, _ENVIRONMENT_NAME  # pylint: disable=global-statement

    _APPLICATION_NAME = application_name
    _APPLICATION_STAGE = application_stage
    _APPLICATION_VERSION = application_version
    _ENVIRONMENT_NAME = environment_name
    # logging.basicConfig(level="INFO")
    logger = logging.getLogger()
    log_handler = logging.StreamHandler(stream=stream)
    # add as many fields as need to be dumped
    log_handler.setFormatter(
        CustomJsonFormatter("%(pathname)s %(lineno)s %(levelname)s %(message)s")
    )
    # Set the handler with CustomJsonFormatter as the only handler
    logger.handlers.clear()
    logger.addHandler(log_handler)
    # Make sure we are logging info messages
    logger.setLevel("INFO")
