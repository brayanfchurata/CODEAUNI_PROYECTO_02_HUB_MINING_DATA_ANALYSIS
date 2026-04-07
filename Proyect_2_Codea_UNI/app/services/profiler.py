import pandas as pd


def _sample_series(series: pd.Series, max_samples: int = 1500) -> pd.Series:
    series = series.dropna()
    if len(series) > max_samples:
        return series.sample(max_samples, random_state=42)
    return series


def detect_numeric_like_columns(df: pd.DataFrame) -> list[str]:
    candidates = []

    for col in df.columns:
        try:
            if df[col].dtype != "object":
                continue

            series = _sample_series(df[col])
            if series.empty:
                continue

            series = series.astype(str).str.strip()

            cleaned = (
                series.str.replace("\u00a0", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.replace(",", ".", regex=False)
            )

            numeric = pd.to_numeric(cleaned, errors="coerce")
            ratio = numeric.notna().mean()

            if ratio >= 0.7:
                candidates.append(col)

        except Exception:
            continue

    return candidates

def detect_date_like_columns(df):
    candidates = []

    for col in df.columns:
        try:
            lower = str(col).lower().strip()

            # Solo columnas claramente temporales
            if not any(token in lower for token in ["date", "fecha", "time", "timestamp", "datetime"]):
                continue

            series = _sample_series(df[col])
            if series.empty:
                continue

            series = series.astype(str).str.strip()

            # Intento simple y silencioso
            converted = pd.to_datetime(series, errors="coerce")
            ratio = converted.notna().mean()

            if ratio >= 0.8:
                candidates.append(col)

        except Exception:
            continue

    return candidates


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df) if len(df) else 1

    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing > 0:
            rows.append(
                {
                    "column": col,
                    "missing": n_missing,
                    "missing_pct": round((n_missing / total) * 100, 2),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["column", "missing", "missing_pct"])

    return pd.DataFrame(rows).sort_values("missing", ascending=False)


def categorical_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for col in df.columns:
        try:
            if df[col].dtype == "object":
                mode = df[col].mode(dropna=True)
                rows.append(
                    {
                        "column": col,
                        "unique_values": int(df[col].nunique(dropna=True)),
                        "top_value": mode.iloc[0] if not mode.empty else "N/D",
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return pd.DataFrame()

    try:
        return df[numeric_cols].describe().T.reset_index().rename(columns={"index": "column"})
    except Exception:
        return pd.DataFrame()


def profile_dataframe(df: pd.DataFrame) -> dict:
    duplicate_count = int(df.duplicated().sum())
    total_nulls = int(df.isna().sum().sum())

    numeric_like = detect_numeric_like_columns(df)
    date_like = detect_date_like_columns(df)
    missing_df = missing_summary(df)
    categorical_df = categorical_summary(df)
    numeric_df = numeric_summary(df)

    constant_columns = []
    for col in df.columns:
        try:
            if df[col].nunique(dropna=False) <= 1:
                constant_columns.append(col)
        except Exception:
            continue

    suggestions = []
    if duplicate_count > 0:
        suggestions.append("Eliminar duplicados exactos.")
    if len(numeric_like) > 0:
        suggestions.append(
            f"Convertir a numérico: {', '.join(numeric_like[:6])}" + ("..." if len(numeric_like) > 6 else "")
        )
    if len(date_like) > 0:
        suggestions.append(
            f"Convertir a fecha: {', '.join(date_like[:6])}" + ("..." if len(date_like) > 6 else "")
        )
    if not missing_df.empty:
        suggestions.append("Revisar o imputar valores nulos en columnas críticas.")
    if constant_columns:
        suggestions.append("Existen columnas constantes que aportan poco al análisis.")

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