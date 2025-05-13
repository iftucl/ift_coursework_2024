import unittest

from modules.input.postprocess import normalize_unit_and_number, postprocess_value


class TestPostprocessValueEdgeCases(unittest.TestCase):
    def test_billion_scale_gallons_to_m3(self):
        result = normalize_unit_and_number("0.5 billion gallons", "cubic meters")
        self.assertEqual(result, "1892705.0 cubic meters")

    def test_thousand_with_percent(self):
        result = normalize_unit_and_number("2 thousand percent", "%")
        self.assertEqual(result, "2000.0 %")

    def test_dash_as_na(self):
        result = postprocess_value("-", "tonnes", {})
        self.assertEqual(result["normalized"], "N/A")
        self.assertFalse(result["valid"])

    def test_empty_string_as_na(self):
        result = postprocess_value("", "MW", {})
        self.assertEqual(result["normalized"], "N/A")
        self.assertFalse(result["valid"])

    def test_unit_missing_use_expected(self):
        result = normalize_unit_and_number("1000", "MW")
        self.assertEqual(result, "1000.0 MW")

    def test_already_normalized_input(self):
        result = normalize_unit_and_number("1000.0 MW", "MW")
        self.assertEqual(result, "1000.0 MW")

    def test_percentage_without_symbol(self):
        result = normalize_unit_and_number("30 percent", "%")
        self.assertEqual(result, "30.0 %")

    def test_shorthand_m3(self):
        result = normalize_unit_and_number("1.5m3", "m³")
        self.assertEqual(result, "1.5 m³")

    def test_percent_spacing(self):
        result = normalize_unit_and_number("7.2 per cent", "%")
        self.assertEqual(result, "7.2 %")

    def test_no_unit_with_scale(self):
        result = normalize_unit_and_number("2.1 million", "tonnes")
        self.assertEqual(result, "2100000.0 tonnes")

    def test_combined_units_case_insensitive(self):
        result = normalize_unit_and_number("15 MWh", "MWh")
        self.assertEqual(result, "15.0 MWh")

    def test_zero_value(self):
        result = normalize_unit_and_number("0", "tonnes")
        self.assertEqual(result, "0.0 tonnes")

    def test_normalize_mtco2e(self):
        result = normalize_unit_and_number("11.9 million MTCO2e", "tonnes CO₂")
        self.assertEqual(result, "11900000.0 tonnes CO₂")

    def test_invalid_but_present(self):
        rules = {"max": 1000}
        result = postprocess_value("5000 MTCO2e", "tonnes CO₂", rules)
        self.assertEqual(result["normalized"], "5000.0 tonnes CO₂")
        self.assertFalse(result["valid"])

    def test_gallons_to_m3(self):
        result = normalize_unit_and_number("10.2 billion gallons", "cubic meters")
        self.assertEqual(result, "38611182.0 cubic meters")

    def test_billion_gallons_expected_m3(self):
        post = postprocess_value(
            "36 billion gallons", "cubic meters", {"min": 0, "max": 100000000000}
        )
        self.assertEqual(post["normalized"], "136274760.0 cubic meters")

    def test_non_numeric_textual(self):
        post = postprocess_value(
            "A Water Security Rating", "cubic meters", {"min": 0, "max": 100000000}
        )
        self.assertEqual(post["normalized"], "N/A")
        self.assertFalse(post["valid"])

    def test_percent_phrase(self):
        result = normalize_unit_and_number("99% renewable electricity", "%")
        self.assertEqual(result, "99.0 %")

    def test_upcycled_description(self):
        post = postprocess_value(
            "63% of manufacturing waste upcycled", "%", {"min": 0, "max": 100}
        )
        self.assertEqual(post["normalized"], "63.0%")
        self.assertTrue(post["valid"])

    def test_renewable_energy_mwh(self):
        result = normalize_unit_and_number("537,173 MWh", "MWh")
        self.assertEqual(result, "537173.0 MWh")

    def test_renewable_energy_usage_percent(self):
        result = postprocess_value("41%", "%", {"min": 0, "max": 100})
        assert result["normalized"] == "41.0%"
        assert result["valid"] is True
        assert result["warning"] is False

    def test_renewable_energy_usage_mwh(self):
        result = postprocess_value("537,173 MWh", "MWh", {"min": 0, "max": 10_000_000})
        assert result["normalized"] == "537173.0 MWh"
        assert result["valid"] is True
        assert result["warning"] is False

    def test_million_cubic_meters(self):
        result = normalize_unit_and_number("2.2 million cubic meters", "cubic meters")
        self.assertEqual(result, "2200000.0 cubic meters")

    def test_million_m3(self):
        result = normalize_unit_and_number("2.2 million m3", "cubic meters")
        self.assertEqual(result, "2200000.0 cubic meters")

    def test_million_m3_superscript(self):
        result = normalize_unit_and_number("2.2 million m³", "cubic meters")
        self.assertEqual(result, "2200000.0 cubic meters")

    def test_water_withdrawal_value(self):
        result = normalize_unit_and_number("7.5 million m³", "cubic meters")
        self.assertEqual(result, "7500000.0 cubic meters")

    def test_billion_gallons_to_m3(self):
        result = normalize_unit_and_number("1 billion gallons", "cubic meters")
        self.assertEqual(result, "3785410.0 cubic meters")

    def test_single_gallon_to_m3(self):
        result = normalize_unit_and_number("1 gallon", "cubic meters")
        self.assertEqual(result, "0.0 cubic meters")


if __name__ == "__main__":
    unittest.main()
