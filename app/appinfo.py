"""Application information.
"""
import os

#  package constants
APPLICATION_NAME = "ukhsa-combine-gzip-files"
APPLICATION_STAGE = "export"
APPLICATION_VERSION = "1.0.0"
ENVIRONMENT_NAME = os.getenv("UKHSA_ENVIRONMENT") or "devp2"
