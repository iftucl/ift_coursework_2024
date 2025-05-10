"""
Store ESG report data models.
"""

from pydantic import BaseModel, Field

from typing import List, Optional
from enum import Enum

from llama_index.core import Document


class ESGReport(BaseModel):
    """
    Class for representing an ESG report.
    """
    
    pages: List[Document] = Field(
        ...,
        description="List of extracted pages in the ESG report.",
    )


class ReportKeywords(Enum):
    """
    Enum for representing keywords in the ESG report.
    """
    
    CO2_EMISSIONS = "co2 emissions"
    CARBON = "carbon"
    GREENHOUSE_GAS = "greenhouse gas"
    GHG = "ghg"
    SCOPE_1 = "scope 1"
    SCOPE_2 = "scope 2"
    SCOPE_3 = "scope 3"
    RECYCLED = "recycled"
    RECYCLING = "recycling"
    RECYCLABLE = "recyclable"
    RECYCLABILITY = "recyclability"
    RECYCLING_RATE = "recycling rate"
    GENERATED = "generated"
    WATER = "water"
    WATER_CONSUMPTION = "water consumption"
    WATER_USAGE = "water usage"
    WATER_INTENSITY = "water intensity"
    ENERGY = "energy"
    ENERGY_CONSUMPTION = "energy consumption"
    ENERGY_USAGE = "energy usage"
    RENEWABLE_ENERGY = "renewable energy"
    WASTE = "waste"
    WASTE_GENERATED = "waste generated"
    PACKAGING = "packaging"
    PACKAGING_WASTE = "packaging waste"
    PACKAGING_MATERIAL = "packaging material"
    PACKAGING_RECYCLABILITY = "packaging recyclability"
