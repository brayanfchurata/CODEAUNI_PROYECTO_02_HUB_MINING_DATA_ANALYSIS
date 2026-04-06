import pandas as pd


def clean_dataframe(df: pd.DataFrame, options: dict | None = None) -> tuple[pd.DataFrame, dict]:
    if options is None:
        options = {
            "drop_duplicates": True,
            "convert_numeric": True,
            "convert_dates": True,
            "drop_high_null_rows": False,
            "fill_numeric_nulls": None,        # None | "mean" | "median" | "zero"
            "fill_categorical_nulls": None,    # None | "unknown" | "mode"
        }

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    original_rows = len(df)
    original_nulls = int(df.isna().sum().sum())
    original_duplicates = int(df.duplicated().sum())

    actions = {
        "duplicates_removed": 0,
        "numeric_converted": [],
        "date_converted": [],
        "rows_removed_high_nulls": 0,
        "numeric_nulls_filled": [],
        "categorical_nulls_filled": [],
    }

    if options.get("drop_duplicates", False):
        before = len(df)
        df = df.drop_duplicates().copy()
        actions["duplicates_removed"] = before - len(df)

    if options.get("convert_numeric", False):
        for col in df.columns:
            if df[col].dtype == "object":
                series = df[col].astype(str).str.strip()
                cleaned = (
                    series.str.replace("\u00a0", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.replace(r"(?<=\d),(?=\d)", ".", regex=True)
                )
                numeric = pd.to_numeric(cleaned, errors="coerce")
                if numeric.notna().mean() >= 0.7:
                    df[col] = numeric
                    actions["numeric_converted"].append(col)

    if options.get("convert_dates", False):
        for col in df.columns:
            lower = col.lower()
            if "date" in lower or "fecha" in lower or df[col].dtype == "object":
                converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                if converted.notna().mean() >= 0.7:
                    df[col] = converted
                    actions["date_converted"].append(col)

    if options.get("drop_high_null_rows", False):
        before = len(df)
        threshold = max(1, int(df.shape[1] * 0.5))
        df = df[df.isna().sum(axis=1) < threshold].copy()
        actions["rows_removed_high_nulls"] = before - len(df)

    fill_num = options.get("fill_numeric_nulls")
    if fill_num:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols:
            if df[col].isna().any():
                if fill_num == "mean":
                    value = df[col].mean()
                elif fill_num == "median":
                    value = df[col].median()
                elif fill_num == "zero":
                    value = 0
                else:
                    value = None

                if value is not None:
                    df[col] = df[col].fillna(value)
                    actions["numeric_nulls_filled"].append(col)

    fill_cat = options.get("fill_categorical_nulls")
    if fill_cat:
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        for col in cat_cols:
            if df[col].isna().any():
                if fill_cat == "unknown":
                    value = "Desconocido"
                elif fill_cat == "mode":
                    mode = df[col].mode(dropna=True)
                    value = mode.iloc[0] if not mode.empty else "Desconocido"
                else:
                    value = None

                if value is not None:
                    df[col] = df[col].fillna(value)
                    actions["categorical_nulls_filled"].append(col)

    summary = {
        "rows_original": original_rows,
        "rows_clean": len(df),
        "nulls_original": original_nulls,
        "nulls_final": int(df.isna().sum().sum()),
        "duplicates_original": original_duplicates,
        "actions": actions,
    }

    return df, summary