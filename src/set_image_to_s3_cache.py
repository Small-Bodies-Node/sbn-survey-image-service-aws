
import io
import boto3


def set_image_to_s3_cache(buffer: io.BytesIO, bucket_name: str, file_key: str, content_type: str):
    """
    Save an image from a BytesIO buffer to an S3 bucket as a specific file type.

    :param buffer: io.BytesIO object containing the image data.
    :param bucket_name: Name of the S3 bucket to upload to.
    :param file_key: The key (path) where the image should be saved in the bucket, including the file extension.
    """
    # Create an S3 client
    s3 = boto3.client('s3')

    # Make sure the buffer's pointer is at the beginning
    buffer.seek(0)

    # Upload the image from the BytesIO object to S3
    s3.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=buffer,
        ContentType=content_type
    )
