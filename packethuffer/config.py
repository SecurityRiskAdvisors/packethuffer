# 3rd party & native imports
from pydantic import BaseModel, Field


class XlsxConfig(BaseModel):
    """
    Stores configuration options for Excel data exports
    """

    column_names: list[str] = Field(
        description="List of columns to include in generated Excel files.",
        default=["SSID", "Security", "Additional Notes"],
    )

    column_data: list[str] = Field(
        description="Network attributes to include as rows in generated Excel files, this should map to attributes of networks in utils.py:build_network_dataframe() or PacketHuffer data exports.",
        default=["SSID", "crypt_string", "None"],
    )


class Rule(BaseModel):
    """
    Defines a PacketHuffer rule used for filtering and network identification
    """

    name: str
    condition: str
    guidance: str


class PacketHufferConfig(BaseModel):
    """
    Defines PacketHuffer Configuration Options
    """

    xlsx_format: XlsxConfig = Field(description="Configuration for Excel exports.")

    rules: list[Rule] | None = Field(
        description="List of rules for PacketHuffer filtering and network identification.",
        default=[],
    )
