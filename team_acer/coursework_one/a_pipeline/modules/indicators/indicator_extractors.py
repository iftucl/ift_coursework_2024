import pdfplumber
import re
import os
from rapidfuzz import fuzz
from .indicator_validators import validate_water_extraction, validate_donation_extraction, validate_waste_extraction, validate_renewable_energy_extraction, validate_air_emissions, validate_scope_emissions


class IndicatorExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    # ======================
    # Shared Helper Methods
    # ======================
    def to_mcm(self, val, unit, is_million=False):
        conversions = {
            "cubic meters": 1 / 1_000_000,
            "megaliters": 0.001,
            "liters": 1e-6,
            "gallons": 0.00378541 / 1_000_000,
            "gallons_billion": 3.78541
        }
        multiplier = 1_000_000 if is_million else 1
        return val * conversions.get(unit, 0) * multiplier
    
    def to_mt(self, val, unit):
        conversions = {
            "metric tons": 1,
            "tonnes": 1,
            "tons": 0.90718474,
            "kilograms": 0.001,
            "kg": 0.001
        }
        return val * conversions.get(unit.lower(), 0)
    
    def to_mwh(self, val, unit):
        unit = unit.lower()
        conversions = {
            "mwh": 1,
            "gwh": 1000,
            "kwh": 1/1000,
            "gj": 0.277778
        }
        return val * conversions.get(unit, 0)
    
    def to_metric_tons(self, val, unit_hint=""):
        unit_hint = unit_hint.lower().strip()
        if "kg" in unit_hint:
            return val / 1000
        if "tonnes" in unit_hint or "metric tons" in unit_hint:
            return val
        if "thousand" in unit_hint or "000" in unit_hint:
            return val * 1000
        if "megaton" in unit_hint or "mt" in unit_hint:
            return val * 1_000_000
        return val



    # ======================
    # Water Consumption
    # ======================
    def extract_water_consumption(self):
        """
        Extracts water consumption from a PDF and standardizes it to MCM.
        Returns a dict with 'value', 'unit', 'standardised_mcm', or error info.
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in reversed(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue

                    match = re.search(
                        r"(total\s+)?water\s+(consumption|use|withdraw(n|al))[^0-9]*([\d,\.]+)",
                        text,
                        re.IGNORECASE,
                    )
                    if match:
                        raw = match.group(4).replace(",", "")
                        try:
                            val = float(raw)
                        except:
                            continue

                        for unit in ["cubic meters", "megaliters", "gallons", "liters", "gallons_billion"]:
                            mcm = self.to_mcm(val, unit)
                            if validate_water_extraction(val, unit, mcm):
                                return {
                                    "value": val,
                                    "unit": unit,
                                    "standardised_mcm": round(mcm, 2)
                                }
        except Exception as e:
            print(f"❌ Extraction failed for {self.pdf_path}: {e}")

        return {
            "error": "Water data not found",
            "standardised_mcm": None
        }
    
    # ======================
    # Donations
    # ======================
    def extract_donations(self, country_code=None):

        # Mapping country codes to currency symbols
        currency_map = {
            "GB": "£", "FR": "€", "DE": "€", "IT": "€", "SP": "€",
            "CH": "CHF", "US": "$", "CA": "C$"
        }

        # Words that imply time/volunteer donations (not financial)
        non_monetary_keywords = {
            "hours", "working hours", "volunteer", "volunteering", "work hours", 
            "time", "employee hours", "man hours", "hr", "hrs", "person hours", "service hours", "skills-based"
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue

                    # First: scan for likely donation phrases
                    matches = re.findall(
                        r"(donat(ion|ed)|charitable\s+giving).*?([\d,.]+)\s*(USD|dollars|million|thousand)?",
                        text, re.IGNORECASE
                    )
                    for match in matches:
                        raw_value = re.sub(r"[^\d.]", "", match[2])
                        try:
                            val = float(raw_value)
                        except:
                            continue

                        # Look ahead: skip if followed by non-monetary context
                        match_span = text.lower().find(match[2].lower())
                        lookahead = text[match_span:match_span+40].lower()
                        if any(keyword in lookahead for keyword in non_monetary_keywords):
                            continue  # Skip time/volunteer donations

                        unit = match[3].lower() if match[3] else "usd"
                        if unit == "million":
                            val *= 1_000_000
                        elif unit == "thousand":
                            val *= 1_000

                        if validate_donation_extraction(val):
                            symbol = currency_map.get(country_code, "$")  # fallback
                            return {
                                "donation": round(val, 2),
                                "currency": symbol
                            }

                # Second: fallback using word-by-word extraction
                for page in pdf.pages:
                    words = page.extract_words()
                    for i, word in enumerate(words):
                        if "donat" in word["text"].lower():  # fuzzy keyword check
                            # Look ahead for value
                            for j in range(i + 1, min(i + 6, len(words))):
                                val_text = words[j]["text"]
                                try:
                                    val = float(re.sub(r"[^\d.]", "", val_text))
                                except:
                                    continue

                                # Look ahead for disqualifying context
                                lookahead_words = " ".join(w["text"].lower() for w in words[j+1:j+4])
                                if any(kw in lookahead_words for kw in non_monetary_keywords):
                                    continue  # skip non-financial

                                # If plausible, store
                                if validate_donation_extraction(val):
                                    symbol = currency_map.get(country_code, "$")
                                    return {
                                        "donation": round(val, 2),
                                        "currency": symbol
                                    }

        except Exception as e:
            print(f"❌ Donation extraction failed: {e}")

        return {"donation": None, "currency": None, "error": "Not found"}


    # ======================
    # Waste
    # ======================
    def extract_waste(self, target_year):
        def _extract_year_from_string(s):
            s = s.lower()
            match = re.search(r"(20\d{2})", s)
            if match:
                return int(match.group(1))
            fy_match = re.search(r"fy\s?-?(\d{2})", s)
            if fy_match:
                return 2000 + int(fy_match.group(1))
            return None

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                candidates = []

                # ----- Table-based Extraction -----
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or not any(row):
                                continue
                            joined = " ".join(str(cell).lower() for cell in row if cell)
                            year = None
                            for cell in row:
                                y = _extract_year_from_string(str(cell))
                                if y:
                                    year = y
                                    break
                            for unit in ["metric tons", "tonnes", "tons", "kg", "kilograms"]:
                                if "waste" in joined and unit in joined:
                                    for cell in row:
                                        try:
                                            val = float(str(cell).replace(",", "").strip())
                                            mt = self.to_mt(val, unit)
                                            if validate_waste_extraction(val, unit, mt):
                                                candidates.append({
                                                    "value": val,
                                                    "unit": unit,
                                                    "standardised_mt": round(mt, 2),
                                                    "year": year,
                                                    "score": 10
                                                })
                                        except:
                                            continue

                # ----- Fallback: Fuzzy Layout-based -----
                for page in reversed(pdf.pages):
                    words = page.extract_words()
                    for i, word in enumerate(words):
                        text = word["text"].lower()
                        if fuzz.partial_ratio("waste", text) >= 85:
                            year = None
                            for w in words[max(0, i-5):i+5]:
                                y = _extract_year_from_string(w["text"])
                                if y:
                                    year = y
                                    break
                            for j in range(i + 1, min(i + 6, len(words))):
                                try:
                                    val_text = words[j]["text"].replace(",", "").strip()
                                    val = float(re.sub(r"[^\d.]", "", val_text))
                                    context = " ".join(w["text"].lower() for w in words[max(0, j - 3):j + 3])
                                    for unit in ["metric tons", "tonnes", "tons", "kg", "kilograms"]:
                                        if unit in context:
                                            mt = self.to_mt(val, unit)
                                            if validate_waste_extraction(val, unit, mt):
                                                candidates.append({
                                                    "value": val,
                                                    "unit": unit,
                                                    "standardised_mt": round(mt, 2),
                                                    "year": year,
                                                    "score": 5
                                                })
                                except:
                                    continue

                if candidates:
                    filtered = [c for c in candidates if c.get("year") and c["year"] <= target_year]
                    best = max(filtered, key=lambda x: x["score"]) if filtered else max(candidates, key=lambda x: x["score"])
                    return {
                        "value": best["value"],
                        "unit": best["unit"],
                        "standardised_mt": best["standardised_mt"]
                    }

        except Exception as e:
            print(f"❌ Waste extraction failed: {e}")

        return {"standardised_mt": None, "error": "Waste data not found"}
    
    # ======================
    # Renewable Energy
    # ======================
    def extract_renewable_energy(self, target_year):
        def _extract_year_from_string(s):
            s = s.lower()
            match = re.search(r"(20\d{2})", s)
            if match:
                return int(match.group(1))
            fy_match = re.search(r"fy\s?-?(\d{2})", s)
            if fy_match:
                return 2000 + int(fy_match.group(1))
            return None

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                candidates = []

                # ----- Table-based -----
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or not any(row):
                                continue
                            row_text = " ".join(str(cell).lower() for cell in row if cell)
                            year = None
                            for cell in row:
                                y = _extract_year_from_string(str(cell))
                                if y:
                                    year = y
                                    break
                            if fuzz.partial_ratio("renewable", row_text) >= 85:
                                amount = None
                                percentage = None
                                score = 0
                                for cell in row:
                                    if not isinstance(cell, str):
                                        continue
                                    clean = cell.replace(",", "").strip()

                                    if "%" in clean or "percent" in row_text:
                                        try:
                                            pct = float(re.sub(r"[^\d.]", "", clean))
                                            if 0 <= pct <= 100:
                                                percentage = pct
                                                score += 5
                                        except:
                                            continue

                                    for unit in ["mwh", "gwh", "kwh", "gj"]:
                                        if unit in clean.lower() or unit in row_text:
                                            try:
                                                val = float(re.sub(r"[^\d.]", "", clean))
                                                mwh = self.to_mwh(val, unit)
                                                if mwh > 0:
                                                    amount = mwh
                                                    score += 10
                                            except:
                                                continue
                                if amount or percentage:
                                    candidates.append({
                                        "standardised_mwh": round(amount, 2) if amount else None,
                                        "percentage": round(percentage, 2) if percentage else None,
                                        "score": score,
                                        "year": year
                                    })

                # ----- Fallback: Text -----
                for page in reversed(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    amount_match = re.search(r"([\d,.]+)\s*(mwh|gwh|kwh|gj)", text, re.IGNORECASE)
                    pct_match = re.search(r"([\d.]+)\s*%\s*(of\s*)?(renewable|clean|green)?", text, re.IGNORECASE)

                    amount = None
                    percentage = None
                    if amount_match:
                        val = float(amount_match.group(1).replace(",", ""))
                        unit = amount_match.group(2)
                        amount = round(self.to_mwh(val, unit), 2)
                    if pct_match:
                        percentage = round(float(pct_match.group(1)), 2)

                    if amount or percentage:
                        fallback = {
                            "standardised_mwh": amount,
                            "percentage": percentage,
                            "score": 5,
                            "year": None
                        }
                        candidates.append(fallback)

                if candidates:
                    filtered = [c for c in candidates if c.get("year") and c["year"] <= target_year]
                    best = max(filtered, key=lambda x: x["score"]) if filtered else max(candidates, key=lambda x: x["score"])
                    if best and validate_renewable_energy_extraction(best):
                        return {
                            "standardised_mwh": best.get("standardised_mwh"),
                            "percentage": best.get("percentage")
                        }

        except Exception as e:
            print(f"❌ Renewable energy extraction failed: {e}")

        return {
            "standardised_mwh": None,
            "percentage": None,
            "error": "Renewable energy data not found"
        }

    
    # ======================
    # Air Emissions
    # ======================
    def extract_air_emissions(self, target_year):
        def _extract_year_from_string(s):
            s = s.lower()
            match = re.search(r"(20\d{2})", s)
            if match:
                return int(match.group(1))
            fy_match = re.search(r"fy\s?-?(\d{2})", s)
            if fy_match:
                return 2000 + int(fy_match.group(1))
            return None

        result = {"standardised_nox": None, "standardised_sox": None, "standardised_voc": None}
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                candidates = []

                # ----- Table-based -----
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or not any(row):
                                continue
                            row_text = " ".join(str(cell).lower() for cell in row if cell)
                            year = None
                            for cell in row:
                                y = _extract_year_from_string(str(cell))
                                if y:
                                    year = y
                                    break
                            record = {}
                            score = 0
                            for pollutant in ["nox", "sox", "voc"]:
                                if fuzz.partial_ratio(pollutant, row_text) >= 85:
                                    for cell in row:
                                        try:
                                            val = float(str(cell).replace(",", "").strip())
                                            if 0 < val < 1_000_000:
                                                record[f"standardised_{pollutant}"] = round(val, 2)
                                                score += 10
                                        except:
                                            continue
                            if record:
                                record["year"] = year
                                record["score"] = score
                                candidates.append(record)

                # ----- Fallback: Text-based -----
                for page in reversed(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    text = text.lower()
                    for pollutant in ["nox", "sox", "voc"]:
                        match = re.search(fr"{pollutant}[^0-9]*([\d,.]+)", text)
                        if match:
                            try:
                                val = float(match.group(1).replace(",", ""))
                                if 0 < val < 1_000_000:
                                    candidates.append({
                                        f"standardised_{pollutant}": round(val, 2),
                                        "year": None,
                                        "score": 5
                                    })
                            except:
                                continue

                if candidates:
                    filtered = [c for c in candidates if c.get("year") and c["year"] <= target_year]
                    best = max(filtered, key=lambda x: x["score"]) if filtered else max(candidates, key=lambda x: x["score"])
                    for k in result:
                        result[k] = best.get(k)
                    if validate_air_emissions(result):
                        return result

        except Exception as e:
            print(f"❌ Air emissions extraction failed: {e}")

        result["error"] = "Air emission data not found"
        return result
    
    # ======================
    # Scope Emissions
    # ======================
    def extract_scope_emissions(self, target_year):
        """
        Extracts Scope 1, 2, 3, and Total GHG emissions (in metric tons CO2e).
        - Uses table-first strategy with fuzzy label matching and scoring.
        - Filters based on year if detected; supports formats like 2020, FY20, RY-2019.
        - Falls back to text parsing if necessary.
        """

        result = {"scope_1": None, "scope_2": None, "scope_3": None, "total_emissions": None}
        fuzzy_targets = {
            "scope_1": ["scope 1", "scope i", "direct emissions"],
            "scope_2": ["scope 2", "scope ii", "indirect emissions"],
            "scope_3": ["scope 3", "scope iii", "other indirect emissions"],
            "total_emissions": ["total emissions", "ghg emissions total", "overall emissions", "total ghg"],
        }

        def _extract_year_from_string(s):
            s = s.lower()
            match = re.search(r"(20\d{2})", s)
            if match:
                return int(match.group(1))
            if "fy" in s:
                match = re.search(r"fy\s?-?(\d{2})", s)
                if match:
                    year = int(match.group(1))
                    return 2000 + year if year < 100 else year
            return None

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                candidates = []

                # -------- PHASE 1: TABLE-BASED PARSING --------
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or not any(row):
                                continue
                            row_str = [str(cell).lower() if cell else "" for cell in row]
                            combined_row = " ".join(row_str)
                            year_in_row = None

                            # Try to extract year from any cell
                            for cell in row_str:
                                detected_year = _extract_year_from_string(cell)
                                if detected_year:
                                    year_in_row = detected_year
                                    break

                            row_scores = {}
                            for key, phrases in fuzzy_targets.items():
                                for phrase in phrases:
                                    if any(fuzz.partial_ratio(phrase, cell) >= 85 for cell in row_str):
                                        for cell in row:
                                            try:
                                                raw_val = float(str(cell).replace(",", "").strip())
                                                context = combined_row + " " + str(cell).lower()
                                                val_mt = self.to_metric_tons(raw_val, context)
                                                if 0 < val_mt < 10_000_000_000:
                                                    row_scores[key] = round(val_mt, 2)
                                                    break
                                            except:
                                                continue

                            if row_scores:
                                row_scores["score"] = len(row_scores) * 10
                                row_scores["year"] = year_in_row
                                candidates.append(row_scores)

                # ✅ FILTER BY CLOSEST YEAR IF POSSIBLE
                filtered = [r for r in candidates if r.get("year") and r["year"] <= target_year]
                if filtered:
                    best = max(filtered, key=lambda x: x["score"])
                elif candidates:
                    best = max(candidates, key=lambda x: x["score"])  # fallback: best row regardless of year
                else:
                    best = None

                if best:
                    for k in result:
                        result[k] = best.get(k)
                    if validate_scope_emissions(result):
                        return result

                # -------- PHASE 2: TEXT-BASED PARSING --------
                flat_result = {}
                for page in reversed(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    text = text.lower()

                    for key, phrases in fuzzy_targets.items():
                        for phrase in phrases:
                            pattern = fr"{phrase}[^0-9\-]*([\d,.\s]+)"
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                raw = match.group(1).replace(",", "").strip()
                                try:
                                    val = float(re.sub(r"[^\d.]", "", raw))
                                    context = phrase + " " + raw
                                    val_mt = self.to_metric_tons(val, context)
                                    if 0 < val_mt < 10_000_000_000:
                                        flat_result[key] = round(val_mt, 2)
                                        break
                                except:
                                    continue

                if flat_result:
                    for k in result:
                        result[k] = flat_result.get(k)
                    if validate_scope_emissions(result):
                        return result

        except Exception as e:
            print(f"❌ Scope emissions extraction failed: {e}")

        result["error"] = "Scope emissions not found"
        return result

    # ======================
    # Main Extraction Method
    # ======================
    def extract_all(self, country, target_year):
        donation_data = self.extract_donations(country)
        return {
            "water": self.extract_water_consumption(),
            "currency": donation_data.get("currency"),
            "donation": donation_data,
            "waste": self.extract_waste(target_year),
            "renewable": self.extract_renewable_energy(target_year),
            "air": self.extract_air_emissions(target_year),
            "scope": self.extract_scope_emissions(target_year)
        }