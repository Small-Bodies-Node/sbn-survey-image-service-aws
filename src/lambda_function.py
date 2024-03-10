import os
import io
import base64

from PIL import Image
from astropy.io import fits
from sbn_sis import cutout_handler, fits_to_image, ImageFormat

from get_file_name import get_file_name
# from reconstruct_url import reconstruct_url
from list_files_in_s3_bucket import list_files_in_s3_bucket
from set_image_to_s3_cache import set_image_to_s3_cache
from get_image_from_s3_cache import get_image_from_s3_cache


def lambda_handler(event: dict, context):

    image_format: ImageFormat = ImageFormat(
        event["queryStringParameters"].get("format", "fits").lower()
    )

    if image_format.value not in ["fits", "jpeg", "png"]:
        return {
            "statusCode": 400,
            "body": "Invalid image format. Must be one of: fits, jpeg, png"
        }

    # Check for cached image
    cached_filename = get_file_name(event)
    caching_bucket = os.getenv('S3_CACHE_BUCKET_NAME', None)
    if not caching_bucket:
        return {
            "statusCode": 500,
            "body": "S3_CACHE_BUCKET_NAME environment variable not set"
        }
    cached_file_buffer = get_image_from_s3_cache(
        caching_bucket,
        cached_filename
    )
    if cached_file_buffer:
        return {
            "headers": {"Content-Type": f"image/{image_format.value}"},
            "statusCode": 200,
            "body": base64.b64encode(cached_file_buffer.getvalue()).decode("utf-8"),
            "isBase64Encoded": True,
        }

    # No cached-file found, so fetch from the cutout service
    hdu: fits.HDUList = cutout_handler(
        event["pathParameters"]["lid"],
        float(event["queryStringParameters"]["ra"]),
        float(event["queryStringParameters"]["dec"]),
        event["queryStringParameters"]["size"],
    )

    buffer: io.BytesIO = io.BytesIO()
    if image_format == ImageFormat.FITS:
        hdu.writeto(buffer, output_verify="ignore")
    else:
        image: Image = fits_to_image(hdu)
        image.save(buffer, format=image_format.value)

    mime_type = f"image/{image_format.value}"

    set_image_to_s3_cache(
        buffer, caching_bucket, cached_filename, mime_type
    )

    return {
        "headers": {"Content-Type": mime_type},
        "statusCode": 200,
        "body": base64.b64encode(buffer.getvalue()).decode("utf-8"),
        "isBase64Encoded": True,
    }
