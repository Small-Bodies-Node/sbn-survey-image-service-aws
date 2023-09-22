import io
import base64
from PIL import Image
from astropy.io import fits
from sbn_sis import cutout_handler, fits_to_image, ImageFormat


def lambda_handler(event: dict, context):
    image_format: ImageFormat = ImageFormat(
        event["queryStringParameters"]["format"].lower())
    hdu: fits.HDUList = cutout_handler(
        event["queryStringParameters"]["lid"],
        event["queryStringParameters"]["ra"],
        event["queryStringParameters"]["dec"],
        event["queryStringParameters"]["size"],
    )

    buffer: io.BytesIO = io.BytesIO()
    if image_format == ImageFormat.FITS:
        hdu.writeto(buffer, output_verify="ignore")
    else:
        image: Image = fits_to_image(hdu)
        image.save(buffer, format=image_format.value)

    return {
        "headers": {"Content-Type": f"image/{image_format.value}"},
        "statusCode": 200,
        "body": base64.b64encode(buffer.getvalue()).decode("utf-8"),
        "isBase64Encoded": True,
    }
