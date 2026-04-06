from app.ui.styles import DEFAULT_THEME


class AppState:
    def __init__(self):
        self.current_module = "Inicio"
        self.current_theme = DEFAULT_THEME
        self.datasets = {
            "Mining": None,
            "Geology": None,
            "Metallurgy": None,
            "Maintenance": None,
        }
        self.cleaned_datasets = {
            "Mining": None,
            "Geology": None,
            "Metallurgy": None,
            "Maintenance": None,
        }

    def set_module(self, module_name: str):
        self.current_module = module_name

    def set_dataset(self, module_name: str, raw_df, clean_df):
        self.datasets[module_name] = raw_df
        self.cleaned_datasets[module_name] = clean_df

    def get_dataset(self, module_name: str):
        return self.cleaned_datasets.get(module_name)

    def set_theme(self, theme_name: str):
        self.current_theme = theme_name