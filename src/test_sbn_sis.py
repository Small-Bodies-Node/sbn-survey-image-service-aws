import pytest
import numpy as np
from sbn_sis import lid_to_url, cutout_handler


@pytest.mark.parametrize(
    "lid,expected_url",
    [
        (
            "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch",
            "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.catalina.survey/data_calibrated/G96/2021/21Apr02/G96_20210402_2B_F5Q9M2_01_0001.arch.fz",
        ),
        (
            "urn:nasa:pds:gbo.ast.spacewatch.survey:data:sw_0993_09.01_2003_03_23_09_18_47.001.fits",
            "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.spacewatch.survey/data/2003/03/23/sw_0993_09.01_2003_03_23_09_18_47.001.fits",
        ),
        (
            "urn:nasa:pds:gbo.ast.neat.survey:data_geodss:g19960417_obsdata_960417070119d",
            "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_geodss/g19960417/obsdata/960417070119d.fit.fz",
        ),
        (
            "urn:nasa:pds:gbo.ast.neat.survey:data_tricam:p20011120_obsdata_20011120014036d",
            "https://sbnarchive.psi.edu/pds4/surveys/gbo.ast.neat.survey/data_tricam/p20011120/obsdata/20011120014036d.fit.fz",
        ),
    ],
)
def test_lid_to_url(lid, expected_url):
    url = lid_to_url(lid)
    assert url == expected_url


def test_cutout_handler_css():
    lid = "urn:nasa:pds:gbo.ast.catalina.survey:data_calibrated:g96_20210402_2b_f5q9m2_01_0001.arch"
    hdu = cutout_handler(lid, 190.99166667, 23.92305556, "5 arcsec")

    assert np.all(
        hdu[0].data
        == np.array(
            [
                [19868, 18170, 18007],
                [21569, 18567, 18011],
                [22972, 18686, 18160],
            ],
            dtype=np.uint16,
        )
    )

    assert hdu[0].header["CRPIX1"] == 286.5
    assert hdu[0].header["CRPIX2"] == -274.5


def test_cutout_handler_spacewatch():
    lid = "urn:nasa:pds:gbo.ast.spacewatch.survey:data:sw_1007_38.07_2004_05_20_06_40_15.003.fits"
    hdu = cutout_handler(lid, 238.96300833, -14.47334861, "3 arcsec")

    assert np.all(
        hdu[0].data
        == np.array(
            [
                [2811.8281, 2785.9785, 2773.0547],
                [2781.0078, 2824.752, 2835.6875],
                [2766.0957, 2831.711, 2779.0195],
            ],
            dtype=np.float32,
        )
    )

    assert np.isclose(hdu[0].header["CRPIX1"], 724.34107357)
    assert np.isclose(hdu[0].header["CRPIX2"], -396.394579044)
