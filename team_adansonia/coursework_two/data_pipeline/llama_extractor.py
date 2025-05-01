"""
LlamaExtractor module for parsing sustainability reports using the LlamaParse API.

This module defines an asynchronous class to extract key environmental metrics
such as Scope emissions, energy consumption, and water usage from PDF reports.

Requires: llama-parse, loguru, pydantic, dotenv
"""

import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from llama_parse import LlamaParse
from loguru import logger
from pydantic import BaseModel

# Load environment variables
load_dotenv()
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")


class LlamaExtractor(BaseModel):
    """
    Asynchronous extractor for sustainability metrics using LlamaParse.

    Attributes:
        api_key (str): LlamaParse API key.
        company_name (str): Name of the company being analyzed.
        filtered_pdf_path (str): Path to the filtered PDF file.
    """

    api_key: str = LLAMA_API_KEY
    company_name: str
    filtered_pdf_path: str

    async def process(self) -> dict:
        """
        Asynchronously processes the PDF and extracts sustainability metrics.

        Returns:
            dict: A dictionary containing the following keys:
                - "Scope Data"
                - "Energy Data"
                - "Water Data"
        """
        logger.info(f"🔍 Processing {self.company_name}")

        scope_data = await self.extract_scope_emissions(self.filtered_pdf_path, self.company_name)
        logger.info(f"Scope data: {json.dumps(scope_data, indent=2)}")

        energy_data = await self.extract_energy_metrics(self.filtered_pdf_path, self.company_name)
        logger.info(f"Energy data: {json.dumps(energy_data, indent=2)}")

        water_data = await self.extract_water_metrics(self.filtered_pdf_path, self.company_name)
        logger.info(f"Water data: {json.dumps(water_data, indent=2)}")

        return {
            "Scope Data": scope_data,
            "Energy Data": energy_data,
            "Water Data": water_data,
        }

    async def extract_scope_emissions(self, pdf_file: str, company_name: str) -> dict:
        """
        Extracts Scope 1 and Scope 2 emissions data from a PDF.

        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Company name for logging and context.

        Returns:
            dict: Extracted emissions data, or an empty dictionary on failure.
        """
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction="""...""",  # abbreviated for clarity
                is_formatting_instruction=True,
            )

            documents = await parser.aload_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )
            return self._extract_best_json_block(documents)

        except Exception as e:
            logger.error(f"Error extracting Scope emissions for {company_name}: {e}")
            return {}

    async def extract_energy_metrics(self, pdf_file: str, company_name: str) -> dict:
        """
        Extracts energy consumption metrics from a PDF.

        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Company name for logging and context.

        Returns:
            dict: Extracted energy data, or an empty dictionary on failure.
        """
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction="""...""",  # abbreviated for clarity
                is_formatting_instruction=True,
            )

            documents = await parser.aload_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )
            return self._extract_best_json_block(documents)

        except Exception as e:
            logger.error(f"Error extracting Energy data for {company_name}: {e}")
            return {}

    async def extract_water_metrics(self, pdf_file: str, company_name: str) -> dict:
        """
        Extracts water usage metrics from a PDF.

        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Company name for logging and context.

        Returns:
            dict: Extracted water usage data, or an empty dictionary on failure.
        """
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction="""...""",  # abbreviated for clarity
                is_formatting_instruction=True,
            )

            documents = await parser.aload_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )
            return self._extract_best_json_block(documents)

        except Exception as e:
            logger.error(f"Error extracting Water data for {company_name}: {e}")
            return {}

    def _extract_best_json_block(self, documents: list) -> dict:
        """
        Extracts the most complete JSON block from a list of documents.

        Args:
            documents (list): LlamaParse output containing document content.

        Returns:
            dict: Most complete structured data block found in the documents.
        """
        code_fence_pattern = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)
        best_data = {}
        max_score = 0

        for doc in documents:
            content = doc.get_content()
            if not content:
                continue

            json_blocks = code_fence_pattern.findall(content)
            for block in json_blocks:
                try:
                    data = json.loads(block.strip())
                except Exception as exc:
                    logger.warning(f"Failed to parse JSON block: {exc}")
                    continue

                # Score completeness of data
                score = 0
                for metric, values in data.items():
                    if isinstance(values, dict):
                        for year_val in values.values():
                            if isinstance(year_val, list) and len(year_val) == 2 and all(year_val):
                                score += 1

                if score > max_score:
                    best_data = data
                    max_score = score
                    logger.debug(f"📊 New best data found with score: {score}")

        return best_data


# Example usage (non-async fallback for testing)
if __name__ == "__main__":
    company = "NVIDIA"
    pdf_path = "filtered_report.pdf"

    extractor = LlamaExtractor(
        api_key=LLAMA_API_KEY,
        company_name=company,
        filtered_pdf_path=pdf_path,
    )
    result = extractor.process()  # This will return a coroutine
    print("NOTE: Use asyncio.run(...) to run 'process' asynchronously.")
