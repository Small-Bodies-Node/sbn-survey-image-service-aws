import os
from typing import Callable
from lid import LID

mm_to_Mon: dict[str, str] = {
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


def lid_to_url(lid: LID | str) -> str:
    """Convert PDS4 LID to URL.


    Parameters
    ----------
    lid : LID
        PDS4 LID.


    Returns
    -------
    url : string

    """

    lid: LID = LID(lid)

    get_url: dict[str, Callable] = {
        "gbo.ast.catalina.survey": css_lid_to_url,
        "gbo.ast.spacewatch.survey": spacewatch_lid_to_url,
        "gbo.ast.neat.survey": neat_lid_to_url,
        "gbo.ast.loneos.survey": loneos_lid_to_url,
    }

    return get_url[lid.bundle](lid)


def css_lid_to_url(lid: LID | str) -> str:
    """Catalina Sky Survey LID to URL

    Uses an S3 HTTPS endpoint if date is <= S3_CSS_DATE_LIMIT:

    urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch
    --> https://pds-css-archive.s3.us-west-2.amazonaws.com/sbn/gbo.ast.catalina.survey/data_calibrated/G96/2021/21Apr02/
        G96_20210402_2B_F5Q9M2_01_0001.arch.fz

    HTTP at PSI otherwise:

    urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.catalina.survey/data_calibrated/G96/2021/21Apr02/
        G96_20210402_2B_F5Q9M2_01_0001.arch.fz

    """

    s3_date_limit = os.getenv("S3_CSS_DATE_LIMIT", "00000000")

    lid: LID = LID(lid)
    basename: str = lid.product_id.upper()[: lid.product_id.index(".")]

    telescope: str
    date: str
    YYMonDD: str
    try:
        telescope, date = basename.split("_")[:2]
        YYMonDD = f"{date[2:4]}{mm_to_Mon[date[4:6]]}{date[6:8]}"
    except IndexError:
        raise ValueError(f"Invalid Catalina Sky Survey PDS4 logical identifier: {lid}.")

    base_url: str
    if date <= s3_date_limit:
        base_url = "https://pds-css-archive.s3.us-west-2.amazonaws.com/sbn/gbo.ast.catalina.survey"
    else:
        base_url = "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.catalina.survey"

    return f"{base_url}/{lid.collection}/{telescope}/{date[:4]}/{YYMonDD}/{basename}.arch.fz"


def spacewatch_lid_to_url(lid: LID | str) -> str:
    """Spacewatch LID to URL.

    urn:nasa:pds:gbo.ast.spacewatch.survey:data:sw_0993_09.01_2003_03_23_09_18_47.001.fits
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.spacewatch.survey/data/2003/03/23/
        sw_0993_09.01_2003_03_23_09_18_47.001.fits

    """

    lid: LID = LID(lid)

    base_url: str = (
        "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.spacewatch.survey/data"
    )

    year: str
    month: str
    day: str
    try:
        year, month, day = lid.product_id.split("_")[3:6]
    except IndexError:
        raise ValueError(f"Invalid Spacewatch PDS4 logical identifier: {lid}")

    return f"{base_url}/{year}/{month}/{day}/{lid.product_id}"


def neat_lid_to_url(lid: LID | str) -> str:
    """NEAT LID to URL."""

    lid: LID = LID(lid)

    get_url: dict[str, Callable] = {
        "data_geodss": neat_geodss_lid_to_url,
        "data_tricam": neat_tricam_lid_to_url,
    }

    return get_url[lid.collection](lid)


def neat_geodss_lid_to_url(lid: LID | str) -> str:
    """NEAT GEODSS LID to URL.

    urn:nasa:pds:gbo.ast.neat.survey:data_geodss:g19960417_obsdata_960417070119d
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_geodss/g19960417/obsdata/
        960417070119d.fit.fz

    """

    lid: LID = LID(lid)

    base_url: str = (
        "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_geodss"
    )

    basename: str
    directory: str
    directory, basename = lid.product_id.rsplit("_", 1)
    directory = directory.replace("_", "/")

    return f"{base_url}/{directory}/{basename}.fit.fz"


def neat_tricam_lid_to_url(lid: LID | str) -> str:
    """NEAT Tricam LID to URL.

    urn:nasa:pds:gbo.ast.neat.survey:data_tricam:p20011120_obsdata_20011120014036d
    --> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_tricam/p20011120/obsdata/
        20011120014036d.fit.fz

    """

    lid: LID = LID(lid)

    base_url: str = (
        "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_tricam"
    )

    basename: str
    directory: str
    directory, basename = lid.product_id.rsplit("_", 1)
    directory = directory.replace("_", "/")

    return f"{base_url}/{directory}/{basename}.fit.fz"


def loneos_lid_to_url(lid: LID | str) -> str:
    """LONEOS LID to URL

    urn:nasa:pds:gbo.ast.loneos.survey:data_augmented:041226_2a_082_fits
    -> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.loneos.survey/data_augmented/
        lois_3_2_0_beta/041226/041226_2a_082.fits

    urn:nasa:pds:gbo.ast.loneos.survey:data_augmented:051113_1a_011_fits
    -> https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.loneos.survey/data_augmented/
        lois_4_2_0/051113/051113_1a_011.fits

    Using the date to determine the URL:
        * Last lois_3_2_0_beta data is 041226
        * First lois 4_2_0 data is 051113

    """

    lid: LID = LID(lid)

    fn: str = lid.product_id[:-5] + ".fits"
    date: str = lid.product_id[:6]

    lois: str
    if date < "050101":
        lois = "lois_3_2_0_beta"
    else:
        lois = "lois_4_2_0"

    base_url: str = (
        "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.loneos.survey/data_augmented"
    )

    return f"{base_url}/{lois}/{date}/{fn}"
