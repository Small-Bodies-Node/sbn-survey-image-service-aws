import os
from tempfile import NamedTemporaryFile

import numpy as np
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS
from PIL import Image
from pyavm import AVM


def north_up_preview(hdu, image_format: str) -> bytes:
    """Derive the same ICRS TAN view as UMD/CAT without modifying science data.

    Tile nearest-neighbor reprojection to bound Lambda memory. Use full native
    WCS (including TPV) and embed the output WCS in both JPEG and PNG.
    """
    data = hdu[0].data
    height, width = data.shape
    native = WCS(hdu[0].header).celestial
    if not native.has_celestial:
        raise ValueError("Cannot align an image without celestial WCS")
    center = native.pixel_to_world((width - 1) / 2, (height - 1) / 2).icrs
    scales = native.proj_plane_pixel_scales()
    target = WCS(naxis=2)
    target.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    target.wcs.radesys = "ICRS"
    target.wcs.crpix = [(width + 1) / 2, (height + 1) / 2]
    target.wcs.crval = [center.ra.deg, center.dec.deg]
    target.wcs.cdelt = [-abs(scales[0].value), abs(scales[1].value)]
    target.pixel_shape = (width, height)
    rendered = np.full(data.shape, np.nan, dtype=float)
    for start in range(0, height, 128):
        stop = min(start + 128, height)
        yy, xx = np.mgrid[start:stop, :width]
        x, y = native.world_to_pixel(target.pixel_to_world(xx, yy))
        valid = np.isfinite(x) & np.isfinite(y)
        ix = np.floor(np.nan_to_num(x) + 0.5).astype(int)
        iy = np.floor(np.nan_to_num(y) + 0.5).astype(int)
        valid &= (ix >= 0) & (ix < width) & (iy >= 0) & (iy < height)
        tile = rendered[start:stop]
        tile[valid] = data[iy[valid], ix[valid]]
    scaled = (
        ZScaleInterval()(rendered) * 255
        if np.isfinite(rendered).any()
        else np.zeros(data.shape)
    )
    pixels = np.nan_to_num(scaled).clip(0, 255).astype(np.uint8)[::-1]
    with NamedTemporaryFile(suffix=f".{image_format}", delete=False) as tmp:
        path = tmp.name
    try:
        Image.fromarray(pixels).save(path, format=image_format, quality=95)
        AVM.from_wcs(target, shape=data.shape).embed(path, path)
        with open(path, "rb") as stream:
            return stream.read()
    finally:
        os.remove(path)
