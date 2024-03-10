# SBN Survey Image Service AWS

## What's This?

This is a lambda function with S3-caching to retrieve fits and jpeg images with urls of the following format:

```
https://HOST/api/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:703_20220122_2b_n32022_01_0003.arch?ra=107.10813&dec=30.84928&size=5arcmin&format=jpeg
```

It is used by [CATCH](https://catch.astro.umd.edu) and other services maintained by [SBN](https://pds-smallbodies.astro.umd.edu/) at [UMD](https://www.astro.umd.edu/).


## Overview

The AWS Lambda function receives path params and query params, checks if a corresponding image exists within the S3 bucket and returns that if it does. If the image does not exist then the master fits file is retrieved from `sbnarchive.psi.edu`, a cutout is made, and either returned directly or used to generate a jpeg file. Before returning the file is saved to the image cache.


## Development notes

### Misc

Test Lambda function:

```json
{
    "queryStringParameters": {
        "lid": "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch",
        "ra": 190.99166667,
        "dec": 23.92305556,
        "size": "5 arcmin"
    }
}
```

Test Gateway API query string:
```
/images/urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch?ra=190.99166667&dec=23.92305556&size=5arcmin
```
