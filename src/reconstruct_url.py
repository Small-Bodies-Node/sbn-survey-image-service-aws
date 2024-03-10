

# def reconstruct_url(event):
#     """ Reconstruct the full URL from the event object. """

#     # Get the HTTP method and the path
#     http_method = event.get('httpMethod')
#     path = event.get('path')

#     # API Gateway passes the host and protocol in headers
#     host = event['headers'].get('Host')
#     # Typically 'http' or 'https'
#     protocol = event['headers'].get('X-Forwarded-Proto')

#     # Reconstruct the base URL
#     base_url = f"{protocol}://{host}{path}"

#     # Check if there are query string parameters and append them if present
#     query_string_params = event.get('queryStringParameters')
#     print('+++++++++')
#     print(query_string_params)
#     print('+++++++++')
#     if query_string_params:
#         query_string = '&'.join(
#             [f"{key}={value}" for key, value in query_string_params.items()])
#         full_url = f"{base_url}?{query_string}"
#     else:
#         full_url = base_url

#     print("Full URL:", full_url)
#     return full_url
