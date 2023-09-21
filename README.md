

## Development notes

Test Lambda function:

```json
{
    "queryStringParameters": {
        "lid": "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch",
        "ra": "12:43:58",
        "dec": "23:55:23",
        "size": "5 arcmin"
    }
}
```

Test Gateway API query string:
```
lid=urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch&ra=12:43:58&dec=23:55:23&size=5arcmin
```
