from typing import List, Optional, Union

from pydantic import BaseModel, Field
from datetime import datetime


class Company(BaseModel):
    """
    Represents a company with its associated details and ESG reports.

    This class models a company, including its stock symbol, name, sector, industry,
    location, and any associated ESG (Environmental, Social, and Governance) reports.

    :param symbol: The stock symbol of the company.
    :type symbol: str
    :param security: The name of the company.
    :type security: str
    :param gics_sector: The GICS sector of the company.
    :type gics_sector: str
    :param gics_industry: The GICS industry of the company.
    :type gics_industry: str
    :param country: The country where the company is headquartered.
    :type country: str
    :param region: The region where the company is headquartered.
    :type region: str
    :param esg_reports: A list of ESG reports associated with the company.
    :type esg_reports: List[ESGReport], optional

    Example:
        >>> company = Company(
        ...     symbol="AAPL",
        ...     security="Apple Inc.",
        ...     gics_sector="Information Technology",
        ...     gics_industry="Technology Hardware, Storage & Peripherals",
        ...     country="United States",
        ...     region="North America",
        ...     esg_reports=[]
        ... )
        >>> print(company.symbol)
        AAPL
    """

    symbol: Optional[str] = Field(None, description="The stock symbol of the company")
    security: str = Field(..., description="The name of the company")
    gics_sector: Optional[str] = Field(
        None, description="The GICS sector of the company"
    )
    gics_industry: Optional[str] = Field(
        None, description="The GICS industry of the company"
    )
    country: Optional[str] = Field(
        None, description="The country company is headquartered in"
    )
    region: Optional[str] = Field(
        None, description="The region the company is headquartered in"
    )
    esg_reports: Optional[List["ESGReport"]] = Field(
        default_factory=list, description="The ESG reports of the company"
    )


class ESGReport(BaseModel):
    """
    Represents an ESG (Environmental, Social, and Governance) report.

    This class models an ESG report, including its URL and the year it was published.

    :param url: The URL of the ESG report.
    :type url: Optional[str]
    :param year: The year the ESG report was published.
    :type year: Optional[str]

    Example:
        >>> report = ESGReport(
        ...     url="https://example.com/esg-report-2023.pdf",
        ...     year="2023",
        ...     retrieved_at="2023-10-01 12:00:00.000000"
        ... )
        >>> print(report.url)
        https://example.com/esg-report-2023.pdf
    """

    url: Optional[str] = Field(None, description="The URL of the ESG report", alias="report_url")
    year: Optional[Union[str, int]] = Field(
        None, description="The year the ESG report was published", alias="report_year"
    )
    retrieved_at: Optional[datetime] = Field(None, description="The timestamp the report was retrieved at")
