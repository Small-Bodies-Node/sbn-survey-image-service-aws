import io
import warnings
from enum import Enum
from typing import Dict
import requests
from PIL import Image
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS, FITSFixedWarning
from astropy.visualization import ZScaleInterval

mm_to_Mon: Dict[str, str] = {
    "01": "Jan",
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec",
}


class ImageFormat(Enum):
    FITS: str = "fits"
    JPEG: str = "jpeg"
    PNG: str = "png"


def cutout_handler(lid: str, ra: str, dec: str, size: str) -> fits.HDUList:
    """Entry point for getting image cutouts.


    Parameters
    ----------
    lid : string
        PDS4 logical identifier.

    ra : string
    dec : string
        Right ascension and declination in hour angle and degrees, parsable by
        `astropy.coordinates.SkyCoord`.

    size : string
        Cutout size, parsable by `astropy.units.Quantity`.


    Returns
    -------
    cutout : fits.HDUList

    """

    position: SkyCoord = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
    _size: u.QuantityInfo = np.minimum(u.Quantity(size), 15 * u.arcmin)

    url: str = lid_to_url(lid)
    response: requests.Response = requests.get(url)

    data: fits.HDUList = fits.open(io.BytesIO(response.content))

    data[1].header["CTYPE1"] = "RA---TPV"
    data[1].header["CTYPE2"] = "DEC--TPV"
    with warnings.catch_warnings():
        warnings.simplefilter(
            "ignore",
            (fits.verify.VerifyWarning, FITSFixedWarning)
        )
        wcs: WCS = WCS(data[1].header)

    cutout: Cutout2D = Cutout2D(data[1].data, position, _size, wcs=wcs)
    header: fits.Header = data[1].header
    header.update(cutout.wcs.to_header())

    hdu: fits.HDUList = fits.HDUList()
    hdu.append(fits.PrimaryHDU(cutout.data, header))

    del data
    return hdu


def get_product_id(lid: str) -> str:
    try:
        product_id: str = lid.split(":")[5]
    except IndexError:
        raise ValueError("Invalid PDS4 logical identifier.")

    return product_id


def lid_to_url(lid: str) -> str:
    """Convert PDS4 LID to URL.


    Parameters
    ----------
    lid : string
        PDS4 LID.


    Returns
    -------
    url : string

    """

    url: str
    if lid.startswith("urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated"):
        url = css_lid_to_url(lid)
    elif lid.startswith("urn:nasa:pds:gbo.ast.spacewatch.survey"):
        url = spacewatch_lid_to_url(lid)
    elif lid.startswith("urn:nasa:pds:gbo.ast.neat.survey:data_geodss"):
        url = neat_geodss_lid_to_url(lid)
    elif lid.startswith("urn:nasa:pds:gbo.ast.neat.survey:data_tricam"):
        url = neat_tricam_lid_to_url(lid)
    else:
        raise ValueError("Unsupported or invalid PDS4 logical identifier.")

    return url


def css_lid_to_url(lid: str) -> str:
    """Catalina Sky Survey LID to URL

    urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.catalina.survey/data_calibrated/G96/2021/21Apr02/G96_20210402_2B_F5Q9M2_01_0001.arch.fz

    """

    base_url: str = "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.catalina.survey/data_calibrated"

    product_id: str = get_product_id(lid)
    basename: str = product_id.upper()[:product_id.index(".")]

    telescope: str
    date: str
    YYMonDD: str
    try:
        telescope, date = basename.split("_")[:2]
        YYMonDD = f"{date[2:4]}{mm_to_Mon[date[4:6]]}{date[6:8]}"
    except IndexError:
        raise ValueError(
            f"Invalid Catalina Sky Survey PDS4 logical identifier: {lid}."
        )

    return f"{base_url}/{telescope}/{date[:4]}/{YYMonDD}/{basename}.arch.fz"


def spacewatch_lid_to_url(lid: str) -> str:
    """Spacewatch LID to URL.

    urn:nasa:pds:gbo.ast.spacewatch.survey:data:sw_0993_09.01_2003_03_23_09_18_47.001.fits
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.spacewatch.survey/data/2003/03/23/sw_0993_09.01_2003_03_23_09_18_47.001.fits

    """

    base_url: str = "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.spacewatch.survey/data"

    product_id: str = get_product_id(lid)

    year: str
    month: str
    day: str
    try:
        year, month, day = product_id.split("_")[3:6]
    except IndexError:
        raise ValueError(f"Invalid Spacewatch PDS4 logical identifier: {lid}")

    return f"{base_url}/{year}/{month}/{day}/{product_id}"


def neat_geodss_lid_to_url(lid: str) -> str:
    """NEAT GEODSS LID to URL.

    urn:nasa:pds:gbo.ast.neat.survey:data_geodss:g19960417_obsdata_960417070119d
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_geodss/g19960417/obsdata/960417070119d.fit.fz

    """

    base_url: str = "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_geodss"
    product_id: str = get_product_id(lid)

    basename: str
    directory: str
    directory, basename = product_id.rsplit("_", 1)
    directory = directory.replace("_", "/")

    return f"{base_url}/{directory}/{basename}.fit.fz"


def neat_tricam_lid_to_url(lid: str) -> str:
    """NEAT Tricam LID to URL.

    urn:nasa:pds:gbo.ast.neat.survey:data_tricam:p20011120_obsdata_20011120014036d
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_tricam/p20011120/obsdata/20011120014036d.fit.fz

    """

    base_url: str = "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_tricam"
    product_id: str = get_product_id(lid)

    basename: str
    directory: str
    directory, basename = product_id.rsplit("_", 1)
    directory = directory.replace("_", "/")

    return f"{base_url}/{directory}/{basename}.fit.fz"


def fits_to_image(hdu: fits.HDUList) -> Image:
    """Convert FITS data to PIL Image."""
    interval: ZScaleInterval = ZScaleInterval()
    scaled_data: np.ndarray = interval(hdu[0].data, clip=True) * 255
    return Image.fromarray(scaled_data.astype(np.uint8))
