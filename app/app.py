"""Main module.
"""

from dataclasses import dataclass
import datetime as dt
import logging
import os
import pathlib
import re

import boto3


DEFAULT_S3_KEY_PATTERN = r"^(?:.*/)?([^/]*)$"
DEFAULT_S3_KEY_REPL = r"\1"


@dataclass
class SubstitutionInfo:
    """Information needed to generate the target file name from the source key."""

    s3_key_pattern: str = DEFAULT_S3_KEY_PATTERN
    s3_key_repl: str = DEFAULT_S3_KEY_REPL


def path_to_dict(s3_path: str) -> dict:
    """Convert an S3 path into a dictionary."""
    regex = r"s3://(.[^/]*)/(.*)"
    matches = re.search(regex, s3_path, re.IGNORECASE)

    if not matches:
        raise RuntimeError(f"Incorrect S3 path: {s3_path}")

    return {"bucket": matches.group(1), "key": matches.group(2)}


def s3_key_is_dir(s3_key: str) -> bool:
    """Returns true if ``s3_key`` is a directory."""
    return len(s3_key) == 0 or s3_key[-1:] == "/"


def s3_key_is_file(s3_key: str) -> bool:
    """Returns true if ``s3_key`` is a file."""
    return not s3_key_is_dir(s3_key)


def check_if_file_to_file_copy(source_key: str, dest_key: str) -> bool:
    """check if file to file copy"""
    file_to_file = False

    if s3_key_is_file(source_key) and s3_key_is_file(dest_key):
        file_to_file = True
    elif s3_key_is_dir(source_key) and s3_key_is_file(dest_key):
        raise RuntimeError("It is not possible to copy a directory to a file.")
    elif (
        pathlib.PurePosixPath(source_key).suffix
        != pathlib.PurePosixPath(dest_key).suffix
        and pathlib.PurePosixPath(source_key).suffix != ""
        and pathlib.PurePosixPath(dest_key).suffix != ""
    ):
        raise RuntimeError("Source and target files have different formats.")

    return file_to_file


def copy_objects(
    source: str,
    destination: str,
    delete_after_copy: bool,
    max_age: int,
    s3_key_regex: str,
    substituttion_info: SubstitutionInfo,
):
    """Copy or move S3 objects."""
    source_dict = path_to_dict(source)
    destination_dict = path_to_dict(destination)
    s3_client = boto3.client("s3")
    first = True
    cont_token = ""
    file_to_file = check_if_file_to_file_copy(
        source_dict["key"], destination_dict["key"]
    )
    while first or cont_token:
        first = False
        response = (
            s3_client.list_objects_v2(
                Bucket=source_dict["bucket"],
                Prefix=source_dict["key"],
                ContinuationToken=cont_token,
            )
            if cont_token
            else s3_client.list_objects_v2(
                Bucket=source_dict["bucket"], Prefix=source_dict["key"]
            )
        )
        cont_token = response.get("NextContinuationToken", "")

        objs = response.get("Contents", None)
        if not objs:
            logging.warning("No files found in source.")
            return
        for obj in objs:
            this_source_key = obj.get("Key", "")
            logging.debug("Processing source key: %s", this_source_key)
            if not re.fullmatch(s3_key_regex, this_source_key):
                logging.debug("Skipping key (regex): %s", this_source_key)
                continue
            if max_age > 0 and _file_older_than_hours(obj, max_age_hours=max_age):
                logging.debug("Skipping key (max_age): %s", this_source_key)
                continue

            logging.info(
                'Copying file: "%s" to "%s"',
                f"s3://{source_dict['bucket']}/{this_source_key}",
                f"s3://{destination_dict['bucket']}/{destination_dict['key']}",
            )
            if not file_to_file:
                _do_copy_one_file_to_dir(
                    source_dict["bucket"],
                    this_source_key,
                    destination_dict["bucket"],
                    destination_dict["key"],
                    delete_after_copy,
                    substituttion_info,
                )
            else:
                _do_copy_one_file_to_file(
                    source_dict["bucket"],
                    this_source_key,
                    destination_dict["bucket"],
                    destination_dict["key"],
                    delete_after_copy,
                )


