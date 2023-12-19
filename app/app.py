import gzip
import shutil
import logging
import os
import re
from io import BytesIO
import boto3


def path_to_dict(s3_path: str) -> dict:
    """Convert an S3 path into a dictionary."""
    regex = r"s3://(.[^/]*)/(.*)"
    matches = re.search(regex, s3_path, re.IGNORECASE)

    if not matches:
        raise RuntimeError(f"Incorrect S3 path: {s3_path}")

    return {"bucket": matches.group(1), "key": matches.group(2)}


def copy_to_staging(
    src_bucket: str,
    src_key: str,
    dst_bucket: str,
):
    s3_client = boto3.client("s3")
    s3_client.copy(
        CopySource={"Bucket": src_bucket, "Key": src_key},
        Bucket=dst_bucket,
    )

    s3_client.delete_object(Bucket=src_bucket, Key=src_key)


def _do_copy_one_file_to_file(
    src_bucket: str,
    src_key: str,
    dst_bucket: str,
    dst_dir: str,
):
    s3_client = boto3.client("s3")
    s3_client.copy(
        CopySource={"Bucket": src_bucket, "Key": src_key},
        Bucket=dst_bucket,
        Key=dst_dir,
    )

    s3_client.delete_object(Bucket=src_bucket, Key=src_key)


def combine_gzip_files_s3(bucket_name, matching_objects, output_file):
    s3 = boto3.client('s3')

    with open(output_file, 'wb') as outfile:
        for prefix in sorted(matching_objects):
            response = s3.get_object(Bucket=bucket_name, Key=prefix)
            with gzip.GzipFile(fileobj=BytesIO(response['Body'].read())) as infile:
                shutil.copyfileobj(infile, outfile)


def check_if_single_or_multiple_files(source_bucket_name: tuple, source_target_filename_prefix: str) -> list:
    s3 = boto3.client('s3')
    objects = s3.list_objects_v2(Bucket=source_bucket_name).get('Contents', [])
    matching_objects = [obj for obj in objects if obj['Key'].startswith(source_target_filename_prefix)]

    if not matching_objects:
        print(f"No objects with prefix '{source_target_filename_prefix}' found in the bucket '{source_bucket_name}'.")
    elif len(matching_objects) == 1 and not matching_objects[0]['Key'].endswith('/'):
        print(f"The bucket '{source_bucket_name}' contains one file with prefix '{source_target_filename_prefix}'.")
        return matching_objects
    else:
        gzip_files = [obj for obj in matching_objects if obj['Key'].lower().endswith('.gz')]

        if len(gzip_files) > 1:
            print(f"The bucket '{source_bucket_name}' contains multiple gzip files with a common prefix "
                  f"'{source_target_filename_prefix}'.")
            return matching_objects
        else:
            print(f"The bucket '{source_bucket_name}' does not meet the specified criteria.")


def get_filename_prefix(source_prefix):
    first_dot_index = source_prefix.find('.')
    base_filename = source_prefix[:first_dot_index] if first_dot_index != -1 else source_prefix
    return base_filename


def copy_objects(source: str, destination: str):
    source_dict = path_to_dict(source)
    destination_dict = path_to_dict(destination)

    source_bucket = source_dict["bucket"]
    source_prefix = source_dict["key"]
    dest_bucket = destination_dict["bucket"]
    dest_prefix = destination_dict["key"]

    filename_prefix = get_filename_prefix(source_prefix)

    matching_objects = check_if_single_or_multiple_files(source_bucket, filename_prefix)
    if len(matching_objects) > 1:
        combine_gzip_files_s3(
            source_dict["bucket"],
            matching_objects,
            dest_bucket,
        )
        delete_all_gzip_files(source_dict["bucket"])
    if matching_objects == 1:
        matching_object = "".join(matching_objects)
        _do_copy_one_file_to_file(source_bucket, matching_object, dest_bucket, dest_prefix)


def delete_all_gzip_files(source: str):
    """Copy or move S3 objects."""
    source_dict = path_to_dict(source)
    s3 = boto3.client('s3')

    objects = s3.list_objects_v2(Bucket=source_dict).get('Contents', [])

    for obj in objects:
        key = obj['Key']
        if key.endswith('.gz'):
            s3.delete_object(Bucket=source_dict, Key=key)
            print(f"Deleted: s3://{source_dict}/{key}")


def main(event):
    copy_objects(
        source=event["source"],
        destination=event["destination"],
    )
    

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))
    main(
        {
            "source": os.getenv("SOURCE", ""),
            "destination": os.getenv("DESTINATION", ""),
        }
    )
