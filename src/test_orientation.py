import base64
import io
from unittest.mock import MagicMock
from urllib.parse import parse_qsl

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image
from pyavm import AVM

import lambda_function as handler
from get_file_name import get_file_name
from north_up_preview import north_up_preview


@pytest.mark.parametrize("prefix", ["", "stage/"])
@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize(
    "options",
    [
        {"format": "fits"},
        {"format": "jpeg"},
        {"format": "png", "align": "true", "renderer": "north-up-v1"},
    ],
)
def test_cache_namespace_applies_to_reads_and_writes(
    monkeypatch, prefix, cached, options
):
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    monkeypatch.setenv("S3_CACHE_KEY_PREFIX", prefix)
    lookup = MagicMock(return_value=io.BytesIO(b"CACHED") if cached else None)
    upload = MagicMock()
    monkeypatch.setattr(handler, "get_image_from_s3_cache", lookup)
    monkeypatch.setattr(handler, "set_image_to_s3_cache", upload)
    monkeypatch.setattr(
        handler,
        "cutout_handler",
        lambda *args: fits.HDUList([fits.PrimaryHDU(np.ones((3, 4)))]),
    )
    monkeypatch.setattr(handler, "fits_to_image", lambda *args: Image.new("L", (4, 3)))
    monkeypatch.setattr(handler, "north_up_preview", lambda *args: b"PREVIEW")
    event = {
        "path": "/api/images/id",
        "pathParameters": {"lid": "id"},
        "queryStringParameters": {
            "ra": "12",
            "dec": "-16",
            "size": "5arcmin",
            **options,
        },
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 200
    expected = prefix + get_file_name(event)
    assert lookup.call_args.args == ("test-only", expected)
    if cached:
        upload.assert_not_called()
    else:
        assert upload.call_args.args[1:3] == ("test-only", expected)


@pytest.mark.parametrize("angle,parity", [(0, -1), (31, -1), (180, -1), (31, 1)])
@pytest.mark.parametrize("image_format", ["jpeg", "png"])
def test_aligned_preview_has_output_wcs_and_preserves_science(
    tmp_path, angle, parity, image_format
):
    native = WCS(naxis=2)
    native.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    native.wcs.crval = [344.3, -16.2]
    native.wcs.crpix = [31, 19]
    r = np.deg2rad(angle)
    native.wcs.cd = np.array(
        [[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]]
    ) @ np.diag([parity * 0.00014, 0.00014])
    yy, xx = np.mgrid[:37, :61]
    data = np.exp(-((xx - 30) ** 2 + (yy - 18) ** 2) / 4)
    hdus = fits.HDUList([fits.PrimaryHDU(data, native.to_header())])
    path = tmp_path / f"view.{image_format}"
    path.write_bytes(north_up_preview(hdus, image_format))
    assert Image.open(path).size == (61, 37)
    np.testing.assert_array_equal(hdus[0].data, data)
    target = AVM.from_image(str(path)).to_wcs()
    assert target.wcs.cdelt[0] < 0 and target.wcs.cdelt[1] > 0
    assert (
        target.pixel_to_world(30, 18)
        .icrs.separation(native.pixel_to_world(30, 18).icrs)
        .arcsec
        < 1e-5
    )


def test_versioned_browse_cache_is_independent_of_parameter_order():
    one = {
        "path": "/id",
        "queryStringParameters": {
            "format": "jpeg",
            "ra": "12",
            "align": "true",
            "renderer": "north-up-v1",
        },
    }
    two = {
        "path": "/id",
        "queryStringParameters": {
            "renderer": "north-up-v1",
            "align": "true",
            "ra": "12",
            "format": "jpeg",
        },
    }
    assert get_file_name(one) == get_file_name(two)
    assert get_file_name(one).startswith("north-up-v1-")
    two["queryStringParameters"]["align"] = "false"
    assert get_file_name(one) != get_file_name(two)


@pytest.mark.parametrize("image_format", ["jpeg", "png"])
def test_lambda_honors_versioned_alignment_without_real_storage(
    monkeypatch, image_format
):
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    cache_lookup = MagicMock(return_value=None)
    monkeypatch.setattr(handler, "get_image_from_s3_cache", cache_lookup)
    monkeypatch.setattr(handler, "cutout_handler", lambda *args: "native science")
    called = []
    monkeypatch.setattr(
        handler,
        "north_up_preview",
        lambda hdu, fmt: called.append((hdu, fmt)) or b"PNG",
    )
    monkeypatch.setattr(handler, "set_image_to_s3_cache", lambda *args: None)
    event = {
        "path": "/id",
        "pathParameters": {"lid": "id"},
        "queryStringParameters": {
            "format": image_format,
            "align": "true",
            "renderer": "north-up-v1",
            "ra": "12",
            "dec": "-16",
            "size": "5arcmin",
        },
    }
    result = handler.lambda_handler(event, None)
    assert result["statusCode"] == 200 and base64.b64decode(result["body"]) == b"PNG"
    assert result["headers"]["Content-Type"] == f"image/{image_format}"
    assert result["headers"]["User-Agent"].endswith(handler.__version__)
    assert called == [("native science", image_format)]
    assert cache_lookup.call_args.args[1].startswith("north-up-v1-")


@pytest.mark.parametrize(
    "image_format,content_type",
    [("fits", "image/fits"), ("jpeg", "image/jpeg"), ("png", "image/png")],
)
def test_cached_response_keeps_version_and_content_type(
    monkeypatch, image_format, content_type
):
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    monkeypatch.setattr(
        handler, "get_image_from_s3_cache", lambda *args: io.BytesIO(b"CACHED")
    )
    cutout = MagicMock()
    renderer = MagicMock()
    monkeypatch.setattr(handler, "cutout_handler", cutout)
    monkeypatch.setattr(handler, "north_up_preview", renderer)
    event = {
        "path": "/id",
        "queryStringParameters": {"format": image_format, "align": "true"},
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 200
    assert result["headers"]["Content-Type"] == content_type
    assert result["headers"]["User-Agent"] == (
        f"SBN Survey Image Service AWS {handler.__version__}"
    )
    assert result["headers"]["Access-Control-Allow-Origin"] == "*"
    assert base64.b64decode(result["body"]) == b"CACHED"
    cutout.assert_not_called()
    renderer.assert_not_called()


@pytest.mark.parametrize("align", ["true", "false", "1"])
def test_fits_request_preserves_native_pixels_and_media_type(monkeypatch, align):
    data = np.arange(12, dtype=np.float32).reshape(3, 4)
    hdus = fits.HDUList([fits.PrimaryHDU(data)])
    renderer = MagicMock()
    upload = MagicMock()
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    monkeypatch.setattr(handler, "get_image_from_s3_cache", lambda *args: None)
    monkeypatch.setattr(handler, "cutout_handler", lambda *args: hdus)
    monkeypatch.setattr(handler, "north_up_preview", renderer)
    monkeypatch.setattr(handler, "set_image_to_s3_cache", upload)
    event = {
        "path": "/id",
        "pathParameters": {"lid": "id"},
        "queryStringParameters": {
            "format": "fits",
            "align": align,
            "renderer": "north-up-v1",
            "ra": "12",
            "dec": "-16",
            "size": "5arcmin",
        },
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 200
    assert result["headers"]["Content-Type"] == "image/fits"
    assert result["headers"]["User-Agent"].endswith(handler.__version__)
    with fits.open(io.BytesIO(base64.b64decode(result["body"]))) as returned:
        np.testing.assert_array_equal(returned[0].data, data)
    np.testing.assert_array_equal(hdus[0].data, data)
    renderer.assert_not_called()
    assert upload.call_args.args[3] == "image/fits"
    assert not upload.call_args.args[2].startswith("north-up-v1-")


@pytest.mark.parametrize(
    "query,expected_filename",
    [
        (
            "format=jpeg&ra=12&dec=-16&size=5arcmin",
            "id_ra_12_dec_-16_size_5arcmin.jpeg",
        ),
        (
            "format=png&ra=12&dec=-16&size=5arcmin&align=true",
            "id_ra_12_dec_-16_size_5arcmin_align_true.png",
        ),
        (
            "format=jpeg&ra=12&dec=-16&size=5arcmin&align=1",
            "id_ra_12_dec_-16_size_5arcmin_align_1.jpeg",
        ),
        (
            "format=png&ra=12&dec=-16&size=5arcmin&renderer=north-up-v2&align=true",
            "id_ra_12_dec_-16_size_5arcmin_renderer_north-up-v2_align_true.png",
        ),
        (
            "format=fits&ra=12&dec=-16&size=5arcmin&renderer=north-up-v1&align=true",
            "id_ra_12_dec_-16_size_5arcmin_renderer_north-up-v1_align_true.fits",
        ),
        (
            "ra=12&dec=-16&size=5arcmin",
            "id_ra_12_dec_-16_size_5arcmin.fits",
        ),
    ],
)
def test_legacy_cache_filenames_are_preserved(query, expected_filename):
    event = {
        "path": "/api/images/id",
        "queryStringParameters": dict(parse_qsl(query)),
    }

    assert get_file_name(event) == expected_filename


@pytest.mark.parametrize("image_format", ["jpeg", "png"])
@pytest.mark.parametrize(
    "options",
    [
        {},
        {"align": "true"},
        {"align": "false"},
        {"align": "1"},
        {"align": "true", "renderer": "north-up-v2"},
    ],
)
def test_legacy_browse_requests_keep_existing_rendering(
    monkeypatch, image_format, options
):
    hdus = fits.HDUList([fits.PrimaryHDU(np.ones((3, 4)))])
    legacy_image = Image.new("L", (4, 3), color=64)
    legacy_renderer = MagicMock(return_value=legacy_image)
    new_renderer = MagicMock()
    cache_lookup = MagicMock(return_value=None)
    upload = MagicMock()
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    monkeypatch.setattr(handler, "get_image_from_s3_cache", cache_lookup)
    monkeypatch.setattr(handler, "cutout_handler", lambda *args: hdus)
    monkeypatch.setattr(handler, "fits_to_image", legacy_renderer)
    monkeypatch.setattr(handler, "north_up_preview", new_renderer)
    monkeypatch.setattr(handler, "set_image_to_s3_cache", upload)
    event = {
        "path": "/api/images/id",
        "pathParameters": {"lid": "id"},
        "queryStringParameters": {
            "format": image_format,
            "ra": "12",
            "dec": "-16",
            "size": "5arcmin",
            **options,
        },
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 200
    assert result["headers"]["Content-Type"] == f"image/{image_format}"
    with Image.open(io.BytesIO(base64.b64decode(result["body"]))) as returned:
        np.testing.assert_array_equal(np.asarray(returned), np.full((3, 4), 64))
    legacy_renderer.assert_called_once_with(hdus)
    new_renderer.assert_not_called()
    assert not cache_lookup.call_args.args[1].startswith("north-up-v1-")
    assert upload.call_args.args[2] == cache_lookup.call_args.args[1]


@pytest.mark.parametrize("align", ["1", "invalid"])
def test_versioned_browse_requests_reject_invalid_alignment(monkeypatch, align):
    cache_lookup = MagicMock()
    monkeypatch.setenv("S3_CACHE_BUCKET_NAME", "test-only")
    monkeypatch.setattr(handler, "get_image_from_s3_cache", cache_lookup)
    event = {
        "path": "/id",
        "queryStringParameters": {
            "format": "png",
            "align": align,
            "renderer": "north-up-v1",
        },
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 400
    cache_lookup.assert_not_called()
