
import sys
import os
from loguru import logger

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.data_models.company import Company, ESGReport
from src.db_utils.postgres import PostgreSQLDB

def get_all_companies(db: PostgreSQLDB) -> list[Company]:
    """
    Get all companies from the database.
    """
    companies = db.fetch("SELECT * FROM csr_reporting.company_static")
    logger.debug(f"Companies Preview: {companies[:1]}")
    if not companies:
        logger.error("No companies found in the database. Exiting.")
        exit()

    companies_list = []
    for company_data in companies[:20]:  # TODO - remove this limit
        logger.debug(f"Processing company: {company_data['security']}")
        company = Company(**company_data)
        companies_list.append(company)
    logger.info(f"Processed {len(companies_list)} companies.")

    return companies_list


def append_reports_to_companies(companies: list[Company], db: PostgreSQLDB) -> list[Company]:
    """
    Append ESG reports to each company.
    """
    for company in companies:
        logger.debug(f"Appending reports for company: {company}")
        logger.debug(f"Appending reports for company: {company.security}")
        reports = db.get_csr_reports_by_company(company.security)
        logger.debug(f"Reports for {company.security}: {reports}")
        if reports:
            for report in reports:
                esg_report = ESGReport(**report)
                company.esg_reports.append(esg_report)
            logger.info(f"Appended {len(company.esg_reports)} reports for {company.security}.")
        else:
            logger.warning(f"No reports found for {company.security}.")

    return companies