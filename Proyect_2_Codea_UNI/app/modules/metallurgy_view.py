import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.ui.chart_theme import create_figure, style_axes, style_legend
from app.core.constants import MODULE_CONFIG
from app.services.file_loader import load_file
from app.services.validator import validate_module_file
from app.services.cleaner import clean_dataframe
from app.services.profiler import profile_dataframe
from app.ui.shared_widgets import (
    make_title,
    make_subtitle,
    make_button,
    make_card,
    configure_treeview_style,
)
from app.ui.styles import PALETTE


class MetallurgyView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        self.app_state = app_state

        self.raw_df = None
        self.df = None
        self.profile = None
        self.clean_summary = None

        # Estado de limpieza
        self.drop_duplicates_var = tk.BooleanVar(value=True)
        self.convert_numeric_var = tk.BooleanVar(value=True)
        self.convert_dates_var = tk.BooleanVar(value=True)
        self.drop_high_null_rows_var = tk.BooleanVar(value=False)
        self.fill_numeric_var = tk.StringVar(value="None")
        self.fill_categorical_var = tk.StringVar(value="None")

        # Estado de interfaz
        self.metric_var = tk.StringVar(value="% Silica Concentrate")
        self.x_var = tk.StringVar(value="% Iron Concentrate")
        self.y_var = tk.StringVar(value="% Silica Concentrate")
        self.top_n_var = tk.StringVar(value="8")
        self.sort_by_var = tk.StringVar(value="date")
        self.sort_order_var = tk.StringVar(value="Asc")
        self.view_mode_var = tk.StringVar(value="Analisis")

        # Cache ligero para reducir recálculo
        self._cache = {
            "filtered_df": None,
            "filtered_key": None,
            "numeric_cols": None,
            "numeric_cols_key": None,
            "corr_series": None,
            "corr_key": None,
            "time_agg": None,
            "time_agg_key": None,
        }

        configure_treeview_style()
        self.build_ui()

    # ------------------------------------------------------------------
    # Utilidades base
    # ------------------------------------------------------------------
    def get_palette(self):
        try:
            return self.master.master.palette
        except Exception:
            return PALETTE

    def clear_analysis_cache(self):
        self._cache["filtered_df"] = None
        self._cache["filtered_key"] = None
        self._cache["numeric_cols"] = None
        self._cache["numeric_cols_key"] = None
        self._cache["corr_series"] = None
        self._cache["corr_key"] = None
        self._cache["time_agg"] = None
        self._cache["time_agg_key"] = None

    def silica_col(self):
        return "% Silica Concentrate"

    def iron_col(self):
        return "% Iron Concentrate"

    def candidate_process_cols(self):
        return [
            "Amina Flow",
            "Starch Flow",
            "Ore Pulp Density",
            "Ore Pulp pH",
            "Flotation Column 01 Air Flow",
            "Flotation Column 02 Air Flow",
            "Flotation Column 03 Air Flow",
            "Flotation Column 04 Air Flow",
        ]

    def safe_top_n(self):
        try:
            value = int(self.top_n_var.get())
            return max(3, min(value, 12))
        except Exception:
            return 8

    def safe_numeric_series(self, df, col):
        if df is None or col not in df.columns:
            return pd.Series(dtype="float64")
        return pd.to_numeric(df[col], errors="coerce")

    def filtered_key(self):
        if self.df is None:
            return None
        return (
            id(self.df),
            self.sort_by_var.get(),
            self.sort_order_var.get(),
        )

    def get_filtered_df(self):
        if self.df is None:
            return None

        cache_key = self.filtered_key()
        if self._cache["filtered_key"] == cache_key and self._cache["filtered_df"] is not None:
            return self._cache["filtered_df"]

        df = self.df

        sort_col = self.sort_by_var.get()
        ascending = self.sort_order_var.get() == "Asc"

        if sort_col in df.columns:
            try:
                filtered = df.sort_values(sort_col, ascending=ascending, kind="mergesort")
            except Exception:
                filtered = df
        else:
            filtered = df

        self._cache["filtered_key"] = cache_key
        self._cache["filtered_df"] = filtered
        return filtered

    def numeric_columns(self, df):
        if df is None:
            return []

        key = (id(df), tuple(df.columns))
        if self._cache["numeric_cols_key"] == key and self._cache["numeric_cols"] is not None:
            return self._cache["numeric_cols"]

        cols = df.select_dtypes(include=["number"]).columns.tolist()
        self._cache["numeric_cols_key"] = key
        self._cache["numeric_cols"] = cols
        return cols

    def critical_columns(self):
        cols = [self.silica_col(), self.iron_col(), "date"]
        return [c for c in cols if self.df is not None and c in self.df.columns]

    def current_metric(self):
        metric = self.metric_var.get()
        df = self.get_filtered_df()
        if df is not None and metric in df.columns:
            return metric
        return self.silica_col() if df is not None and self.silica_col() in df.columns else metric

    def get_time_agg(self, metric):
        df = self.get_filtered_df()
        if df is None or "date" not in df.columns or metric not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), metric)
        if self._cache["time_agg_key"] == cache_key and self._cache["time_agg"] is not None:
            return self._cache["time_agg"]

        temp = df[["date", metric]].copy()
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
        temp["date"] = pd.to_datetime(temp["date"], errors="coerce")
        temp = temp.dropna(subset=["date", metric])

        if temp.empty:
            result = pd.DataFrame()
        else:
            temp["day"] = temp["date"].dt.date
            result = temp.groupby("day", as_index=False)[metric].mean()
            result["rolling_5"] = result[metric].rolling(window=5, min_periods=2).mean()

        self._cache["time_agg_key"] = cache_key
        self._cache["time_agg"] = result
        return result

    def get_corr_series(self):
        df = self.get_filtered_df()
        silica_col = self.silica_col()

        if df is None or silica_col not in df.columns:
            return pd.Series(dtype="float64")

        cache_key = (id(df), silica_col)
        if self._cache["corr_key"] == cache_key and self._cache["corr_series"] is not None:
            return self._cache["corr_series"]

        numeric_cols = self.numeric_columns(df)
        if silica_col not in numeric_cols or len(numeric_cols) < 2:
            result = pd.Series(dtype="float64")
        else:
            valid_cols = []
            for col in numeric_cols:
                try:
                    if df[col].notna().sum() < 20:
                        continue
                    if df[col].nunique(dropna=True) <= 1:
                        continue
                    valid_cols.append(col)
                except Exception:
                    continue

            if silica_col not in valid_cols or len(valid_cols) < 2:
                result = pd.Series(dtype="float64")
            else:
                try:
                    corr = df[valid_cols].corr(numeric_only=True)[silica_col].dropna()
                    corr = corr.drop(labels=[silica_col], errors="ignore")

                    # Favorecer columnas de proceso útiles, sin impedir otras
                    ordered = []
                    preferred = [c for c in self.candidate_process_cols() if c in corr.index]
                    remaining = [c for c in corr.index if c not in preferred]
                    ordered = preferred + remaining
                    corr = corr.loc[ordered].sort_values(key=lambda s: s.abs(), ascending=False)
                    result = corr
                except Exception:
                    result = pd.Series(dtype="float64")

        self._cache["corr_key"] = cache_key
        self._cache["corr_series"] = result
        return result

    def format_number(self, value, decimals=2, default="N/D"):
        try:
            if pd.isna(value):
                return default
            return f"{float(value):.{decimals}f}"
        except Exception:
            return default

    def classify_stability(self, std_value):
        try:
            if pd.isna(std_value):
                return "N/D"
            if std_value <= 0.35:
                return "Alta"
            if std_value <= 0.75:
                return "Media"
            return "Baja"
        except Exception:
            return "N/D"

    def classify_trend(self, recent_mean, previous_mean):
        try:
            if pd.isna(recent_mean) or pd.isna(previous_mean):
                return "N/D"
            delta = recent_mean - previous_mean
            if abs(delta) < 0.03:
                return "Estable"
            if delta > 0:
                return "Empeorando"
            return "Mejorando"
        except Exception:
            return "N/D"

    def rolling_variability(self, metric):
        df = self.get_time_agg(metric)
        if df.empty or metric not in df.columns:
            return pd.Series(dtype="float64")

        temp = df[[metric]].copy()
        temp["window_std"] = temp[metric].rolling(window=5, min_periods=3).std()
        return temp["window_std"].dropna()

    def update_treeview(self, tree, dataframe, width=120, height_limit=30):
        tree.delete(*tree.get_children())
        cols = list(dataframe.columns)
        tree["columns"] = cols

        for col in cols:
            tree.heading(col, text=str(col))
            tree.column(col, width=width, anchor="center")

        for _, row in dataframe.head(height_limit).iterrows():
            values = []
            for v in row.tolist():
                if isinstance(v, float):
                    values.append(f"{v:.3f}")
                else:
                    values.append(str(v))
            tree.insert("", "end", values=values)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def build_ui(self):
        palette = self.get_palette()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        make_title(header, "Metallurgy Module").pack(anchor="w")
        make_subtitle(
            header,
            "Control de calidad del concentrado, estabilidad del proceso y lectura accionable para decisión.",
        ).pack(anchor="w", pady=(4, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 10))

        make_button(actions, "Importar CSV/Excel", self.import_file).pack(side="left")
        make_button(actions, "Aplicar limpieza", self.apply_cleaning).pack(side="left", padx=10)

        self.info_label = ctk.CTkLabel(
            actions,
            text="Sin archivo cargado",
            text_color=palette["muted"],
        )
        self.info_label.pack(side="left", padx=8)

        mode_box = ctk.CTkFrame(actions, fg_color="transparent")
        mode_box.pack(side="right")

        ctk.CTkLabel(mode_box, text="Vista", text_color=palette["muted"]).pack(side="left", padx=(0, 6))
        ctk.CTkSegmentedButton(
            mode_box,
            values=["Analisis", "Reporte"],
            variable=self.view_mode_var,
            command=lambda _: self.toggle_mode(),
        ).pack(side="left")

        self.build_kpi_section()
        self.build_prep_section()
        self.build_profile_section()
        self.build_analysis_zone()
        self.build_report_zone()

        self.toggle_mode()

    def build_kpi_section(self):
        palette = self.get_palette()

        self.kpi_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_wrap.pack(fill="x", padx=20, pady=(0, 10))
        self.kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.main_kpis = {}
        labels = [
            ("silica", "Sílice promedio"),
            ("iron", "Hierro promedio"),
            ("stability", "Estabilidad sílice"),
            ("trend", "Tendencia reciente"),
        ]

        for i, (key, title_txt) in enumerate(labels):
            card = make_card(self.kpi_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            ctk.CTkLabel(
                card,
                text=title_txt,
                text_color=palette["muted"],
            ).pack(anchor="w", padx=12, pady=(10, 2))

            value = ctk.CTkLabel(
                card,
                text="-",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=palette["text"],
                wraplength=220,
                justify="left",
            )
            value.pack(anchor="w", padx=12, pady=(0, 10))
            self.main_kpis[key] = value

        self.tech_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.tech_wrap.pack(fill="x", padx=20, pady=(0, 10))
        self.tech_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.tech_kpis = {}
        tech_labels = [
            ("rows", "Filas"),
            ("cols", "Columnas"),
            ("duplicates", "Duplicados"),
            ("nulls", "Nulos"),
        ]

        for i, (key, title_txt) in enumerate(tech_labels):
            card = make_card(self.tech_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            ctk.CTkLabel(
                card,
                text=title_txt,
                text_color=palette["muted"],
            ).pack(anchor="w", padx=12, pady=(10, 2))

            value = ctk.CTkLabel(
                card,
                text="-",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=palette["text"],
            )
            value.pack(anchor="w", padx=12, pady=(0, 10))
            self.tech_kpis[key] = value

    def build_prep_section(self):
        palette = self.get_palette()

        self.prep_card = make_card(self)
        self.prep_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.prep_card,
            text="Preparación del análisis",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        clean_box = ctk.CTkFrame(self.prep_card, fg_color="transparent")
        clean_box.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkCheckBox(clean_box, text="Eliminar duplicados", variable=self.drop_duplicates_var).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        ctk.CTkCheckBox(clean_box, text="Convertir numéricos", variable=self.convert_numeric_var).grid(row=0, column=1, padx=8, pady=6, sticky="w")
        ctk.CTkCheckBox(clean_box, text="Convertir fechas", variable=self.convert_dates_var).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkCheckBox(clean_box, text="Quitar filas muy nulas", variable=self.drop_high_null_rows_var).grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(clean_box, text="Relleno numérico", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            clean_box,
            values=["None", "mean", "median", "zero"],
            variable=self.fill_numeric_var,
            width=120,
        ).grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(clean_box, text="Relleno categórico", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            clean_box,
            values=["None", "unknown", "mode"],
            variable=self.fill_categorical_var,
            width=120,
        ).grid(row=1, column=3, padx=8, pady=6, sticky="w")

        filter_box = ctk.CTkFrame(self.prep_card, fg_color="transparent")
        filter_box.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["date"],
            variable=self.sort_by_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.sort_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            filter_box,
            values=["Asc", "Desc"],
            variable=self.sort_order_var,
            command=lambda _: self.refresh_current_view(),
            width=90,
        ).grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable X", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.x_menu = ctk.CTkOptionMenu(
            filter_box,
            values=[self.iron_col()],
            variable=self.x_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.x_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable Y", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        self.y_menu = ctk.CTkOptionMenu(
            filter_box,
            values=[self.silica_col()],
            variable=self.y_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.y_menu.grid(row=1, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica principal", text_color=palette["muted"]).grid(row=1, column=4, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(
            filter_box,
            values=[self.silica_col()],
            variable=self.metric_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.metric_menu.grid(row=1, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Top N", text_color=palette["muted"]).grid(row=1, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            filter_box,
            values=["4", "6", "8", "10", "12"],
            variable=self.top_n_var,
            command=lambda _: self.refresh_current_view(),
            width=80,
        ).grid(row=1, column=7, padx=8, pady=6, sticky="w")

    def build_profile_section(self):
        palette = self.get_palette()

        self.profile_card = make_card(self)
        self.profile_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.profile_card,
            text="Estado del dataset",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.profile_box = ctk.CTkTextbox(self.profile_card, height=155)
        self.profile_box.pack(fill="x", padx=12, pady=(0, 12))
        self.profile_box.insert("1.0", "Aquí aparecerá el diagnóstico y la calidad del dataset.")
        self.profile_box.configure(state="disabled")

    def build_analysis_zone(self):
        palette = self.get_palette()

        self.analysis_zone = ctk.CTkFrame(self, fg_color="transparent")

        self.preview_card = make_card(self.analysis_zone)
        self.preview_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.preview_card,
            text="Vista previa operativa",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        wrap = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(wrap, show="headings", height=12)
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.dashboard_card = make_card(self.analysis_zone)
        self.dashboard_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.dashboard_card,
            text="Dashboard metalúrgico",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        grid = ctk.CTkFrame(self.dashboard_card, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self.scatter_card = make_card(grid)
        self.scatter_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.line_card = make_card(grid)
        self.line_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.bar_card = make_card(grid)
        self.bar_card.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.stability_card = make_card(grid)
        self.stability_card.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for card, title_txt in [
            (self.scatter_card, "Hierro vs sílice"),
            (self.line_card, "Tendencia temporal de sílice"),
            (self.bar_card, "Variables más asociadas a sílice"),
            (self.stability_card, "Estabilidad del proceso"),
        ]:
            ctk.CTkLabel(
                card,
                text=title_txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 6))

        self.scatter_frame = ctk.CTkFrame(self.scatter_card, fg_color="transparent")
        self.scatter_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.line_frame = ctk.CTkFrame(self.line_card, fg_color="transparent")
        self.line_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bar_frame = ctk.CTkFrame(self.bar_card, fg_color="transparent")
        self.bar_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.stability_frame = ctk.CTkFrame(self.stability_card, fg_color="transparent")
        self.stability_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.summary_card = make_card(self.analysis_zone)
        self.summary_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.summary_card,
            text="Resumen operativo crítico",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        wrap2 = ctk.CTkFrame(self.summary_card, fg_color="transparent")
        wrap2.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        wrap2.grid_rowconfigure(0, weight=1)
        wrap2.grid_columnconfigure(0, weight=1)

        self.summary_table = ttk.Treeview(wrap2, show="headings", height=10)
        self.summary_table.grid(row=0, column=0, sticky="nsew")

        sb2 = ttk.Scrollbar(wrap2, orient="vertical", command=self.summary_table.yview)
        sb2.grid(row=0, column=1, sticky="ns")
        self.summary_table.configure(yscrollcommand=sb2.set)

    def build_report_zone(self):
        palette = self.get_palette()

        self.report_zone = ctk.CTkFrame(self, fg_color="transparent")

        self.report_main_card = make_card(self.report_zone)
        self.report_main_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.report_main_card,
            text="Lectura principal para decisión",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.report_main_box = ctk.CTkTextbox(self.report_main_card, height=130)
        self.report_main_box.pack(fill="x", padx=12, pady=(0, 12))
        self.report_main_box.insert("1.0", "Aquí aparecerá la lectura principal del proceso.")
        self.report_main_box.configure(state="disabled")

        self.report_chart_card = make_card(self.report_zone)
        self.report_chart_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.report_chart_card,
            text="Visual principal de soporte",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.report_chart_frame = ctk.CTkFrame(self.report_chart_card, fg_color="transparent")
        self.report_chart_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.conclusion_card = make_card(self.report_zone)
        self.conclusion_card.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            self.conclusion_card,
            text="Conclusiones y recomendación",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.conclusion_box = ctk.CTkTextbox(self.conclusion_card, height=170)
        self.conclusion_box.pack(fill="x", padx=12, pady=(0, 12))
        self.conclusion_box.insert("1.0", "Aquí aparecerán conclusiones y acción sugerida.")
        self.conclusion_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # Flujo principal
    # ------------------------------------------------------------------
    def toggle_mode(self):
        if self.view_mode_var.get() == "Analisis":
            self.report_zone.pack_forget()
            self.analysis_zone.pack(fill="both", expand=True, pady=(0, 0))
        else:
            self.analysis_zone.pack_forget()
            self.report_zone.pack(fill="both", expand=True, pady=(0, 0))

        if self.df is not None:
            self.refresh_current_view()

    def import_file(self):
        path = filedialog.askopenfilename(
            title="Selecciona archivo de Metallurgy",
            filetypes=[("Datos", "*.csv *.xlsx *.xls")],
        )
        if not path:
            return

        try:
            raw_df = load_file(path)
            is_valid, missing = validate_module_file(
                raw_df,
                MODULE_CONFIG["Metallurgy"]["required_columns"],
            )

            if not is_valid:
                messagebox.showerror(
                    "Archivo inválido",
                    f"Faltan columnas requeridas: {missing}",
                )
                return

            self.raw_df = raw_df.copy()
            self.df = raw_df.copy()
            self.profile = profile_dataframe(self.raw_df)
            self.clean_summary = None
            self.clear_analysis_cache()

            self.info_label.configure(text=os.path.basename(path))
            self.app_state.set_dataset("Metallurgy", self.raw_df, self.df)

            self.update_controls()
            self.refresh_all(initial=True)

        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def apply_cleaning(self):
        if self.raw_df is None:
            messagebox.showwarning("Aviso", "Primero carga un archivo.")
            return

        options = {
            "drop_duplicates": self.drop_duplicates_var.get(),
            "convert_numeric": self.convert_numeric_var.get(),
            "convert_dates": self.convert_dates_var.get(),
            "drop_high_null_rows": self.drop_high_null_rows_var.get(),
            "fill_numeric_nulls": None if self.fill_numeric_var.get() == "None" else self.fill_numeric_var.get(),
            "fill_categorical_nulls": None if self.fill_categorical_var.get() == "None" else self.fill_categorical_var.get(),
        }

        self.df, self.clean_summary = clean_dataframe(self.raw_df, options)
        self.profile = profile_dataframe(self.df)
        self.clear_analysis_cache()

        self.app_state.set_dataset("Metallurgy", self.raw_df, self.df)

        self.update_controls()
        self.refresh_all(initial=False)

    def update_controls(self):
        if self.df is None or self.df.empty:
            return

        cols = list(self.df.columns)
        self.sort_menu.configure(values=cols)
        self.sort_by_var.set("date" if "date" in cols else cols[0])

        num_cols = self.numeric_columns(self.df)
        if num_cols:
            self.x_menu.configure(values=num_cols)
            self.y_menu.configure(values=num_cols)
            self.metric_menu.configure(values=num_cols)

            default_x = self.iron_col() if self.iron_col() in num_cols else num_cols[0]
            default_y = self.silica_col() if self.silica_col() in num_cols else num_cols[min(1, len(num_cols) - 1)]
            default_metric = self.silica_col() if self.silica_col() in num_cols else num_cols[0]

            self.x_var.set(default_x)
            self.y_var.set(default_y)
            self.metric_var.set(default_metric)

    def refresh_all(self, initial=False):
        if self.df is None:
            return

        self.render_kpis()
        self.render_profile_box(initial=initial)

        if self.view_mode_var.get() == "Analisis":
            self.render_preview_table()
            self.render_summary_table()
            self.render_all_charts()
        else:
            self.render_report_main()
            self.render_report_chart()
            self.render_conclusions(initial=initial)

    def refresh_current_view(self):
        if self.df is None:
            return

        self.clear_analysis_cache()
        self.render_kpis()

        if self.view_mode_var.get() == "Analisis":
            self.render_preview_table()
            self.render_summary_table()
            self.render_all_charts()
        else:
            self.render_report_main()
            self.render_report_chart()
            self.render_conclusions(initial=False)

    # ------------------------------------------------------------------
    # Render de texto y tablas
    # ------------------------------------------------------------------
    def render_kpis(self):
        df = self.get_filtered_df()
        if df is None or self.profile is None:
            return

        silica_col = self.silica_col()
        iron_col = self.iron_col()

        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        silica_mean = self.safe_numeric_series(df, silica_col).mean() if silica_col in df.columns else None
        iron_mean = self.safe_numeric_series(df, iron_col).mean() if iron_col in df.columns else None
        silica_std = self.safe_numeric_series(df, silica_col).std() if silica_col in df.columns else None

        self.main_kpis["silica"].configure(text=self.format_number(silica_mean))
        self.main_kpis["iron"].configure(text=self.format_number(iron_mean))
        self.main_kpis["stability"].configure(
            text=f"{self.classify_stability(silica_std)} ({self.format_number(silica_std)})"
            if silica_col in df.columns else "N/D"
        )

        trend_text = "N/D"
        if silica_col in df.columns:
            series = self.safe_numeric_series(df, silica_col).dropna()
            if len(series) >= 10:
                recent = series.tail(5).mean()
                previous = series.iloc[-10:-5].mean()
                label = self.classify_trend(recent, previous)
                delta = recent - previous if pd.notna(recent) and pd.notna(previous) else None
                if delta is not None and pd.notna(delta):
                    trend_text = f"{label} ({delta:+.2f})"
                else:
                    trend_text = label
        self.main_kpis["trend"].configure(text=trend_text)

    def render_profile_box(self, initial=False):
        if self.profile is None:
            return

        lines = [
            "Diagnóstico general del dataset",
            "",
            f"- Filas: {self.profile['rows']}",
            f"- Columnas: {self.profile['cols']}",
            f"- Duplicados detectados: {self.profile['duplicates']}",
            f"- Nulos totales: {self.profile['total_nulls']}",
            f"- Columnas numéricas detectables: {len(self.profile['numeric_like_cols'])}",
            f"- Columnas fecha detectables: {len(self.profile['date_like_cols'])}",
            f"- Columnas constantes: {len(self.profile['constant_columns'])}",
            "",
            "Lectura de calidad:",
        ]

        critical = self.critical_columns()
        if self.df is not None and critical:
            for col in critical:
                try:
                    missing = int(self.df[col].isna().sum())
                    pct = (missing / len(self.df)) * 100 if len(self.df) > 0 else 0
                    lines.append(f"  • {col}: {missing} faltantes ({pct:.2f}%)")
                except Exception:
                    continue

        lines.extend(["", "Sugerencias automáticas:"])
        if self.profile["suggestions"]:
            lines.extend([f"  • {item}" for item in self.profile["suggestions"]])
        else:
            lines.append("  • No se detectaron problemas relevantes.")

        if not initial and self.clean_summary:
            lines.extend([
                "",
                "Resultado de la limpieza:",
                f"  • Filas originales: {self.clean_summary['rows_original']}",
                f"  • Filas finales: {self.clean_summary['rows_clean']}",
                f"  • Nulos originales: {self.clean_summary['nulls_original']}",
                f"  • Nulos finales: {self.clean_summary['nulls_final']}",
                f"  • Duplicados removidos: {self.clean_summary['actions']['duplicates_removed']}",
            ])

        self.profile_box.configure(state="normal")
        self.profile_box.delete("1.0", tk.END)
        self.profile_box.insert("1.0", "\n".join(lines))
        self.profile_box.configure(state="disabled")

    def render_preview_table(self):
        df = self.get_filtered_df()
        if df is None:
            return
        preview = df.head(15).copy()
        self.update_treeview(self.tree, preview, width=115, height_limit=15)

    def render_summary_table(self):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        silica_col = self.silica_col()
        iron_col = self.iron_col()

        ordered_cols = [silica_col, iron_col] + self.candidate_process_cols()
        ordered_cols = [c for c in ordered_cols if c in df.columns]

        if not ordered_cols:
            return

        rows = []
        for col in ordered_cols:
            s = pd.to_numeric(df[col], errors="coerce")
            if s.notna().sum() == 0:
                continue

            rows.append({
                "Variable": col,
                "Media": s.mean(),
                "DesvStd": s.std(),
                "P25": s.quantile(0.25),
                "P75": s.quantile(0.75),
                "Max": s.max(),
            })

        summary = pd.DataFrame(rows)
        if summary.empty:
            return

        self.update_treeview(self.summary_table, summary, width=130, height_limit=20)

    # ------------------------------------------------------------------
    # Render de charts
    # ------------------------------------------------------------------
    def render_all_charts(self):
        self.render_scatter_chart()
        self.render_line_chart()
        self.render_bar_chart()
        self.render_stability_chart()

    def render_scatter_chart(self):
        self.clear_chart_frame(self.scatter_frame)

        df = self.get_filtered_df()
        palette = self.get_palette()
        x = self.x_var.get()
        y = self.y_var.get()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if df is not None and {x, y}.issubset(df.columns):
            sample = df[[x, y]].copy()
            sample[x] = pd.to_numeric(sample[x], errors="coerce")
            sample[y] = pd.to_numeric(sample[y], errors="coerce")
            sample = sample.dropna().head(2500)

            if not sample.empty:
                ax.scatter(
                    sample[x],
                    sample[y],
                    s=18,
                    alpha=0.70,
                    color=palette["series_1"],
                    edgecolors="none",
                    label="Muestras",
                )

                corr_value = sample[[x, y]].corr(numeric_only=True).iloc[0, 1]
                ax.set_title(f"{x} vs {y} | Corr: {corr_value:.3f}")
                ax.set_xlabel(x)
                ax.set_ylabel(y)
                style_legend(ax, palette)

        canvas = FigureCanvasTkAgg(fig, master=self.scatter_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_line_chart(self):
        self.clear_chart_frame(self.line_frame)

        palette = self.get_palette()
        silica_col = self.silica_col()
        agg = self.get_time_agg(silica_col)

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not agg.empty and silica_col in agg.columns:
            ax.plot(
                agg["day"],
                agg[silica_col],
                color=palette["series_1"],
                linewidth=1.8,
                alpha=0.75,
                label="Promedio diario",
            )

            if "rolling_5" in agg.columns:
                ax.plot(
                    agg["day"],
                    agg["rolling_5"],
                    color=palette["series_2"],
                    linewidth=2.3,
                    alpha=0.95,
                    label="Media móvil 5",
                )

            mean_value = agg[silica_col].mean()
            if pd.notna(mean_value):
                ax.axhline(
                    mean_value,
                    color=palette["series_5"],
                    linestyle="--",
                    linewidth=1.4,
                    alpha=0.85,
                    label=f"Media ({mean_value:.2f})",
                )

            ax.set_title("Evolución temporal de sílice")
            ax.set_xlabel("Fecha")
            ax.set_ylabel(silica_col)

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            style_legend(ax, palette)

        canvas = FigureCanvasTkAgg(fig, master=self.line_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_bar_chart(self):
        self.clear_chart_frame(self.bar_frame)

        palette = self.get_palette()
        corr = self.get_corr_series().head(self.safe_top_n())

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not corr.empty:
            colors = []
            for value in corr.values:
                colors.append(palette["series_3"] if value >= 0 else palette["series_5"])

            bars = ax.bar(
                corr.index.astype(str),
                corr.values,
                color=colors,
                edgecolor=palette["accent"],
                alpha=0.88,
            )

            ax.axhline(0, color=palette["chart_axis"], linewidth=1.1, alpha=0.9)
            ax.set_title(f"Top {len(corr)} variables asociadas a sílice")
            ax.set_ylabel("Correlación")

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            if len(bars) > 0:
                ax.margins(x=0.05)

        canvas = FigureCanvasTkAgg(fig, master=self.bar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_stability_chart(self):
        self.clear_chart_frame(self.stability_frame)

        palette = self.get_palette()
        silica_col = self.silica_col()
        variability = self.rolling_variability(silica_col)

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not variability.empty:
            ax.plot(
                variability.index,
                variability.values,
                color=palette["series_3"],
                linewidth=2.0,
                alpha=0.92,
            )

            mean_std = variability.mean()
            if pd.notna(mean_std):
                ax.axhline(
                    mean_std,
                    color=palette["series_2"],
                    linestyle="--",
                    linewidth=1.4,
                    alpha=0.9,
                )

            ax.set_title("Variabilidad móvil de sílice")
            ax.set_xlabel("Ventanas sucesivas")
            ax.set_ylabel("Std móvil")

        canvas = FigureCanvasTkAgg(fig, master=self.stability_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Reporte ejecutivo
    # ------------------------------------------------------------------
    def render_report_main(self):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        silica_col = self.silica_col()
        iron_col = self.iron_col()
        corr = self.get_corr_series()

        lines = []

        if silica_col in df.columns:
            silica = self.safe_numeric_series(df, silica_col)
            lines.append(f"Resultado principal: la sílice promedio del concentrado se ubica en {self.format_number(silica.mean())}.")
            lines.append(f"Comportamiento del proceso: la estabilidad actual de sílice es {self.classify_stability(silica.std())}.")

            if len(silica.dropna()) >= 10:
                recent = silica.dropna().tail(5).mean()
                previous = silica.dropna().iloc[-10:-5].mean()
                trend = self.classify_trend(recent, previous)
                delta = recent - previous if pd.notna(recent) and pd.notna(previous) else None
                if delta is not None and pd.notna(delta):
                    lines.append(f"Lectura reciente: la sílice muestra una tendencia {trend.lower()} con variación de {delta:+.2f} frente al bloque previo.")

        if iron_col in df.columns:
            iron = self.safe_numeric_series(df, iron_col)
            lines.append(f"Soporte de calidad: el hierro promedio en concentrado es {self.format_number(iron.mean())}.")

        if not corr.empty:
            top_var = corr.index[0]
            top_corr = corr.iloc[0]
            sign_text = "directa" if top_corr >= 0 else "inversa"
            lines.append(
                f"Señal dominante: la variable más asociada a sílice es {top_var} con relación {sign_text} ({top_corr:.3f})."
            )

        self.report_main_box.configure(state="normal")
        self.report_main_box.delete("1.0", tk.END)
        self.report_main_box.insert("1.0", "\n".join(lines))
        self.report_main_box.configure(state="disabled")

    def render_report_chart(self):
        for child in self.report_chart_frame.winfo_children():
            child.destroy()

        palette = self.get_palette()
        silica_col = self.silica_col()
        agg = self.get_time_agg(silica_col)

        fig = create_figure(palette, figsize=(7.2, 4.3), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not agg.empty and silica_col in agg.columns:
            ax.plot(
                agg["day"],
                agg[silica_col],
                color=palette["series_1"],
                linewidth=1.8,
                alpha=0.75,
                label="Promedio diario",
            )

            if "rolling_5" in agg.columns:
                ax.plot(
                    agg["day"],
                    agg["rolling_5"],
                    color=palette["series_2"],
                    linewidth=2.4,
                    alpha=0.95,
                    label="Media móvil 5",
                )

            mean_value = agg[silica_col].mean()
            if pd.notna(mean_value):
                ax.axhline(
                    mean_value,
                    color=palette["series_5"],
                    linestyle="--",
                    linewidth=1.4,
                    alpha=0.90,
                    label=f"Media ({mean_value:.2f})",
                )

            ax.set_title("Visual principal: evolución de sílice")
            ax.set_xlabel("Fecha")
            ax.set_ylabel(silica_col)

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            style_legend(ax, palette)

        canvas = FigureCanvasTkAgg(fig, master=self.report_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_conclusions(self, initial=False):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        silica_col = self.silica_col()
        iron_col = self.iron_col()
        x = self.x_var.get()
        y = self.y_var.get()

        lines = []
        corr = self.get_corr_series()

        # Lectura principal
        if silica_col in df.columns:
            silica = self.safe_numeric_series(df, silica_col)
            silica_mean = silica.mean()
            silica_std = silica.std()
            lines.append(f"- La sílice promedio actual es {self.format_number(silica_mean)} y su estabilidad se clasifica como {self.classify_stability(silica_std)}.")

        if iron_col in df.columns:
            iron = self.safe_numeric_series(df, iron_col)
            lines.append(f"- El hierro promedio en concentrado es {self.format_number(iron.mean())}.")

        # Relación operativa
        if {x, y}.issubset(df.columns):
            temp = df[[x, y]].copy()
            temp[x] = pd.to_numeric(temp[x], errors="coerce")
            temp[y] = pd.to_numeric(temp[y], errors="coerce")
            temp = temp.dropna()

            if len(temp) >= 10:
                corr_xy = temp[[x, y]].corr(numeric_only=True).iloc[0, 1]
                if abs(corr_xy) >= 0.7:
                    strength = "fuerte"
                elif abs(corr_xy) >= 0.4:
                    strength = "moderada"
                else:
                    strength = "débil"
                lines.append(f"- La relación entre {x} y {y} es {strength} ({corr_xy:.3f}).")

        # Variable de vigilancia
        if not corr.empty:
            top_var = corr.index[0]
            top_value = corr.iloc[0]
            if top_value >= 0:
                lines.append(f"- La variable a vigilar primero es {top_var}, porque aumenta junto con la sílice ({top_value:.3f}).")
            else:
                lines.append(f"- La variable a vigilar primero es {top_var}, porque se mueve en sentido inverso a la sílice ({top_value:.3f}).")

        # Calidad del dato
        if self.profile and not self.profile["missing_df"].empty:
            critical_missing = self.profile["missing_df"]
            critical_missing = critical_missing[critical_missing["column"].isin(self.critical_columns())]
            if not critical_missing.empty:
                top_missing = critical_missing.iloc[0]
                lines.append(
                    f"- La principal alerta de calidad está en {top_missing['column']}, con {int(top_missing['missing'])} faltantes."
                )

        # Acción sugerida
        if initial:
            lines.append("- Acción sugerida: revisar el diagnóstico del dataset antes de tomar decisiones operativas definitivas.")
        else:
            action = "- Acción sugerida: "
            if silica_col in df.columns:
                silica = self.safe_numeric_series(df, silica_col).dropna()
                if len(silica) >= 10:
                    recent = silica.tail(5).mean()
                    previous = silica.iloc[-10:-5].mean()
                    trend = self.classify_trend(recent, previous)

                    if trend == "Empeorando":
                        action += "priorizar revisión de las variables más asociadas a sílice y validar estabilidad reciente del proceso."
                    elif trend == "Mejorando":
                        action += "mantener seguimiento de la señal dominante y confirmar que la mejora se sostenga en próximas ventanas."
                    else:
                        action += "mantener control sobre estabilidad de sílice y revisar desvíos puntuales más que cambios estructurales."
                else:
                    action += "complementar esta lectura con más datos para validar tendencia reciente."
            else:
                action += "validar primero la disponibilidad de columnas críticas para una lectura confiable."

            lines.append(action)

        self.conclusion_box.configure(state="normal")
        self.conclusion_box.delete("1.0", tk.END)
        self.conclusion_box.insert("1.0", "\n".join(lines))
        self.conclusion_box.configure(state="disabled")