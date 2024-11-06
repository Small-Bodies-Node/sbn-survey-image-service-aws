from typing import Any


class LID:
    """PDS4 logical identifier."""

    def __init__(self, lid: Any) -> None:
        self._lid = str(lid)
        if not self._lid.startswith("urn:nasa:pds"):
            raise ValueError(f"Invalid PDS4 LID: {lid}")

    def __str__(self) -> str:
        return self._lid

    def __repr__(self) -> str:
        return f"<LID: {self._lid}>"

    @property
    def bundle(self) -> str:
        return self._lid.split(":")[3]

    @property
    def collection(self) -> str:
        return self._lid.split(":")[4]

    @property
    def product_id(self) -> str:
        return self._lid.split(":")[5]
