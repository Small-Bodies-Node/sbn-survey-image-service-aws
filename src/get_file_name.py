import re


def get_file_name(event: dict) -> str:
    """
    Take lambda event extract the file name from the URL.
    """

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
