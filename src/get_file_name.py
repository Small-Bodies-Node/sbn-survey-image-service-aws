import re
from hashlib import sha256
from urllib.parse import urlencode

from uses_north_up_renderer import NORTH_UP_RENDERER_VERSION, uses_north_up_renderer


def get_file_name(event: dict) -> str:
    """
    Take lambda event extract the file name from the URL.
    """

    # Opted-in previews bypass old browse objects; legacy URLs keep their keys.
    parameters = event.get("queryStringParameters") or {}
    image_format = str(parameters.get("format", "fits")).lower()
    if uses_north_up_renderer(parameters):
        query = urlencode(sorted(parameters.items()))
        identity = f"{NORTH_UP_RENDERER_VERSION}:{event.get('path', '')}?{query}"
        extension = "jpeg" if image_format == "jpg" else image_format
        digest = sha256(identity.encode()).hexdigest()
        return f"{NORTH_UP_RENDERER_VERSION}-{digest}.{extension}"

    # Get the HTTP path
    path = event.get("path")

    # Check if there are query string parameters and append them if present
    query_string_params = event.get("queryStringParameters")
    if query_string_params:
        query_string = "&".join(
            [f"{key}={value}" for key, value in query_string_params.items()]
        )
        path = f"{path}?{query_string}"

    # Extract the content after the last '/'
    last_slash_index = path.rfind("/")
    if last_slash_index == -1:
        content_after_last_slash = path
    else:
        content_after_last_slash = path[last_slash_index + 1 :]

    # Convert to a file-name friendly format
    safe_filename = re.sub(r"[/:?&=\.]", "_", content_after_last_slash)

    # "..._format_jpeg..." -> "... .jpeg", etc.
    if (
        "_format_jpg" in safe_filename.lower()
        or "_format_jpeg" in safe_filename.lower()
    ):
        image_filename = safe_filename.replace("_format_jpeg", "") + ".jpeg"
    elif "_format_png" in safe_filename.lower():
        image_filename = safe_filename.replace("_format_png", "") + ".png"
    else:
        # must be FITS
        image_filename = safe_filename.replace("_format_fits", "") + ".fits"

    return image_filename
