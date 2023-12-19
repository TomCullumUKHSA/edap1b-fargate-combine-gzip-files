"""Unit tests for BaseAPI class.
"""

import random
import unittest

import boto3
from moto import mock_s3

# from app.app import (
#     SubstitutionInfo,
#     check_if_file_to_file_copy,
#     get_target_filename_from_src_key,
#     path_to_dict,
# )


@mock_s3
class S3CopyTestCase(unittest.TestCase):
    """Unit tests for S3 copy."""

    def setUp(self) -> None:
        self.bucket_name = f"unit-testing-bucket-{random.randrange(0, 10000)}"
        self.s3_client = boto3.client("s3")
        self.s3_client.create_bucket(
            Bucket=self.bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

    def tearDown(self) -> None:
        boto3.resource("s3").Bucket(self.bucket_name).objects.delete()
        self.s3_client.delete_bucket(Bucket=self.bucket_name)


if __name__ == "__main__":
    unittest.main()
