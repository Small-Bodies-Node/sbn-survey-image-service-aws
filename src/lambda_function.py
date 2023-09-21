import io
import base64
from astropy.io import fits
from sbn_sis import cutout_handler


def lambda_handler(event, context):
    hdu: fits.HDUList = cutout_handler(
        event["queryStringParameters"]["lid"],
        event["queryStringParameters"]["ra"],
        event["queryStringParameters"]["dec"],
        event["queryStringParameters"]["size"],
    )
    data: io.BytesIO = io.BytesIO()
    hdu.writeto(data, output_verify="ignore")

    return {
        "headers": {"Content-Type": "image/fits"},
        "statusCode": 200,
        "body": base64.b64encode(data.getvalue()).decode("utf-8"),
        "isBase64Encoded": True,
    }
