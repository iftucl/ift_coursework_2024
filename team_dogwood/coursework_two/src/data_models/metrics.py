"""
Store ESG metrics data models.
"""

from pydantic import BaseModel, Field

from enum import Enum

class IndicatorUnits(Enum):
    IND_001 = "tCO2e"
    IND_002 = "tCO2e"
    IND_003 = "tCO2e"
    IND_004 = "MWh"
    IND_005 = "m³/year"
    IND_006 = "%"
    IND_007 = "Tones"
    IND_008 = "%"
    IND_009 = "Tones"


class IndicatorNames(Enum):
    IND_001 = "Scope 1 GHG Emissions"
    IND_002 = "Scope 2 GHG Emissions"
    IND_003 = "Scope 3 GHG Emissions"
    IND_004 = "Total energy consumption"
    IND_005 = "Water consumption"
    IND_006 = "Water recycled/reused"
    IND_007 = "Total waste generated"
    IND_008 = "Product packaging recyclability"
    IND_009 = "Packaging"


class IndicatorCategory(BaseModel):
    CLIMATE_EMISSIONS: list = ["IND_001", "IND_002", "IND_003"]
    ENERGY: list = ["IND_004", "IND_005", "IND_006"]
    WASTE: list = ["IND_007", "IND_009", "IND_010"]

    MAP: dict = {
        "Climate / Emissions": CLIMATE_EMISSIONS,
        "Energy": ENERGY,
        "Waste": WASTE
    }


class IndicatorList(BaseModel):
    """
    List of ESG indicators.
    """

    indicators: list["Indicator"] = Field(
        ...,
        description="List of ESG indicators.",
    )

    class Config:
        arbitrary_types_allowed = True


class Indicator(BaseModel):
    ID: str = Field(
        ...,
        description="Unique identifier for the indicator.",
    )
    name: str = Field(
        ...,
        description="Name of the indicator.",
    )
    category: str = Field(
        ...,
        description="Category of the indicator.",
    )
    company: str = Field(
        ...,
        description="Company associated with the indicator.",
    )
    year: int = Field(
        ...,
        description="Year of the report.",
    )
    figure: float = Field(
        ...,
        description="Value of the indicator.",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement for the indicator.",
    )
    data_type: str = Field(
        ...,
        description="Type of data (e.g., 'absolute', 'intensity').",
    )