def _file_older_than_hours(s3_object, max_age_hours: float) -> bool:
    """Return ``True`` if ``s3_object`` is older than ``max_age_hours``."""
    # last modified date zone-aware datetime
    last_modified_datetime = s3_object.get("LastModified")
    if last_modified_datetime is None:
        logging.warning(
            "Cannot determine last-modified date of key: %s", s3_object.get("Key")
        )
        return True

    now_utc = dt.datetime.now(dt.timezone.utc)
    age_hours = (now_utc - last_modified_datetime).total_seconds() / 60 / 60
    if age_hours > max_age_hours:
        logging.debug(
            "File is older than %g hours. Max age is %g hours.",
            age_hours,
            max_age_hours,
        )
        return True

    return False


def get_target_filename_from_src_key(
    src_key: str, substitution_info: SubstitutionInfo
) -> str:
    """Obtain the filename from the ``src_key``.

    This function will apply a ``re.sub()`` using the parameters in
    ``substitution_info``.

    Args:
        src_key (str): The source S3 key (i.e.: 'ONS/my_table/')
        substitution_info (SubstitutionInfo): _description_

    Returns:
        str: _description_
    """
    substituted = re.sub(
        substitution_info.s3_key_pattern, substitution_info.s3_key_repl, src_key
    )
    # replace <TIMESTAMP> with an actual timestamp
    if "<TIMESTAMP>" in substituted:
        timestamp_str = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        substituted = substituted.replace("<TIMESTAMP>", timestamp_str)
    logging.info(
        "Src Key: %s SubstitutionInfo: %r RESULT: %s",
        src_key,
        substitution_info,
        substituted,
    )
    return substituted


def _do_copy_one_file_to_dir(
    src_bucket: str,
    src_key: str,
    dst_bucket: str,
    dst_dir: str,
    delete_after_copy: bool,
    substitution_info: SubstitutionInfo,
):
    # this_source_filename = src_key.rsplit("/", 1)[1] if "/" in src_key else src_key
    this_source_filename = get_target_filename_from_src_key(src_key, substitution_info)
    target_key = f"{dst_dir}{this_source_filename}"
    # apply name transformation on the target key

    s3_client = boto3.client("s3")
    s3_client.copy(
        CopySource={"Bucket": src_bucket, "Key": src_key},
        Bucket=dst_bucket,
        Key=target_key,
    )
    if delete_after_copy:
        s3_client.delete_object(Bucket=src_bucket, Key=src_key)


def _do_copy_one_file_to_file(
    src_bucket: str,
    src_key: str,
    dst_bucket: str,
    dst_dir: str,
    delete_after_copy: bool,
):
    s3_client = boto3.client("s3")
    s3_client.copy(
        CopySource={"Bucket": src_bucket, "Key": src_key},
        Bucket=dst_bucket,
        Key=dst_dir,
    )
    if delete_after_copy:
        s3_client.delete_object(Bucket=src_bucket, Key=src_key)


def main(event, _context):
    """Main function."""
    # copy or move objects
    copy_objects(
        source=event["source"],
        destination=event["destination"],
        delete_after_copy=event["move"],
        max_age=event["max_age"],
        s3_key_regex=event["s3_key_regex"],
        substituttion_info=event["substitution_info"],
    )


if __name__ == "__main__":
    # Convert arguments passed through the environment to a dictionary
    logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))
    main(
        {
            "source": os.getenv("SOURCE", ""),
            "destination": os.getenv("DESTINATION", ""),
            "move": os.getenv("MOVE", "FALSE").upper() in ("TRUE", "Y", "YES", "1"),
            "max_age": int(os.getenv("MAX_AGE") or "0"),
            "s3_key_regex": os.getenv("S3_KEY_REGEX") or r"^.*$",
            "substitution_info": SubstitutionInfo(
                s3_key_pattern=os.getenv("S3_KEY_PATTERN") or DEFAULT_S3_KEY_PATTERN,
                s3_key_repl=os.getenv("S3_KEY_REPL") or r"\1",
            ),
        },
        None,
    )
