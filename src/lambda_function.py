import os
import io
import base64
from enum import Enum

from sbn_sis import cutout_handler, fits_to_image

from get_file_name import get_file_name
from set_image_to_s3_cache import set_image_to_s3_cache
from get_image_from_s3_cache import get_image_from_s3_cache


class ImageFormat(Enum):
    FITS: str = "fits"
    JPEG: str = "jpeg"
    PNG: str = "png"

    @property
    def mime_type(self) -> str:
        return f"image/{self.value}"


def lambda_handler(event: dict, context):
    # ENV variables must be set
    caching_bucket = os.getenv("S3_CACHE_BUCKET_NAME", None)
    if not caching_bucket:
        return {
            "statusCode": 500,
            "body": "S3_CACHE_BUCKET_NAME environment variable not set",
        }

    # Image format must be valid
    try:
        image_format = ImageFormat(
            event["queryStringParameters"].get("format", "fits").lower()
        )
    except ValueError:
        return {
            "statusCode": 400,
            "body": "Invalid image format. Must be one of: fits, jpeg, png",
        }

    # Check for cached image
    cached_filename = get_file_name(event)
    cached_file_buffer = get_image_from_s3_cache(caching_bucket, cached_filename)

    if cached_file_buffer:
        # Cached file found
        content_body = base64.b64encode(cached_file_buffer.getvalue()).decode("utf-8")
    else:
        # Cached file not found, so fetch from the cutout service
        hdu = cutout_handler(
            event["pathParameters"]["lid"],
            float(event["queryStringParameters"]["ra"]),
            float(event["queryStringParameters"]["dec"]),
            event["queryStringParameters"]["size"],
        )

        buffer: io.BytesIO = io.BytesIO()
        if image_format == ImageFormat.FITS:
            hdu.writeto(buffer, output_verify="ignore")
        else:
            image = fits_to_image(hdu)
            image.save(buffer, format=image_format.value, quality=95)

        content_body = base64.b64encode(buffer.getvalue()).decode("utf-8")
        set_image_to_s3_cache(
            buffer, caching_bucket, cached_filename, image_format.mime_type
        )

    return {
        "headers": {
            "Content-Type": image_format.mime_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "statusCode": 200,
        "body": content_body,
        "isBase64Encoded": True,
    }
