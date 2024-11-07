# SBN Survey Image Service AWS

## What's This?

This is a lambda function with S3-caching to retrieve FITS and JPEG images.  The function is intended to be served by AWS's Gateway API.  URLs requesting data take the following format:

```
https://HOST/api/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:703_20220122_2b_n32022_01_0003.arch?ra=107.10813&dec=30.84928&size=5arcmin&format=jpeg
```

It is used by [CATCH](https://catch.astro.umd.edu) and other services maintained by [SBN](https://pds-smallbodies.astro.umd.edu/) at [UMD](https://www.astro.umd.edu/).

## Overview

The AWS Lambda function:

1. Receives path and query parameters.
2. Formulate a unique file name based on the query.
3. Checks if a corresponding file exists within a data cache backed by an S3 bucket.
4. If the file exists, it is returned to the user.
5. If the file does not exist, then the data is retrieved from externally hosted services.
6. Images are converted to the user's requested format (e.g., JPEG or PNG).
7. The result is cached to S3 and returned to the user.

Catalina Sky Survey, NEAT, and Spacewatch data archived at `sbnarchive.psi.edu` are presently supported.

## Development notes

### Testing

Unit tests are in the src/test_sbn_sis.py file.  They are designed to be run with `pytest src/`.  The tests can also be run with the Makefile, which will setup a virtual environment in the `test-venv` directory:

```bash
make test
```

### Misc

Test Lambda function:

```json
{
  "queryStringParameters": {
    "lid": "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch",
    "ra": 190.99166667,
    "dec": 23.92305556,
    "size": "5 arcmin",
    "format": "jpeg"
  }
}
```

Test API Gateway query string:

```
/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch?ra=190.99166667&dec=23.92305556&size=5arcmin&format=jpeg
```

Test API Gateway method:

lid: urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch
Query strings: ra=190.99166667&dec=23.92305556&size=5arcmin
