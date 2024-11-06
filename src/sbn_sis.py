import warnings
from enum import Enum
from PIL import Image
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS, FITSFixedWarning
from astropy.visualization import ZScaleInterval
from lid import LID
from lid_to_url import lid_to_url


class ImageFormat(Enum):
    FITS: str = "fits"
    JPEG: str = "jpeg"
    PNG: str = "png"


def cutout_handler(lid: str, ra: float, dec: float, size: str) -> fits.HDUList:
    """Entry point for getting image cutouts.


    Parameters
    ----------
    lid : LID
        PDS4 logical identifier.

    ra : float
        Right ascension in units of degrees.

    dec : float
        Declination in units of degrees.

    size : string
        Cutout size, parsable by `astropy.units.Quantity`.  Minimum 1 arcsec.


    Returns
    -------
    cutout : fits.HDUList

    """

    lid: LID = LID(lid)

    position: SkyCoord = SkyCoord(ra, dec, unit=(u.deg, u.deg))
    _size: u.Quantity = np.maximum(u.Quantity(size), 1 * u.arcsec)

    url: str = lid_to_url(lid)
    data: fits.HDUList
    with fits.open(url, use_fsspec=True, lazy_load_hdus=True) as data:
        i: int = 0
        if lid.bundle == "gbo.ast.catalina.survey":
            i = 1

        data[i].header["CTYPE1"] = "RA---TPV"
        data[i].header["CTYPE2"] = "DEC--TPV"
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore", (fits.verify.VerifyWarning, FITSFixedWarning)
            )
            wcs: WCS = WCS(data[i].header)

        cutout: Cutout2D = Cutout2D(data[i].section, position, _size, wcs=wcs)

        header: fits.Header = data[i].header
        header.update(cutout.wcs.to_header())

    result: fits.HDUList = fits.HDUList()
    result.append(fits.PrimaryHDU(cutout.data, header))

    return result


def fits_to_image(hdu: fits.HDUList) -> Image:
    """Convert FITS data to PIL Image."""
    interval: ZScaleInterval = ZScaleInterval()
    scaled_data: np.ndarray = interval(hdu[0].data, clip=True) * 255
    return Image.fromarray(scaled_data.astype(np.uint8))
