import pandas as pd


def load_file(filepath: str) -> pd.DataFrame:
    lower = filepath.lower()

    if lower.endswith(".csv"):
        encodings = ["utf-8", "latin-1", "cp1252"]
        separators = [",", ";"]
        last_error = None

        for enc in encodings:
            for sep in separators:
                try:
                    return pd.read_csv(filepath, encoding=enc, sep=sep)
                except Exception as exc:
                    last_error = exc

        raise ValueError(f"No se pudo leer el CSV: {last_error}")

    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(filepath)

    raise ValueError("Formato no soportado. Usa CSV o Excel.")