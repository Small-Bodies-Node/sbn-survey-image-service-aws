from collections.abc import Mapping

NORTH_UP_RENDERER_VERSION = "north-up-v1"


def uses_north_up_renderer(parameters: Mapping[str, str | None]) -> bool:
    """Select the versioned browse renderer only for explicitly opted-in images.

    Older clients already send align=true, so that flag alone cannot identify
    the new display contract. FITS requests always keep their native behavior.
    """
    return parameters.get("renderer") == NORTH_UP_RENDERER_VERSION and str(
        parameters.get("format", "fits")
    ).lower() in ("jpeg", "jpg", "png")
