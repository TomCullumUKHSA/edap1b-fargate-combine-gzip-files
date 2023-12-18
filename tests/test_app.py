"""Unit tests for BaseAPI class.
"""

import random
import unittest

import boto3
from moto import mock_s3

from app.app import (
    SubstitutionInfo,
    check_if_file_to_file_copy,
    get_target_filename_from_src_key,
    path_to_dict,
)


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

    def test_check_if_file_to_file_copy(self):
        """Test function `check_if_file_to_file_copy()`."""
        for message, source, dest, should_raise, result in [
            ("Dir to file should throw", "dir1/", "dir2/file.txt", True, None),
            ("Dir with dot to dir", "dir1.csv/", "dir2/", False, False),
            ("Dir to dir with dot", "dir1/", "dir2.csv/", False, False),
            ("Dir with dot to dir with dot", "dir1.csv/", "dir2.csv/", False, False),
        ]:
            with self.subTest(message):
                if should_raise:
                    self.assertRaises(
                        RuntimeError, check_if_file_to_file_copy, source, dest
                    )
                else:
                    self.assertEqual(check_if_file_to_file_copy(source, dest), result)

    def test_path_to_dict(self):
        """Test that we can correctly convert paths into dictionaries."""
        self.assertEqual(
            path_to_dict("s3://bucket/key.txt"), {"bucket": "bucket", "key": "key.txt"}
        )

    def test_get_target_filename_from_src_key_with_default(self):
        """Test the default substitution."""
        for key, filename in [
            ("my/file.csv", "file.csv"),
            ("two/dirs/file.csv", "file.csv"),
        ]:
            with self.subTest(key):
                self.assertEqual(
                    get_target_filename_from_src_key(
                        key,
                        SubstitutionInfo(),
                    ),
                    filename,
                )

    def test_get_target_filename_from_src_key_with_date(self):
        """Test a substitution that uses the date in the key."""
        pattern = r"^.*/([0-9]{4}-[0-9]{2}-[0-9]{2})/([^/]*)\.csv"
        repl = r"\2_\1.csv"
        for key, filename in [
            ("my/2023-06-07/file.csv", "file_2023-06-07.csv"),
            ("two/dirs/2023-06-07/file.csv", "file_2023-06-07.csv"),
        ]:
            with self.subTest(key):
                self.assertEqual(
                    get_target_filename_from_src_key(
                        key,
                        SubstitutionInfo(pattern, repl),
                    ),
                    filename,
                )

    def test_get_target_filename_from_src_key_with_date_and_timestamp(self):
        """Test a substitution that uses the date in the key and adds a timestamp."""
        pattern = r"^.*/([0-9]{4}-[0-9]{2}-[0-9]{2})/([^/]*)\.csv"
        repl = r"\2_<TIMESTAMP>_edge_\1.csv"
        for key, filename_regex in [
            ("my/2023-06-07/file.csv", r"file_[0-9]{8}T[0-9]{6}Z_edge_2023-06-07\.csv"),
            (
                "two/dirs/2023-06-07/file.csv",
                r"file_[0-9]{8}T[0-9]{6}Z_edge_2023-06-07\.csv",
            ),
        ]:
            with self.subTest(key):
                self.assertRegex(
                    get_target_filename_from_src_key(
                        key,
                        SubstitutionInfo(pattern, repl),
                    ),
                    filename_regex,
                )

    def test_gisaid(self):
        """Test gisaid regular expression."""
        pattern = "^.*/([0-9]{4}-[0-9]{2}-[0-9]{2})/([^/]*)\\.json"
        repl = "\\2_\u003cTIMESTAMP\u003e_edge_\\1.json.xz"
        self.assertRegex(
            get_target_filename_from_src_key(
                "gisaid/2023-06-08/gisaid.json", SubstitutionInfo(pattern, repl)
            ),
            r"gisaid_[0-9]{8}T[0-9]{6}Z_edge_2023-06-08.json.xz",
        )


if __name__ == "__main__":
    unittest.main()
