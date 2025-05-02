from modules.input.indicator_config import load_indicator_config


def test_load_indicator_config(tmp_path):
    """Test that YAML config loads correctly"""
    # 1. Create a temporary YAML file
    config_content = """
    - group_name: "Emissions"
      indicators:
        - name: "Annual CO2 Emissions"
          unit: "tonnes CO2"
    """
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content)

    # 2. Load the config
    result = load_indicator_config(config_path)

    # 3. Verify basic structure
    assert isinstance(result, list)
    assert result[0]["group_name"] == "Emissions"
    assert result[0]["indicators"][0]["name"] == "Annual CO2 Emissions"
