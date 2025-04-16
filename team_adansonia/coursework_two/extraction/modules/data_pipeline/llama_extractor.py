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
    api_key: str = LLAMA_API_KEY
    company_name: str
    filtered_pdf_path: str

    def process(self):
        logger.info(f"🔍 Processing {self.company_name}")

        # Extract Scope emissions
        scope_data = self.extract_scope_emissions(self.filtered_pdf_path, self.company_name)
        logger.info(f"Scope data: {json.dumps(scope_data, indent=2)}")

        # Extract Energy metrics
        energy_data = self.extract_energy_metrics(self.filtered_pdf_path, self.company_name)
        logger.info(f"Energy data: {json.dumps(energy_data, indent=2)}")

        # Extract Water metrics
        water_data = self.extract_water_metrics(self.filtered_pdf_path, self.company_name)
        logger.info(f"Water data: {json.dumps(water_data, indent=2)}")

        return {
            "Scope Data": scope_data,
            "Energy Data": energy_data,
            "Water Data": water_data
        }

    def extract_scope_emissions(self, pdf_file: str, company_name: str):
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction=""" 
                This is a corporate sustainability report.

                Extract the following emissions metrics for all financial years available:
                - Scope 1 emissions (total)
                - Scope 2 emissions (market-based)
                - Scope 2 emissions (location-based)

                For each metric, provide a JSON structure like:
                {
                  "Scope 1": {
                    "2020": [value, unit],
                    "2021": [value, unit]
                  },
                  "Scope 2 (market-based)": {
                    "2020": [value, unit],
                    "2021": [value, unit]
                  },
                  "Scope 2 (location-based)": {
                    "2020": [value, unit],
                    "2021": [value, unit]
                  }
                }

                Use null when data is not reported. Return a single JSON block.
                """,
                is_formatting_instruction=True,
            )

            documents = parser.load_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )

            best_data = self._extract_best_json_block(documents)
            return best_data

        except Exception as e:
            logger.error(f"Error extracting Scope emissions data for {company_name}: {e}")
            return {}

    def extract_energy_metrics(self, pdf_file: str, company_name: str):
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction=""" 
                This is a corporate sustainability report.

                Extract the following energy metrics for all financial years available:
                - Electricity consumption (total, renewable, non-renewable)

                For each metric, provide a JSON structure like:
                {
                  "*energy metric name*": {
                    "2020": [value, unit],
                    "2021": [value, unit]
                  }
                }

                Use null when data is not reported. Return a single JSON block.
                """,
                is_formatting_instruction=True,
            )

            documents = parser.load_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )

            best_data = self._extract_best_json_block(documents)
            return best_data

        except Exception as e:
            logger.error(f"Error extracting Energy data for {company_name}: {e}")
            return {}

    def extract_water_metrics(self, pdf_file: str, company_name: str):
        try:
            parser = LlamaParse(
                api_key=self.api_key,
                result_type="markdown",
                verbose=False,
                language="en",
                num_workers=4,
                table_extraction_mode="full",
                parsing_instruction=""" 
                This is a corporate sustainability report.

                Extract the following water-related metrics for all financial years available:
                - Water usage (withdrawal, consumption, or any other relevant metrics)
                For each metric, provide a JSON structure like:
                {
                  "*water metric name*": {
                    "2020": [value, unit],
                    "2021": [value, unit]
                  }
                }

                Use null when data is not reported. Return a single JSON block.
                """,
                is_formatting_instruction=True,
            )

            documents = parser.load_data(
                pdf_file,
                extra_info={
                    "file_name": f"{company_name}.pdf",
                    "processed_date": datetime.now().isoformat(),
                },
            )

            best_data = self._extract_best_json_block(documents)
            return best_data

        except Exception as e:
            logger.error(f"Error extracting Water data for {company_name}: {e}")
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

                # Scoring block: count total [value, unit] pairs
                score = 0
                for metric, values in data.items():
                    if isinstance(values, dict):
                        for year_val in values.values():
                            if isinstance(year_val, list) and len(year_val) == 2 and all(year_val):
                                score += 1
                    elif isinstance(values, dict):  # for Scope 3 category breakdown
                        for cat, years in values.items():
                            if isinstance(years, dict):
                                for yv in years.values():
                                    if isinstance(yv, list) and len(yv) == 2 and all(yv):
                                        score += 1

                if score > max_score:
                    best_data = data
                    max_score = score
                    logger.debug(f"📊 New best data found with score: {score}")

        return best_data


# Example usage
if __name__ == "__main__":
    company = "NVIDIA"
    pdf_path = "filtered_report.pdf"

    extractor = LlamaExtractor(
        api_key="llx-4ehDkApY05QKew0EqmcFO0d43lDGF95N037gziyUve3gIZc4",
        company_name=company,
        filtered_pdf_path=pdf_path,
    )
    result = extractor.process()
    print(json.dumps(result, indent=2))
