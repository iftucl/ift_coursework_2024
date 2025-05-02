# coursework_two/modules/catalogue_loader.py
# ===============================================================
# CSR Data-Catalogue helper
# ---------------------------------------------------------------
# • load_catalogue()  →  return CSV as pandas.DataFrame
# • if the CSV does not exist, raise FileNotFoundError with hint
# ===============================================================

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

# 全局常量由 config_loader 统一维护
from modules.extract.config_loader import DATA_CATALOGUE


def load_catalogue(csv_path: Union[str, Path, None] = None) -> pd.DataFrame:
    """
    Read the CSR Data-Catalogue CSV and return it as a ``pandas.DataFrame``.

    Parameters
    ----------
    csv_path : str | pathlib.Path | None, default = None
        ▸ When *None*, fall back to ``modules.config_loader.DATA_CATALOGUE``  
        ▸ Otherwise, use the user-supplied path.

    Returns
    -------
    pandas.DataFrame
        Parsed catalogue.

    Raises
    ------
    FileNotFoundError
        If the CSV cannot be found.
    """
    path = Path(csv_path or DATA_CATALOGUE)

    if not path.exists():
        raise FileNotFoundError(
            f"Data-catalogue CSV not found: {path}\n"
            "• Check `config/conf.yaml:data_catalogue`, or\n"
            "• Pass an explicit path to load_catalogue(csv_path=…) "
            "when calling the function."
        )

    df = pd.read_csv(path)

    # ── light normalisation ─────────────────────────────────────
    # ▸ strip whitespace from column names
    df.columns = df.columns.str.strip()
    # ▸ ensure a predictable column order if you rely on it later
    #    (uncomment & edit as needed)
    # preferred_cols = ["company_name", "report_year", "file_path", ...]
    # df = df[[c for c in preferred_cols if c in df.columns]]

    return df
