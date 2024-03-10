import io
import boto3
from botocore.exceptions import ClientError


def get_image_from_s3_cache(bucket_name: str, file_key: str) -> io.BytesIO | None:
    """
    Check if a file exists in an S3 bucket.
    If it exists, return the file as a BytesIO buffer.
    Else, return None.

    :param bucket_name: Name of the S3 bucket.
    :param file_key: Key of the file to check.
    :return: True if the file exists, False otherwise.
    """

    # Check if file exists in S3
    s3 = boto3.client('s3')

    try:
        # Attempt to fetch the metadata of the file
        s3.head_object(Bucket=bucket_name, Key=file_key)
    except ClientError as e:
        # If a ClientError is raised, check if it was because the file was not found
        if e.response['Error']['Code'] == '404':
            # The file does not exist
            print(e.response['Error']['Message'])
            return None
        else:
            # Some other error occurred
            raise

    # File exists, so fetch and return
    response = s3.get_object(Bucket=bucket_name, Key=file_key)

    # Access the file's body and read it into a BytesIO buffer
    buffer = io.BytesIO(response['Body'].read())

    return buffer
