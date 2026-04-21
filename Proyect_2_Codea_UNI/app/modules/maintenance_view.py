import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.ui.chart_theme import create_figure, style_axes
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


class MaintenanceView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        self.app_state = app_state

        self.raw_df = None
        self.df = None
        self.profile = None
        self.clean_summary = None

        # Limpieza
        self.drop_duplicates_var = tk.BooleanVar(value=True)
        self.convert_numeric_var = tk.BooleanVar(value=True)
        self.convert_dates_var = tk.BooleanVar(value=True)
        self.drop_high_null_rows_var = tk.BooleanVar(value=False)
        self.fill_numeric_var = tk.StringVar(value="None")
        self.fill_categorical_var = tk.StringVar(value="None")

        # Filtros y controles
        self.selected_device_var = tk.StringVar(value="Todos")
        self.selected_failure_var = tk.StringVar(value="Todos")
        self.sort_by_var = tk.StringVar(value="date")
        self.sort_order_var = tk.StringVar(value="Asc")
        self.metric_var = tk.StringVar(value="metric7")
        self.top_n_var = tk.StringVar(value="10")
        self.view_mode_var = tk.StringVar(value="Analisis")

        # Cache ligero
        self._cache = {
            "filtered_df": None,
            "filtered_key": None,
            "failure_series": None,
            "failure_key": None,
            "metric_effects": None,
            "metric_effects_key": None,
            "daily_failure": None,
            "daily_failure_key": None,
            "device_summary": None,
            "device_summary_key": None,
        }

        configure_treeview_style()
        self.build_ui()

    # -------------------------------------------------
    # Utilidades
    # -------------------------------------------------
    def get_palette(self):
        try:
            return self.master.master.palette
        except Exception:
            return PALETTE

    def metric_columns(self, df=None):
        source = df if df is not None else self.df
        if source is None:
            return []
        return [c for c in source.columns if str(c).lower().startswith("metric")]

    def safe_top_n(self):
        try:
            value = int(self.top_n_var.get())
            return max(3, min(value, 20))
        except Exception:
            return 10

    def clear_analysis_cache(self):
        for key in self._cache:
            self._cache[key] = None

    def format_number(self, value, decimals=2, default="N/D"):
        try:
            if pd.isna(value):
                return default
            return f"{float(value):.{decimals}f}"
        except Exception:
            return default

    def filtered_key(self):
        if self.df is None:
            return None
        return (
            id(self.df),
            self.selected_device_var.get(),
            self.selected_failure_var.get(),
            self.sort_by_var.get(),
            self.sort_order_var.get(),
        )

    def get_failure_series(self, df):
        if df is None or "failure" not in df.columns:
            return pd.Series(dtype="int64")

        cache_key = (id(df), tuple(df.columns))
        if self._cache["failure_key"] == cache_key and self._cache["failure_series"] is not None:
            return self._cache["failure_series"]

        s = df["failure"].copy()

        if pd.api.types.is_numeric_dtype(s):
            out = pd.to_numeric(s, errors="coerce").fillna(0).astype(int)
        else:
            mapped = (
                s.astype(str)
                .str.strip()
                .str.lower()
                .map(
                    {
                        "1": 1,
                        "0": 0,
                        "true": 1,
                        "false": 0,
                        "yes": 1,
                        "no": 0,
                        "si": 1,
                        "sí": 1,
                    }
                )
            )
            out = mapped.fillna(0).astype(int)

        self._cache["failure_key"] = cache_key
        self._cache["failure_series"] = out
        return out

    def get_filtered_df(self):
        if self.df is None:
            return None

        cache_key = self.filtered_key()
        if self._cache["filtered_key"] == cache_key and self._cache["filtered_df"] is not None:
            return self._cache["filtered_df"]

        df = self.df

        if "device" in df.columns and self.selected_device_var.get() != "Todos":
            df = df[df["device"].astype(str) == self.selected_device_var.get()]

        if "failure" in df.columns and self.selected_failure_var.get() != "Todos":
            failure_series = self.get_failure_series(df)
            desired = 1 if self.selected_failure_var.get() == "Con falla" else 0
            df = df[failure_series == desired]

        sort_col = self.sort_by_var.get()
        if sort_col in df.columns:
            ascending = self.sort_order_var.get() == "Asc"
            try:
                df = df.sort_values(sort_col, ascending=ascending, kind="mergesort")
            except Exception:
                pass

        self._cache["filtered_key"] = cache_key
        self._cache["filtered_df"] = df
        return df

    def classify_recent_risk(self, recent_rate, previous_rate):
        try:
            if pd.isna(recent_rate) or pd.isna(previous_rate):
                return "N/D"
            delta = recent_rate - previous_rate
            if abs(delta) < 0.0002:
                return "Estable"
            if delta > 0:
                return "Subiendo"
            return "Bajando"
        except Exception:
            return "N/D"

    def get_metric_effects(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        if df is None or df.empty or "failure" not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), tuple(df.columns))
        if self._cache["metric_effects_key"] == cache_key and self._cache["metric_effects"] is not None:
            return self._cache["metric_effects"]

        metric_cols = self.metric_columns(df)
        if not metric_cols:
            result = pd.DataFrame()
        else:
            failure = self.get_failure_series(df)
            rows = []

            for col in metric_cols:
                series = pd.to_numeric(df[col], errors="coerce")
                valid = pd.DataFrame({"metric": series, "failure": failure}).dropna()

                if valid.empty or valid["failure"].nunique() < 2:
                    continue

                fail_values = valid.loc[valid["failure"] == 1, "metric"]
                ok_values = valid.loc[valid["failure"] == 0, "metric"]

                if fail_values.empty or ok_values.empty:
                    continue

                mean_fail = fail_values.mean()
                mean_ok = ok_values.mean()
                delta = mean_fail - mean_ok
                std_ref = valid["metric"].std()
                effect = delta / std_ref if pd.notna(std_ref) and std_ref not in (0, 0.0) else 0.0

                rows.append(
                    {
                        "metric": col,
                        "mean_fail": mean_fail,
                        "mean_ok": mean_ok,
                        "delta": delta,
                        "effect_size": effect,
                        "abs_effect_size": abs(effect),
                    }
                )

            result = pd.DataFrame(rows).sort_values("abs_effect_size", ascending=False) if rows else pd.DataFrame()

        self._cache["metric_effects_key"] = cache_key
        self._cache["metric_effects"] = result
        return result

    def get_daily_failure_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        if df is None or df.empty or "failure" not in df.columns or "date" not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), "daily_failure")
        if self._cache["daily_failure_key"] == cache_key and self._cache["daily_failure"] is not None:
            return self._cache["daily_failure"]

        temp = df[["date"]].copy()
        temp["failure_num"] = self.get_failure_series(df)
        temp["date"] = pd.to_datetime(temp["date"], errors="coerce", dayfirst=True)
        temp = temp.dropna(subset=["date"])

        if temp.empty:
            result = pd.DataFrame()
        else:
            temp["day"] = temp["date"].dt.date
            grouped = temp.groupby("day").agg(
                records=("failure_num", "count"),
                failures=("failure_num", "sum"),
            ).reset_index()
            grouped["failure_rate"] = grouped["failures"] / grouped["records"]
            grouped["rolling_rate"] = grouped["failure_rate"].rolling(window=7, min_periods=2).mean()
            result = grouped

        self._cache["daily_failure_key"] = cache_key
        self._cache["daily_failure"] = result
        return result

    def get_device_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        if df is None or df.empty or "device" not in df.columns or "failure" not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), "device_summary", self.metric_var.get())
        if self._cache["device_summary_key"] == cache_key and self._cache["device_summary"] is not None:
            return self._cache["device_summary"]

        temp = df.copy()
        temp["failure_num"] = self.get_failure_series(df)

        grouped = temp.groupby("device").agg(
            records=("failure_num", "count"),
            failures=("failure_num", "sum"),
            failure_rate=("failure_num", "mean"),
        ).reset_index()

        # Criticidad compuesta: pondera conteo + tasa, evitando ruido en equipos con muy pocos registros
        grouped["criticality_score"] = (
            grouped["failures"] * 0.65
            + grouped["failure_rate"] * 100 * 0.35
        )

        metric = self.metric_var.get()
        if metric in temp.columns:
            numeric_metric = pd.to_numeric(temp[metric], errors="coerce")
            temp["_metric_num"] = numeric_metric
            metric_group = temp.groupby("device")["_metric_num"].mean().reset_index().rename(columns={"_metric_num": f"{metric}_mean"})
            grouped = grouped.merge(metric_group, on="device", how="left")

        grouped = grouped.sort_values(["criticality_score", "failures", "failure_rate"], ascending=False)
        self._cache["device_summary_key"] = cache_key
        self._cache["device_summary"] = grouped
        return grouped

    def top_metric_name(self):
        effects = self.get_metric_effects()
        if effects.empty:
            return "N/D"
        return str(effects.iloc[0]["metric"])

    def update_treeview(self, tree, dataframe, width=120, limit=30):
        tree.delete(*tree.get_children())

        cols = list(dataframe.columns)
        tree["columns"] = cols

        for col in cols:
            tree.heading(col, text=str(col))
            tree.column(col, width=width, anchor="center")

        for _, row in dataframe.head(limit).iterrows():
            values = []
            for value in row.tolist():
                if isinstance(value, float):
                    if "rate" in str(cols[len(values)]).lower():
                        values.append(f"{value * 100:.2f}%")
                    else:
                        values.append(f"{value:.3f}")
                else:
                    values.append(str(value))
            tree.insert("", "end", values=values)

    # -------------------------------------------------
    # UI
    # -------------------------------------------------
    def build_ui(self):
        palette = self.get_palette()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        make_title(header, "Maintenance Module").pack(anchor="w")
        make_subtitle(
            header,
            "Criticidad de equipos, métricas discriminantes y señal temporal de riesgo.",
        ).pack(anchor="w", pady=(4, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 10))

        make_button(actions, "Importar CSV/Excel", self.import_file).pack(side="left")
        make_button(actions, "Aplicar limpieza", self.apply_cleaning).pack(side="left", padx=10)

        self.info_label = ctk.CTkLabel(actions, text="Sin archivo cargado", text_color=palette["muted"])
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

        self.kpi_cards = {}
        labels = [
            ("failure_rate", "Tasa de falla"),
            ("critical_device", "Equipo más crítico"),
            ("signal_metric", "Métrica más discriminante"),
            ("recent_signal", "Señal reciente"),
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
            self.kpi_cards[key] = value

        self.tech_kpi_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.tech_kpi_wrap.pack(fill="x", padx=20, pady=(0, 10))
        self.tech_kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.tech_kpis = {}
        tech_labels = [
            ("rows", "Filas"),
            ("cols", "Columnas"),
            ("duplicates", "Duplicados"),
            ("nulls", "Nulos"),
        ]

        for i, (key, title_txt) in enumerate(tech_labels):
            card = make_card(self.tech_kpi_wrap)
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
        ctk.CTkOptionMenu(clean_box, values=["None", "mean", "median", "zero"], variable=self.fill_numeric_var, width=120).grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(clean_box, text="Relleno categórico", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(clean_box, values=["None", "unknown", "mode"], variable=self.fill_categorical_var, width=120).grid(row=1, column=3, padx=8, pady=6, sticky="w")

        filter_box = ctk.CTkFrame(self.prep_card, fg_color="transparent")
        filter_box.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(filter_box, text="Dispositivo", text_color=palette["muted"]).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.device_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Todos"],
            variable=self.selected_device_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.device_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Estado falla", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        self.failure_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Todos", "Con falla", "Sin falla"],
            variable=self.selected_failure_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.failure_menu.grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=4, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["date"],
            variable=self.sort_by_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.sort_menu.grid(row=0, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            filter_box,
            values=["Asc", "Desc"],
            variable=self.sort_order_var,
            command=lambda _: self.refresh_current_view(),
            width=90,
        ).grid(row=0, column=7, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica foco", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["metric1"],
            variable=self.metric_var,
            command=lambda _: self.refresh_current_view(),
        )
        self.metric_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Top N", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(
            filter_box,
            values=["5", "8", "10", "12", "15", "20"],
            variable=self.top_n_var,
            command=lambda _: self.refresh_current_view(),
            width=80,
        ).grid(row=1, column=3, padx=8, pady=6, sticky="w")

    def build_profile_section(self):
        palette = self.get_palette()

        self.profile_card = make_card(self)
        self.profile_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.profile_card,
            text="Perfil y calidad del dataset",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.profile_box = ctk.CTkTextbox(self.profile_card, height=170)
        self.profile_box.pack(fill="x", padx=12, pady=(0, 12))
        self.profile_box.insert("1.0", "Aquí aparecerá el diagnóstico del dataset.")
        self.profile_box.configure(state="disabled")

    def build_analysis_zone(self):
        palette = self.get_palette()

        self.analysis_zone = ctk.CTkFrame(self, fg_color="transparent")

        self.preview_card = make_card(self.analysis_zone)
        self.preview_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.preview_card,
            text="Vista previa filtrada",
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
            text="Dashboard de mantenimiento",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        grid = ctk.CTkFrame(self.dashboard_card, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self.time_card = make_card(grid)
        self.time_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.metric_card = make_card(grid)
        self.metric_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.device_card = make_card(grid)
        self.device_card.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.box_card = make_card(grid)
        self.box_card.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for card, txt in [
            (self.time_card, "Tendencia temporal de falla"),
            (self.metric_card, "Métricas más discriminantes"),
            (self.device_card, "Equipos críticos"),
            (self.box_card, "Comparación de métrica foco"),
        ]:
            ctk.CTkLabel(
                card,
                text=txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 6))

        self.time_frame = ctk.CTkFrame(self.time_card, fg_color="transparent")
        self.time_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.metric_frame = ctk.CTkFrame(self.metric_card, fg_color="transparent")
        self.metric_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.device_frame = ctk.CTkFrame(self.device_card, fg_color="transparent")
        self.device_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.box_frame = ctk.CTkFrame(self.box_card, fg_color="transparent")
        self.box_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.summary_card = make_card(self.analysis_zone)
        self.summary_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.summary_card,
            text="Resumen por dispositivo",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        wrap2 = ctk.CTkFrame(self.summary_card, fg_color="transparent")
        wrap2.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        wrap2.grid_rowconfigure(0, weight=1)
        wrap2.grid_columnconfigure(0, weight=1)

        self.summary_table = ttk.Treeview(wrap2, show="headings", height=12)
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
        self.report_main_box.insert("1.0", "Aquí aparecerá la lectura principal del riesgo de mantenimiento.")
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
            text="Conclusiones y acción sugerida",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.conclusion_box = ctk.CTkTextbox(self.conclusion_card, height=170)
        self.conclusion_box.pack(fill="x", padx=12, pady=(0, 12))
        self.conclusion_box.insert("1.0", "Aquí aparecerán conclusiones y apoyo para decisión.")
        self.conclusion_box.configure(state="disabled")

    # -------------------------------------------------
    # Lógica
    # -------------------------------------------------
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
            title="Selecciona archivo de Maintenance",
            filetypes=[("Datos", "*.csv *.xlsx *.xls")],
        )
        if not path:
            return

        try:
            raw_df = load_file(path)
            is_valid, missing = validate_module_file(
                raw_df,
                MODULE_CONFIG["Maintenance"]["required_columns"]
            )

            if not is_valid:
                messagebox.showerror("Archivo inválido", f"Faltan columnas requeridas: {missing}")
                return

            self.raw_df = raw_df.copy()
            self.df = raw_df.copy()
            self.profile = profile_dataframe(self.raw_df)
            self.clean_summary = None
            self.clear_analysis_cache()

            self.info_label.configure(text=os.path.basename(path))
            self.app_state.set_dataset("Maintenance", self.raw_df, self.df)

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

        self.app_state.set_dataset("Maintenance", self.raw_df, self.df)

        self.update_controls()
        self.refresh_all(initial=False)

    def update_controls(self):
        if self.df is None:
            return

        if "device" in self.df.columns:
            devices = sorted(self.df["device"].dropna().astype(str).unique().tolist())
            self.device_menu.configure(values=["Todos"] + devices[:300])
            self.selected_device_var.set("Todos")

        cols = list(self.df.columns)
        self.sort_menu.configure(values=cols)
        self.sort_by_var.set("date" if "date" in cols else cols[0])

        metric_cols = self.metric_columns(self.df)
        if metric_cols:
            self.metric_menu.configure(values=metric_cols)

            effects = self.get_metric_effects(self.df)
            if not effects.empty:
                self.metric_var.set(str(effects.iloc[0]["metric"]))
            else:
                self.metric_var.set(metric_cols[0])

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

    # -------------------------------------------------
    # Render
    # -------------------------------------------------
    def render_kpis(self):
        df = self.get_filtered_df()
        if df is None or self.profile is None:
            return

        failure_series = self.get_failure_series(df)
        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        if len(df) > 0 and len(failure_series) == len(df):
            rate = failure_series.mean() * 100
            self.kpi_cards["failure_rate"].configure(text=f"{rate:.3f}%")
        else:
            self.kpi_cards["failure_rate"].configure(text="N/D")

        device_summary = self.get_device_summary(df)
        if not device_summary.empty:
            self.kpi_cards["critical_device"].configure(text=str(device_summary.iloc[0]["device"]))
        else:
            self.kpi_cards["critical_device"].configure(text="N/D")

        effects = self.get_metric_effects(df)
        if not effects.empty:
            top = effects.iloc[0]
            self.kpi_cards["signal_metric"].configure(text=f"{top['metric']} ({top['effect_size']:+.2f})")
        else:
            self.kpi_cards["signal_metric"].configure(text="N/D")

        daily = self.get_daily_failure_summary(df)
        if not daily.empty and len(daily) >= 10:
            recent = daily["failure_rate"].tail(5).mean()
            previous = daily["failure_rate"].iloc[-10:-5].mean()
            label = self.classify_recent_risk(recent, previous)
            delta = recent - previous if pd.notna(recent) and pd.notna(previous) else None
            if delta is not None and pd.notna(delta):
                self.kpi_cards["recent_signal"].configure(text=f"{label} ({delta * 100:+.3f} pp)")
            else:
                self.kpi_cards["recent_signal"].configure(text=label)
        else:
            self.kpi_cards["recent_signal"].configure(text="N/D")

    def render_profile_box(self, initial=False):
        profile = self.profile
        if profile is None:
            return

        lines = [
            "DIAGNÓSTICO DEL DATASET",
            "",
            f"- Filas: {profile['rows']}",
            f"- Columnas: {profile['cols']}",
            f"- Duplicados detectados: {profile['duplicates']}",
            f"- Nulos totales: {profile['total_nulls']}",
            f"- Columnas numéricas detectables: {len(profile['numeric_like_cols'])}",
            f"- Columnas fecha detectables: {len(profile['date_like_cols'])}",
            f"- Columnas constantes: {len(profile['constant_columns'])}",
            "",
            "Sugerencias:",
        ]

        if profile["suggestions"]:
            lines.extend([f"  • {s}" for s in profile["suggestions"]])
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
        self.update_treeview(self.tree, preview, width=110, limit=15)

    def render_summary_table(self):
        device_summary = self.get_device_summary()
        if device_summary.empty:
            return

        metric = self.metric_var.get()
        cols = ["device", "records", "failures", "failure_rate", "criticality_score"]
        if f"{metric}_mean" in device_summary.columns:
            cols.append(f"{metric}_mean")

        table_df = device_summary[cols].copy().head(30)
        self.update_treeview(self.summary_table, table_df, width=125, limit=30)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def render_all_charts(self):
        self.render_time_chart()
        self.render_metric_effect_chart()
        self.render_device_chart()
        self.render_box_chart()

    def render_time_chart(self):
        self.clear_chart_frame(self.time_frame)
        palette = self.get_palette()
        summary = self.get_daily_failure_summary()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not summary.empty:
            ax.plot(
                summary["day"],
                summary["failure_rate"] * 100,
                color=palette["series_1"],
                linewidth=1.5,
                alpha=0.70,
                label="Tasa diaria",
            )

            if "rolling_rate" in summary.columns:
                ax.plot(
                    summary["day"],
                    summary["rolling_rate"] * 100,
                    color=palette["series_2"],
                    linewidth=2.2,
                    alpha=0.95,
                    label="Media móvil 7",
                )

            ax.set_title("Tendencia temporal de falla")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Tasa de falla (%)")

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            ax.legend()

        canvas = FigureCanvasTkAgg(fig, master=self.time_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_metric_effect_chart(self):
        self.clear_chart_frame(self.metric_frame)
        palette = self.get_palette()
        effects = self.get_metric_effects()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not effects.empty:
            top = effects.head(self.safe_top_n())
            colors = [palette["series_3"] if v >= 0 else palette["series_5"] for v in top["effect_size"]]

            ax.bar(
                top["metric"].astype(str),
                top["effect_size"],
                color=colors,
                edgecolor=palette["accent"],
                alpha=0.88,
            )
            ax.axhline(0, color=palette["chart_axis"], linewidth=1.0, alpha=0.9)
            ax.set_title("Métricas que más separan falla vs no falla")
            ax.set_ylabel("Efecto estandarizado")

            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_ha("right")

        canvas = FigureCanvasTkAgg(fig, master=self.metric_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_device_chart(self):
        self.clear_chart_frame(self.device_frame)
        palette = self.get_palette()
        summary = self.get_device_summary()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not summary.empty:
            top = summary.head(self.safe_top_n())

            bars = ax.bar(
                top["device"].astype(str),
                top["criticality_score"],
                color=palette["series_2"],
                edgecolor=palette["accent"],
                alpha=0.88,
            )

            if len(bars) > 0:
                bars[0].set_color(palette["series_5"])

            ax.set_title("Equipos críticos")
            ax.set_ylabel("Score de criticidad")

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            ax.margins(x=0.05)

        canvas = FigureCanvasTkAgg(fig, master=self.device_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_box_chart(self):
        self.clear_chart_frame(self.box_frame)
        palette = self.get_palette()
        df = self.get_filtered_df()
        metric = self.metric_var.get()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if df is not None and metric in df.columns and "failure" in df.columns:
            temp = pd.DataFrame({
                "metric": pd.to_numeric(df[metric], errors="coerce"),
                "failure_num": self.get_failure_series(df),
            }).dropna()

            if not temp.empty and temp["failure_num"].nunique() > 1:
                data_ok = temp.loc[temp["failure_num"] == 0, "metric"].values
                data_fail = temp.loc[temp["failure_num"] == 1, "metric"].values

                data = []
                labels = []

                if len(data_ok) > 0:
                    data.append(data_ok)
                    labels.append("Sin falla")
                if len(data_fail) > 0:
                    data.append(data_fail)
                    labels.append("Con falla")

                if data:
                    box = ax.boxplot(data, labels=labels, patch_artist=True)

                    for patch in box["boxes"]:
                        patch.set_facecolor(palette["series_1"])
                        patch.set_alpha(0.70)
                        patch.set_edgecolor(palette["chart_axis"])

                    for median in box["medians"]:
                        median.set_color(palette["series_2"])

                    for whisker in box["whiskers"]:
                        whisker.set_color(palette["chart_axis"])

                    for cap in box["caps"]:
                        cap.set_color(palette["chart_axis"])

                    ax.set_title(f"Comparación de {metric}")
                    ax.set_ylabel(metric)

        canvas = FigureCanvasTkAgg(fig, master=self.box_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_report_main(self):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        failure_series = self.get_failure_series(df)
        effects = self.get_metric_effects(df)
        device_summary = self.get_device_summary(df)
        daily = self.get_daily_failure_summary(df)

        lines = []

        if len(failure_series) == len(df):
            lines.append(f"Resultado principal: la tasa de falla del conjunto analizado es {failure_series.mean() * 100:.3f}%.")

        if not device_summary.empty:
            top_device = device_summary.iloc[0]
            lines.append(
                f"Equipo prioritario: {top_device['device']} lidera la criticidad con {int(top_device['failures'])} fallas y tasa de {top_device['failure_rate'] * 100:.3f}%."
            )

        if not effects.empty:
            top_metric = effects.iloc[0]
            direction = "sube" if top_metric["effect_size"] > 0 else "baja"
            lines.append(
                f"Métrica más discriminante: {top_metric['metric']} {direction} cuando aparece falla, con efecto {top_metric['effect_size']:+.2f}."
            )

        if not daily.empty and len(daily) >= 10:
            recent = daily["failure_rate"].tail(5).mean()
            previous = daily["failure_rate"].iloc[-10:-5].mean()
            trend = self.classify_recent_risk(recent, previous)
            lines.append(f"Señal temporal: el riesgo reciente está {trend.lower()} respecto al bloque previo.")

        self.report_main_box.configure(state="normal")
        self.report_main_box.delete("1.0", tk.END)
        self.report_main_box.insert("1.0", "\n".join(lines))
        self.report_main_box.configure(state="disabled")

    def render_report_chart(self):
        for child in self.report_chart_frame.winfo_children():
            child.destroy()

        palette = self.get_palette()
        summary = self.get_device_summary()

        fig = create_figure(palette, figsize=(7.2, 4.2), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if not summary.empty:
            top = summary.head(self.safe_top_n())

            bars = ax.bar(
                top["device"].astype(str),
                top["criticality_score"],
                color=palette["series_2"],
                edgecolor=palette["accent"],
                alpha=0.88,
            )

            if len(bars) > 0:
                bars[0].set_color(palette["series_5"])

            ax.set_title("Equipos críticos para priorización")
            ax.set_ylabel("Score de criticidad")

            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

            ax.margins(x=0.05)

        canvas = FigureCanvasTkAgg(fig, master=self.report_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_conclusions(self, initial=False):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        lines = []
        failure_series = self.get_failure_series(df)
        effects = self.get_metric_effects(df)
        device_summary = self.get_device_summary(df)
        metric = self.metric_var.get()

        if len(failure_series) == len(df):
            lines.append(f"- La tasa de falla observada es {failure_series.mean() * 100:.3f}%.")

        if not device_summary.empty:
            top_device = device_summary.iloc[0]
            lines.append(
                f"- El equipo con mayor criticidad actual es {top_device['device']}."
            )

        if not effects.empty:
            top_metric = effects.iloc[0]
            lines.append(
                f"- La métrica con mayor capacidad de separación es {top_metric['metric']} ({top_metric['effect_size']:+.2f})."
            )

        if metric in df.columns and "failure" in df.columns:
            temp = pd.DataFrame({
                "metric": pd.to_numeric(df[metric], errors="coerce"),
                "failure_num": self.get_failure_series(df),
            }).dropna()

            if not temp.empty and temp["failure_num"].nunique() > 1:
                mean_fail = temp.loc[temp["failure_num"] == 1, "metric"].mean()
                mean_ok = temp.loc[temp["failure_num"] == 0, "metric"].mean()

                if pd.notna(mean_fail) and pd.notna(mean_ok):
                    lines.append(f"- En {metric}, el promedio con falla es {mean_fail:.2f} y sin falla es {mean_ok:.2f}.")

        if self.profile and not self.profile["missing_df"].empty:
            top_missing = self.profile["missing_df"].iloc[0]
            lines.append(f"- La columna con más nulos es {top_missing['column']} ({int(top_missing['missing'])}).")

        if initial:
            lines.append("- Acción sugerida: validar primero la calidad del dataset y luego revisar equipos críticos y métricas discriminantes.")
        else:
            if not device_summary.empty and not effects.empty:
                lines.append(
                    f"- Acción sugerida: priorizar revisión de {device_summary.iloc[0]['device']} y vigilar especialmente {effects.iloc[0]['metric']}."
                )
            else:
                lines.append("- Acción sugerida: complementar la lectura con una revisión más específica de equipos y métricas.")

        self.conclusion_box.configure(state="normal")
        self.conclusion_box.delete("1.0", tk.END)
        self.conclusion_box.insert("1.0", "\n".join(lines))
        self.conclusion_box.configure(state="disabled")