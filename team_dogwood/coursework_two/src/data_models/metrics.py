"""
Store ESG metrics data models.
"""

from pydantic import BaseModel, Field


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
    report_year: int = Field(
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
