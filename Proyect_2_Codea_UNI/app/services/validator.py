def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def validate_module_file(df, required_columns):
    df = normalize_columns(df)
    cols = set(df.columns)
    missing = [col for col in required_columns if col not in cols]
    return len(missing) == 0, missing