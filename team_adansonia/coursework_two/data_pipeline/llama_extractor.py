import os
import re
import json
import asyncio
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

    An asynchronous PDF extractor that uses the LlamaParse API to extract sustainability-related

    metrics (Scope 1 and 2 emissions, energy consumption, and water usage) from a filtered corporate PDF.
 
    Attributes:

        api_key (str): LlamaParse API key.

        company_name (str): Name of the company being processed.

        filtered_pdf_path (str): Path to the filtered PDF report.
 
    """
    api_key: str = LLAMA_API_KEY
    company_name: str
    filtered_pdf_path: str

    async def process(self) -> dict:
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
        Extracts Scope 1 and Scope 2 emissions data from the PDF.
 
        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Name of the company.
 
        Returns:
            dict: Emissions data in structured JSON format.
        """
        return await self._extract_with_instruction(
            pdf_file,
            company_name,
            "Extract the following emissions metrics for all financial years available:\n"
            "- Scope 1 emissions (total)\n"
            "- Scope 2 emissions (market-based)\n"
            "- Scope 2 emissions (location-based)\n"
            "\nProvide a JSON structure like:\n"
            "{\n  \"Scope 1\": {\"2020\": [value, unit], \"2021\": [value, unit]}, ...\n}",
        )

    async def extract_energy_metrics(self, pdf_file: str, company_name: str) -> dict:
        """
        Extracts energy consumption data (total, renewable, non-renewable).
 
        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Name of the company.
 
        Returns:
            dict: Energy metrics in structured JSON format.
        """
        return await self._extract_with_instruction(
            pdf_file,
            company_name,
            "Extract the following energy metrics for all financial years available:\n"
            "- Energy consumption (total, renewable, non-renewable)\n"
            "\nProvide a JSON structure like:\n"
            "{\n  \"Total Energy\": {\"2020\": [value, unit], \"2021\": [value, unit]}, ...\n}",
        )

    async def extract_water_metrics(self, pdf_file: str, company_name: str) -> dict:
        """
        Extracts water usage or intensity data from the PDF.
 
        Args:
            pdf_file (str): Path to the PDF file.
            company_name (str): Name of the company.
 
        Returns:
            dict: Water usage data in structured JSON format.
        """
        return await self._extract_with_instruction(
            pdf_file,
            company_name,
            "Extract the following water-related metrics for all financial years available:\n"
            "- Water usage or intensity (withdrawal, consumption, or any other relevant metrics)\n"
            "\nProvide a JSON structure like:\n"
            "{\n  \"Water Usage\": {\"2020\": [value, unit], \"2021\": [value, unit]}, ...\n}",
        )

    async def _extract_with_instruction(self, pdf_file: str, company_name: str, instruction: str) -> dict:
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction=f"This is a corporate sustainability report.\n\n{instruction}",
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
            logger.error(f"Error during extraction for {company_name}: {e}")
            return {}

    def _extract_best_json_block(self, documents: list) -> dict:
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

                score = sum(
                    1 for values in data.values()
                    if isinstance(values, dict)
                    for year_val in values.values()
                    if isinstance(year_val, list) and len(year_val) == 2 and all(year_val)
                )

                if score > max_score:
                    best_data = data
                    max_score = score
                    logger.debug(f"📊 New best data found with score: {score}")

        return best_data

# Example usage
if __name__ == "__main__":
    async def main():
        company = "NVIDIA"
        pdf_path = "filtered_report.pdf"

        extractor = LlamaExtractor(
            api_key=LLAMA_API_KEY,
            company_name=company,
            filtered_pdf_path=pdf_path,
        )
        result = await extractor.process()
        print(json.dumps(result, indent=2))

    asyncio.run(main())
