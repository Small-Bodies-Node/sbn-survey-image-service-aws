import re


def get_file_name(event: dict) -> str:
    """
      Take lambda event,
      reconstruct the full URL,
      and extract the file name from the URL.
    """

    # Get the HTTP method and the path
    http_method = event.get('httpMethod')
    path = event.get('path')

    # API Gateway passes the host and protocol in headers
    host = event['headers'].get('Host')
    # Typically 'http' or 'https'
    protocol = event['headers'].get('X-Forwarded-Proto')

    # Reconstruct the base URL
    base_url = f"{protocol}://{host}{path}"

    # Check if there are query string parameters and append them if present
    query_string_params = event.get('queryStringParameters')
    if query_string_params:
        query_string = '&'.join(
            [f"{key}={value}" for key, value in query_string_params.items()])
        full_url = f"{base_url}?{query_string}"
    else:
        full_url = base_url

    # print('+++++++++')
    # print(query_string_params)
    # print(full_url)
    # print('+++++++++')

    # Extract the content after the last '/'
    last_slash_index = full_url.rfind('/')
    if last_slash_index == -1:
        content_after_last_slash = full_url
    else:
        content_after_last_slash = full_url[last_slash_index + 1:]

    # Convert to a file-name friendly format
    safe_filename = re.sub(r'[/:?&=\.]', '_', content_after_last_slash)

    # "..._format_jpeg..." -> "... .jpeg", etc.
    if '_format_jpg' in safe_filename.lower() or '_format_jpeg' in safe_filename.lower():
        image_filename = safe_filename.replace('_format_jpeg', '') + '.jpeg'
    if '_format_fits' in safe_filename.lower():
        image_filename = safe_filename.replace('_format_fits', '') + '.fits'

    return image_filename
