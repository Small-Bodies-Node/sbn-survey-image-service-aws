
from lambda_function import lambda_handler


def local_lambda_run():
    """
        Run the lambda function locally for debugging
        You might need to first source .env and export the environment variables
    """

    event = {
        "httpMethod": "GET",
        "path": "/api/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:703_20220122_2b_n32022_01_0003.arch",
        "headers": {
            "Host": "localhost:3000",
            "X-Forwarded-Proto": "http"
        },
        "queryStringParameters": {
            "ra": "107.10813",
            "dec": "30.84928",
            "size": "5arcmin",
            "x": "2",
            # "format": "png"
            # "format": "jpeg"
            "format": "fits"
        },
        "pathParameters": {
            "lid": "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:703_20220122_2b_n32022_01_0003.arch"
        }
    }
    context = None
    result = lambda_handler(event, context)
    print(result)


if __name__ == "__main__":
    local_lambda_run()
