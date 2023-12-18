"""Application information.
"""
import os

#  package constants
APPLICATION_NAME = "ukhsa-ingest2raw-s3copy"
APPLICATION_STAGE = "ingest2raw"
APPLICATION_VERSION = "1.3.2"
ENVIRONMENT_NAME = os.getenv("UKHSA_ENVIRONMENT") or "devp2"
