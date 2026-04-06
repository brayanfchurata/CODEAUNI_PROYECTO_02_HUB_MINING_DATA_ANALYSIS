import pandas as pd


def detect_numeric_like_columns(df: pd.DataFrame) -> list[str]:
    candidates = []
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
                candidates.append(col)
    return candidates


def detect_date_like_columns(df: pd.DataFrame) -> list[str]:
    candidates = []
    for col in df.columns:
        lower = str(col).lower()
        if "date" in lower or "fecha" in lower:
            candidates.append(col)
            continue

        if df[col].dtype == "object":
            converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if converted.notna().mean() >= 0.7:
                candidates.append(col)
    return candidates


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df) if len(df) else 1
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        pct_missing = (n_missing / total) * 100
        if n_missing > 0:
            rows.append(
                {
                    "column": col,
                    "missing": n_missing,
                    "missing_pct": round(pct_missing, 2),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["column", "missing", "missing_pct"])
    return pd.DataFrame(rows).sort_values("missing", ascending=False)


def categorical_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        if df[col].dtype == "object":
            rows.append(
                {
                    "column": col,
                    "unique_values": int(df[col].nunique(dropna=True)),
                    "top_value": df[col].mode(dropna=True).iloc[0] if not df[col].mode(dropna=True).empty else "N/D",
                }
            )
    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return pd.DataFrame()

    desc = df[numeric_cols].describe().T.reset_index().rename(columns={"index": "column"})
    return desc


def profile_dataframe(df: pd.DataFrame) -> dict:
    duplicate_count = int(df.duplicated().sum())
    total_nulls = int(df.isna().sum().sum())

    numeric_like = detect_numeric_like_columns(df)
    date_like = detect_date_like_columns(df)
    missing_df = missing_summary(df)
    categorical_df = categorical_summary(df)
    numeric_df = numeric_summary(df)

    constant_columns = [
        col for col in df.columns
        if df[col].nunique(dropna=False) <= 1
    ]

    suggestions = []
    if duplicate_count > 0:
        suggestions.append("Eliminar duplicados exactos.")
    if len(numeric_like) > 0:
        suggestions.append(f"Convertir a numerico: {', '.join(numeric_like[:6])}" + ("..." if len(numeric_like) > 6 else ""))
    if len(date_like) > 0:
        suggestions.append(f"Convertir a fecha: {', '.join(date_like[:6])}" + ("..." if len(date_like) > 6 else ""))
    if not missing_df.empty:
        suggestions.append("Revisar o imputar valores nulos en columnas criticas.")
    if constant_columns:
        suggestions.append("Existen columnas constantes que aportan poco al analisis.")

    return {
        "rows": len(df),
        "cols": df.shape[1],
        "duplicates": duplicate_count,
        "total_nulls": total_nulls,
        "numeric_like_cols": numeric_like,
        "date_like_cols": date_like,
        "constant_columns": constant_columns,
        "missing_df": missing_df,
        "categorical_df": categorical_df,
        "numeric_df": numeric_df,
        "suggestions": suggestions,
        "dtypes": df.dtypes.astype(str).to_dict(),
    }