import os
import csv
import pandas as pd

_FILE_CACHE = {}


def _detect_separator(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except Exception:
        return ","


def load_file(filepath: str) -> pd.DataFrame:
    lower = filepath.lower()

    # cache por ruta + fecha de modificación
    try:
        mtime = os.path.getmtime(filepath)
        cache_key = (filepath, mtime)
        if cache_key in _FILE_CACHE:
            return _FILE_CACHE[cache_key].copy()
    except Exception:
        cache_key = None

    if lower.endswith(".csv"):
        separator = _detect_separator(filepath)
        encodings = ["utf-8", "cp1252", "latin-1"]
        last_error = None

        for enc in encodings:
            try:
                df = pd.read_csv(
                    filepath,
                    encoding=enc,
                    sep=separator,
                    low_memory=False,
                )

                if cache_key is not None:
                    _FILE_CACHE.clear()
                    _FILE_CACHE[cache_key] = df.copy()

                return df

            except Exception as exc:
                last_error = exc

        raise ValueError(f"No se pudo leer el CSV: {last_error}")

    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        df = pd.read_excel(filepath)

        if cache_key is not None:
            _FILE_CACHE.clear()
            _FILE_CACHE[cache_key] = df.copy()

        return df

    raise ValueError("Formato no soportado. Usa CSV o Excel.")