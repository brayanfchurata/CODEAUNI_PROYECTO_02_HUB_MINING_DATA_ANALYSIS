import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import numpy as np
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


class MiningView(ctk.CTkScrollableFrame):
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

        # Controles
        self.operator_var = tk.StringVar(value="Todos")
        self.shift_var = tk.StringVar(value="Todos")
        self.metric_var = tk.StringVar(value="ton")
        self.sort_by_var = tk.StringVar(value="operator")
        self.sort_order_var = tk.StringVar(value="Desc")
        self.top_n_var = tk.StringVar(value="6")
        self.view_mode_var = tk.StringVar(value="Analisis")

        self._cache = {
            "filtered_df": None,
            "filtered_key": None,
            "daily_summary": None,
            "daily_key": None,
            "operator_summary": None,
            "operator_key": None,
            "bench_summary": None,
            "bench_key": None,
            "compliance_daily": None,
            "compliance_key": None,
            "loss_summary": None,
            "loss_key": None,
        }

        configure_treeview_style()
        self.build_ui()

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def get_palette(self):
        try:
            return self.master.master.palette
        except Exception:
            return PALETTE

    def clear_analysis_cache(self):
        for key in self._cache:
            self._cache[key] = None

    def safe_top_n(self):
        try:
            n = int(self.top_n_var.get())
            return max(3, min(n, 15))
        except Exception:
            return 6

    def time_col(self):
        return "tiempo_perforacion (min)"

    def volume_col(self):
        return "M3_volado"

    def ton_col(self):
        return "ton"

    def grade_col(self):
        return "ley"

    def delay_col(self):
        return "demora"

    def total_height_col(self):
        return "altura_perforación_total"

    def real_height_col(self):
        return "altura_perforación_real"

    def bench_col(self):
        return "bench"

    def drill_date_col(self):
        for col in ["drilling_date", "blasting_date", "date", "fecha"]:
            if self.df is not None and col in self.df.columns:
                return col
        return None

    def format_number(self, value, decimals=2, default="N/D"):
        try:
            if pd.isna(value):
                return default
            return f"{float(value):.{decimals}f}"
        except Exception:
            return default

    def to_numeric_col(self, df, col):
        if df is None or col not in df.columns:
            return pd.Series(dtype="float64")
        return pd.to_numeric(df[col], errors="coerce")

    def normalize_operator(self, value):
        if pd.isna(value):
            return value
        return str(value).strip().upper().replace(" ", "")

    def metric_label(self):
        metric = self.metric_var.get()
        return metric if metric in [self.ton_col(), self.volume_col()] else self.ton_col()

    def efficiency_series(self, df):
        metric = self.metric_label()
        prod = self.to_numeric_col(df, metric)
        time_s = self.to_numeric_col(df, self.time_col())

        valid = time_s > 0
        result = pd.Series(index=df.index, dtype="float64")
        result.loc[valid] = prod.loc[valid] / time_s.loc[valid]
        return result

    def compliance_series(self, df):
        total_col = self.total_height_col()
        real_col = self.real_height_col()
        if df is None or total_col not in df.columns or real_col not in df.columns:
            return pd.Series(dtype="float64")

        total = self.to_numeric_col(df, total_col)
        real = self.to_numeric_col(df, real_col)
        valid = total > 0

        result = pd.Series(index=df.index, dtype="float64")
        result.loc[valid] = (real.loc[valid] / total.loc[valid]) * 100
        return result

    def filtered_key(self):
        if self.df is None:
            return None
        return (
            id(self.df),
            self.operator_var.get(),
            self.shift_var.get(),
            self.sort_by_var.get(),
            self.sort_order_var.get(),
            self.metric_var.get(),
        )

    def get_filtered_df(self):
        if self.df is None:
            return None

        cache_key = self.filtered_key()
        if self._cache["filtered_key"] == cache_key and self._cache["filtered_df"] is not None:
            return self._cache["filtered_df"]

        df = self.df.copy()

        if "operator" in df.columns:
            df["_operator_norm"] = df["operator"].apply(self.normalize_operator)

        if "operator" in df.columns and self.operator_var.get() != "Todos":
            selected = self.normalize_operator(self.operator_var.get())
            df = df[df["_operator_norm"] == selected].copy()

        if "shift" in df.columns and self.shift_var.get() != "Todos":
            df = df[df["shift"].astype(str) == self.shift_var.get()].copy()

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

    def get_daily_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        date_col = self.drill_date_col()

        if df is None or df.empty or date_col is None:
            return pd.DataFrame()

        cache_key = (id(df), date_col, self.metric_label())
        if self._cache["daily_key"] == cache_key and self._cache["daily_summary"] is not None:
            return self._cache["daily_summary"]

        metric = self.metric_label()

        temp = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True),
            "metric": self.to_numeric_col(df, metric),
            "time": self.to_numeric_col(df, self.time_col()),
        }).dropna(subset=["date", "metric"])

        if temp.empty:
            result = pd.DataFrame()
        else:
            temp["day"] = temp["date"].dt.date
            result = temp.groupby("day").agg(
                records=("metric", "count"),
                productivity=("metric", "mean"),
                perf_time=("time", "mean"),
            ).reset_index()
            result["efficiency"] = result["productivity"] / result["perf_time"].replace(0, np.nan)
            result["rolling_productivity"] = result["productivity"].rolling(window=7, min_periods=2).mean()

        self._cache["daily_key"] = cache_key
        self._cache["daily_summary"] = result
        return result

    def get_operator_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        if df is None or df.empty or "operator" not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), self.metric_label())
        if self._cache["operator_key"] == cache_key and self._cache["operator_summary"] is not None:
            return self._cache["operator_summary"]

        metric = self.metric_label()
        temp = df.copy()
        temp["_operator_norm"] = temp["operator"].apply(self.normalize_operator)
        temp["_metric_num"] = self.to_numeric_col(temp, metric)
        temp["_time_num"] = self.to_numeric_col(temp, self.time_col())

        grouped = temp.groupby("_operator_norm").agg(
            records=("_metric_num", "count"),
            productivity=("_metric_num", "mean"),
            time_avg=("_time_num", "mean"),
        ).reset_index()

        grouped["efficiency"] = grouped["productivity"] / grouped["time_avg"].replace(0, np.nan)
        grouped = grouped.rename(columns={"_operator_norm": "operator"})
        grouped = grouped.sort_values(["productivity", "efficiency"], ascending=False)

        self._cache["operator_key"] = cache_key
        self._cache["operator_summary"] = grouped
        return grouped

    def get_bench_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        bench_col = self.bench_col()
        if df is None or df.empty or bench_col not in df.columns:
            return pd.DataFrame()

        cache_key = (id(df), self.metric_label(), bench_col)
        if self._cache["bench_key"] == cache_key and self._cache["bench_summary"] is not None:
            return self._cache["bench_summary"]

        metric = self.metric_label()
        temp = df.copy()
        temp["_metric_num"] = self.to_numeric_col(temp, metric)
        temp["_time_num"] = self.to_numeric_col(temp, self.time_col())

        grouped = temp.groupby(bench_col).agg(
            records=("_metric_num", "count"),
            productivity=("_metric_num", "mean"),
            time_avg=("_time_num", "mean"),
        ).reset_index()

        grouped = grouped[grouped["records"] >= 80].copy()
        if grouped.empty:
            result = pd.DataFrame()
        else:
            grouped["efficiency"] = grouped["productivity"] / grouped["time_avg"].replace(0, np.nan)
            result = grouped.sort_values(["productivity", "efficiency"], ascending=False)

        self._cache["bench_key"] = cache_key
        self._cache["bench_summary"] = result
        return result

    def get_compliance_daily(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        date_col = self.drill_date_col()

        if df is None or df.empty or date_col is None:
            return pd.DataFrame()

        cache_key = (id(df), date_col, self.total_height_col(), self.real_height_col())
        if self._cache["compliance_key"] == cache_key and self._cache["compliance_daily"] is not None:
            return self._cache["compliance_daily"]

        compliance = self.compliance_series(df)
        temp = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True),
            "compliance": compliance,
        }).dropna(subset=["date", "compliance"])

        if temp.empty:
            result = pd.DataFrame()
        else:
            temp["day"] = temp["date"].dt.date
            result = temp.groupby("day").agg(
                records=("compliance", "count"),
                compliance=("compliance", "mean"),
            ).reset_index()
            result["rolling_compliance"] = result["compliance"].rolling(window=7, min_periods=2).mean()

        self._cache["compliance_key"] = cache_key
        self._cache["compliance_daily"] = result
        return result

    def get_loss_summary(self, df=None):
        df = df if df is not None else self.get_filtered_df()
        if df is None or df.empty:
            return pd.DataFrame()

        cache_key = (id(df), self.metric_label())
        if self._cache["loss_key"] == cache_key and self._cache["loss_summary"] is not None:
            return self._cache["loss_summary"]

        metric = self.metric_label()
        temp = pd.DataFrame({
            "time": self.to_numeric_col(df, self.time_col()),
            "delay": self.to_numeric_col(df, self.delay_col()) if self.delay_col() in df.columns else np.nan,
            "productivity": self.to_numeric_col(df, metric),
        }).dropna(subset=["productivity"])

        rows = []

        if not temp["time"].dropna().empty:
            corr_time = temp[["time", "productivity"]].dropna().corr(numeric_only=True).iloc[0, 1]
            rows.append({
                "Factor": "Tiempo perforación",
                "Relacion": corr_time,
                "Lectura": "Penaliza" if corr_time < 0 else "Acompaña",
            })

        if "delay" in temp.columns and temp["delay"].notna().sum() > 0:
            corr_delay = temp[["delay", "productivity"]].dropna().corr(numeric_only=True).iloc[0, 1]
            rows.append({
                "Factor": "Demora",
                "Relacion": corr_delay,
                "Lectura": "Penaliza" if corr_delay < 0 else "Acompaña",
            })

        result = pd.DataFrame(rows)
        self._cache["loss_key"] = cache_key
        self._cache["loss_summary"] = result
        return result

    def render_chart_placeholder(self, frame, title, subtitle="No hay datos suficientes para esta visual."):
        self.clear_chart_frame(frame)
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        ax.set_xticks([])
        ax.set_yticks([])

        ax.text(
            0.5, 0.58, title,
            ha="center", va="center",
            fontsize=12, fontweight="bold",
            color=palette["text"],
            transform=ax.transAxes
        )
        ax.text(
            0.5, 0.46, subtitle,
            ha="center", va="center",
            fontsize=10,
            color=palette["muted"],
            transform=ax.transAxes
        )

        for spine in ax.spines.values():
            spine.set_color(palette["border"])

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

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

        make_title(header, "Mining Module").pack(anchor="w")
        make_subtitle(
            header,
            "Productividad, operadores, bancos y cumplimiento de perforación.",
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
        self.build_status_section()
        self.build_analysis_zone()
        self.build_report_zone()

        self.toggle_mode()

    def build_kpi_section(self):
        palette = self.get_palette()

        self.kpi_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_wrap.pack(fill="x", padx=20, pady=(0, 10))
        self.kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.main_kpis = {}
        main_labels = [
            ("productivity", "Productividad promedio"),
            ("leader", "Operador benchmark"),
            ("bench_perf", "Banco destacado"),
            ("efficiency", "Eficiencia operativa"),
        ]

        for i, (key, title_txt) in enumerate(main_labels):
            card = make_card(self.kpi_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            ctk.CTkLabel(card, text=title_txt, text_color=palette["muted"]).pack(anchor="w", padx=12, pady=(10, 2))
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

            ctk.CTkLabel(card, text=title_txt, text_color=palette["muted"]).pack(anchor="w", padx=12, pady=(10, 2))
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

        ctk.CTkLabel(filter_box, text="Operador", text_color=palette["muted"]).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.operator_menu = ctk.CTkOptionMenu(filter_box, values=["Todos"], variable=self.operator_var, command=lambda _: self.refresh_current_view())
        self.operator_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Turno", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        self.shift_menu = ctk.CTkOptionMenu(filter_box, values=["Todos"], variable=self.shift_var, command=lambda _: self.refresh_current_view())
        self.shift_menu.grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=4, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(filter_box, values=["operator"], variable=self.sort_by_var, command=lambda _: self.refresh_current_view())
        self.sort_menu.grid(row=0, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["Asc", "Desc"], variable=self.sort_order_var, command=lambda _: self.refresh_current_view(), width=90).grid(row=0, column=7, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica principal", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(filter_box, values=[self.ton_col()], variable=self.metric_var, command=lambda _: self.refresh_current_view())
        self.metric_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Top N", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["5", "6", "8", "10", "12"], variable=self.top_n_var, command=lambda _: self.refresh_current_view(), width=80).grid(row=1, column=3, padx=8, pady=6, sticky="w")

    def build_status_section(self):
        palette = self.get_palette()

        self.status_card = make_card(self)
        self.status_card.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.status_card,
            text="Estado operativo y calidad del dataset",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.status_box = ctk.CTkTextbox(self.status_card, height=160)
        self.status_box.pack(fill="x", padx=12, pady=(0, 12))
        self.status_box.insert("1.0", "Aquí aparecerá el estado de la operación, alertas y cambios aplicados.")
        self.status_box.configure(state="disabled")

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
            text="Panel de productividad minera",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        grid = ctk.CTkFrame(self.dashboard_card, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self.time_card = make_card(grid)
        self.time_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.operator_card = make_card(grid)
        self.operator_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.bench_card = make_card(grid)
        self.bench_card.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.compliance_card = make_card(grid)
        self.compliance_card.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for card, txt in [
            (self.time_card, "Productividad en el tiempo"),
            (self.operator_card, "Ranking de operadores"),
            (self.bench_card, "Desempeño por banco"),
            (self.compliance_card, "Cumplimiento de perforación"),
        ]:
            ctk.CTkLabel(
                card,
                text=txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 6))

        self.time_frame = ctk.CTkFrame(self.time_card, fg_color="transparent")
        self.time_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.operator_frame = ctk.CTkFrame(self.operator_card, fg_color="transparent")
        self.operator_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bench_frame = ctk.CTkFrame(self.bench_card, fg_color="transparent")
        self.bench_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.compliance_frame = ctk.CTkFrame(self.compliance_card, fg_color="transparent")
        self.compliance_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.summary_card = make_card(self.analysis_zone)
        self.summary_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.summary_card,
            text="Resumen operativo por indicador",
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
        self.report_main_box.insert("1.0", "Aquí aparecerá la lectura principal de productividad.")
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
        self.conclusion_box.insert("1.0", "Aquí aparecerán conclusiones para la decisión operativa.")
        self.conclusion_box.configure(state="disabled")

    def toggle_mode(self):
        if self.view_mode_var.get() == "Analisis":
            self.report_zone.pack_forget()
            self.analysis_zone.pack(fill="both", expand=True, pady=(0, 0))
        else:
            self.analysis_zone.pack_forget()
            self.report_zone.pack(fill="both", expand=True, pady=(0, 0))

        if self.df is not None:
            self.refresh_current_view()

    # -------------------------------------------------
    # Data flow
    # -------------------------------------------------
    def import_file(self):
        path = filedialog.askopenfilename(
            title="Selecciona archivo de Mining",
            filetypes=[("Datos", "*.csv *.xlsx *.xls")],
        )
        if not path:
            return

        try:
            raw_df = load_file(path)
            is_valid, missing = validate_module_file(
                raw_df,
                MODULE_CONFIG["Mining"]["required_columns"]
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
            self.app_state.set_dataset("Mining", self.raw_df, self.df)

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

        self.app_state.set_dataset("Mining", self.raw_df, self.df)

        self.update_controls()
        self.refresh_all(initial=False)

    def update_controls(self):
        if self.df is None:
            return

        cols = list(self.df.columns)
        self.sort_menu.configure(values=cols)
        self.sort_by_var.set("operator" if "operator" in cols else cols[0])

        metric_candidates = [c for c in [self.ton_col(), self.volume_col()] if c in cols]
        if metric_candidates:
            self.metric_menu.configure(values=metric_candidates)
            self.metric_var.set(self.ton_col() if self.ton_col() in metric_candidates else metric_candidates[0])

        if "operator" in self.df.columns:
            operators = sorted({
                self.normalize_operator(x)
                for x in self.df["operator"].dropna().tolist()
            })
            self.operator_menu.configure(values=["Todos"] + list(operators)[:300])
            self.operator_var.set("Todos")

        if "shift" in self.df.columns:
            shifts = sorted(self.df["shift"].dropna().astype(str).unique().tolist())
            self.shift_menu.configure(values=["Todos"] + shifts)
            self.shift_var.set("Todos")

    def refresh_all(self, initial=False):
        if self.df is None:
            return

        self.render_kpis()
        self.render_status_box(initial)

        if self.view_mode_var.get() == "Analisis":
            self.render_preview_table()
            self.render_summary_table()
            self.render_all_charts()
        else:
            self.render_report_main()
            self.render_report_chart()
            self.render_conclusions(initial)

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
            self.render_conclusions(False)

    # -------------------------------------------------
    # Renderers
    # -------------------------------------------------
    def render_kpis(self):
        df = self.get_filtered_df()
        if df is None or self.profile is None:
            return

        metric = self.metric_label()
        operator_summary = self.get_operator_summary(df)
        bench_summary = self.get_bench_summary(df)
        efficiency = self.efficiency_series(df).dropna()

        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        prod = self.to_numeric_col(df, metric)
        self.main_kpis["productivity"].configure(text=f"{metric}: {self.format_number(prod.mean())}")

        leader = operator_summary.iloc[0]["operator"] if not operator_summary.empty else "N/D"
        self.main_kpis["leader"].configure(text=str(leader))

        best_bench = str(bench_summary.iloc[0][self.bench_col()]) if not bench_summary.empty else "N/D"
        self.main_kpis["bench_perf"].configure(text=best_bench)

        self.main_kpis["efficiency"].configure(text=self.format_number(efficiency.mean()))

    def render_status_box(self, initial):
        df = self.get_filtered_df()
        if df is None:
            return

        metric = self.metric_label()
        prod = self.to_numeric_col(df, metric)
        time_s = self.to_numeric_col(df, self.time_col())
        compliance = self.compliance_series(df)

        lines = [
            "Estado operativo y calidad del dataset",
            "",
            f"- Filas disponibles: {self.profile['rows']}",
            f"- Columnas: {self.profile['cols']}",
            f"- Duplicados detectados: {self.profile['duplicates']}",
            f"- Nulos totales: {self.profile['total_nulls']}",
        ]

        if metric in df.columns:
            lines.append(f"- Productividad promedio ({metric}): {self.format_number(prod.mean())}")
            lines.append(f"- Variabilidad de {metric}: {self.format_number(prod.std())}")

        if self.time_col() in df.columns:
            lines.append(f"- Tiempo promedio de perforación: {self.format_number(time_s.mean())} min")

        if not compliance.dropna().empty:
            lines.append(f"- Cumplimiento promedio de perforación: {self.format_number(compliance.mean())}%")

        lines.append("")
        lines.append("Alertas y sugerencias:")

        if self.profile["suggestions"]:
            lines.extend([f"  • {s}" for s in self.profile["suggestions"]])
        else:
            lines.append("  • No se detectaron problemas relevantes.")

        if not initial and self.clean_summary:
            lines.extend([
                "",
                "Transformaciones aplicadas:",
                f"  • Filas originales: {self.clean_summary['rows_original']}",
                f"  • Filas finales: {self.clean_summary['rows_clean']}",
                f"  • Nulos originales: {self.clean_summary['nulls_original']}",
                f"  • Nulos finales: {self.clean_summary['nulls_final']}",
                f"  • Duplicados removidos: {self.clean_summary['actions']['duplicates_removed']}",
            ])

        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", tk.END)
        self.status_box.insert("1.0", "\n".join(lines))
        self.status_box.configure(state="disabled")

    def render_preview_table(self):
        df = self.get_filtered_df()
        if df is None:
            return
        preview = df.head(15).copy()
        self.update_treeview(self.tree, preview, width=110, limit=15)

    def render_summary_table(self):
        df = self.get_filtered_df()
        if df is None:
            return

        cols = [c for c in [
            self.time_col(),
            self.ton_col(),
            self.volume_col(),
            self.total_height_col(),
            self.real_height_col(),
            self.grade_col()
        ] if c in df.columns]

        if not cols:
            return

        summary = pd.DataFrame({
            "Variable": cols,
            "Media": [self.to_numeric_col(df, c).mean() for c in cols],
            "DesvStd": [self.to_numeric_col(df, c).std() for c in cols],
            "P25": [self.to_numeric_col(df, c).quantile(0.25) for c in cols],
            "P75": [self.to_numeric_col(df, c).quantile(0.75) for c in cols],
            "Max": [self.to_numeric_col(df, c).max() for c in cols],
        })

        self.update_treeview(self.summary_table, summary, width=125, limit=20)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def render_all_charts(self):
        self.render_time_chart()
        self.render_operator_chart()
        self.render_bench_chart()
        self.render_compliance_chart()

    def render_time_chart(self):
        self.clear_chart_frame(self.time_frame)
        summary = self.get_daily_summary()

        if summary.empty:
            self.render_chart_placeholder(self.time_frame, "Productividad en el tiempo")
            return

        palette = self.get_palette()
        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        ax.plot(
            summary["day"],
            summary["productivity"],
            color=palette["series_1"],
            linewidth=1.5,
            alpha=0.35,
            label="Promedio diario",
        )

        if "rolling_productivity" in summary.columns:
            ax.plot(
                summary["day"],
                summary["rolling_productivity"],
                color=palette["series_5"],
                linewidth=2.6,
                alpha=0.95,
                label="Media móvil 7",
            )

        ax.set_title(f"Evolución de {self.metric_label()}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel(self.metric_label())

        for label in ax.get_xticklabels():
            label.set_rotation(35)
            label.set_ha("right")

        ax.legend(frameon=False, fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=self.time_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_operator_chart(self):
        self.clear_chart_frame(self.operator_frame)
        summary = self.get_operator_summary()

        if summary.empty:
            self.render_chart_placeholder(self.operator_frame, "Ranking de operadores")
            return

        palette = self.get_palette()
        top = summary.head(self.safe_top_n()).sort_values("productivity", ascending=True)

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        bars = ax.barh(
            top["operator"].astype(str),
            top["productivity"],
            color=palette["series_2"],
            edgecolor=palette["accent"],
            alpha=0.88,
        )

        if len(bars) > 0:
            bars[-1].set_color(palette["series_5"])

        ax.set_title(f"Top {len(top)} operadores por {self.metric_label()}")
        ax.set_xlabel(self.metric_label())
        ax.set_ylabel("Operador")

        max_val = top["productivity"].max() if len(top) else 0
        offset = max_val * 0.02 if max_val else 0.1

        for bar, value in zip(bars, top["productivity"].values):
            ax.text(
                value + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                va="center",
                fontsize=8.5,
                color=palette["text"],
            )

        canvas = FigureCanvasTkAgg(fig, master=self.operator_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_bench_chart(self):
        self.clear_chart_frame(self.bench_frame)
        summary = self.get_bench_summary()

        if summary.empty:
            self.render_chart_placeholder(self.bench_frame, "Desempeño por banco")
            return

        palette = self.get_palette()
        focus = summary.head(5).copy()
        if len(summary) > 8:
            focus = pd.concat([summary.head(4), summary.tail(4)], axis=0)

        focus = focus.drop_duplicates(subset=[self.bench_col()]).sort_values("productivity", ascending=True)

        fig = create_figure(palette, figsize=(6.2, 4.0), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        colors = [palette["series_3"]] * len(focus)
        if len(colors) > 0:
            colors[-1] = palette["series_5"]
            colors[0] = palette["series_2"]

        bars = ax.barh(
            focus[self.bench_col()].astype(str),
            focus["productivity"],
            color=colors,
            edgecolor=palette["accent"],
            alpha=0.88,
        )

        ax.set_title(f"Bancos destacados por {self.metric_label()}")
        ax.set_xlabel(self.metric_label())
        ax.set_ylabel("Banco")

        max_val = float(focus["productivity"].max()) if len(focus) else 0.0
        ax.set_xlim(0, max_val * 1.18 if max_val > 0 else 1)

        inside_offset = max_val * 0.02 if max_val > 0 else 0.1
        outside_offset = max_val * 0.015 if max_val > 0 else 0.1

        for bar, value, rec in zip(bars, focus["productivity"].values, focus["records"].values):
            label = f"{value:.1f} | n={int(rec)}"
            y = bar.get_y() + bar.get_height() / 2

            # Si la barra es suficientemente larga, mete el texto dentro
            if value >= max_val * 0.22:
                ax.text(
                    value - inside_offset,
                    y,
                    label,
                    va="center",
                    ha="right",
                    fontsize=8.0,
                    color=palette["panel"],
                    fontweight="bold",
                )
            else:
                ax.text(
                    value + outside_offset,
                    y,
                    label,
                    va="center",
                    ha="left",
                    fontsize=8.0,
                    color=palette["text"],
                )

        fig.tight_layout(pad=1.4)

        canvas = FigureCanvasTkAgg(fig, master=self.bench_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_compliance_chart(self):
        self.clear_chart_frame(self.compliance_frame)
        summary = self.get_compliance_daily()

        if summary.empty:
            self.render_chart_placeholder(self.compliance_frame, "Cumplimiento de perforación")
            return

        palette = self.get_palette()
        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        ax.plot(
            summary["day"],
            summary["compliance"],
            color=palette["series_3"],
            linewidth=1.4,
            alpha=0.30,
            label="Promedio diario",
        )

        if "rolling_compliance" in summary.columns:
            ax.plot(
                summary["day"],
                summary["rolling_compliance"],
                color=palette["series_5"],
                linewidth=2.4,
                alpha=0.95,
                label="Media móvil 7",
            )

        ax.axhline(
            100,
            color=palette["series_2"],
            linestyle="--",
            linewidth=1.2,
            alpha=0.85,
            label="Objetivo 100%",
        )

        ax.set_title("Cumplimiento de perforación (%)")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("% cumplimiento")

        for label in ax.get_xticklabels():
            label.set_rotation(35)
            label.set_ha("right")

        ax.legend(frameon=False, fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=self.compliance_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_report_main(self):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        metric = self.metric_label()
        operator_summary = self.get_operator_summary(df)
        bench_summary = self.get_bench_summary(df)
        daily_summary = self.get_daily_summary(df)
        compliance_daily = self.get_compliance_daily(df)
        loss_summary = self.get_loss_summary(df)

        lines = []

        prod = self.to_numeric_col(df, metric)
        if not prod.dropna().empty:
            lines.append(f"Resultado principal: la productividad promedio de {metric} es {prod.mean():.2f}.")

        if not operator_summary.empty:
            leader = operator_summary.iloc[0]
            lines.append(f"Operador benchmark: {leader['operator']} presenta el mejor promedio en {metric} ({leader['productivity']:.2f}).")

        if not bench_summary.empty:
            best_bench = bench_summary.iloc[0]
            lines.append(f"Banco destacado: {best_bench[self.bench_col()]} lidera el rendimiento con {best_bench['productivity']:.2f}.")

        if not daily_summary.empty and len(daily_summary) >= 10:
            recent = daily_summary["productivity"].tail(5).mean()
            previous = daily_summary["productivity"].iloc[-10:-5].mean()
            delta = recent - previous if pd.notna(recent) and pd.notna(previous) else np.nan
            if pd.notna(delta):
                trend = "mejorando" if delta > 0 else "cayendo" if delta < 0 else "estable"
                lines.append(f"Señal reciente: la productividad está {trend} ({delta:+.2f} frente al bloque previo).")

        if not compliance_daily.empty:
            latest_comp = compliance_daily["compliance"].tail(7).mean()
            if pd.notna(latest_comp):
                lines.append(f"Cumplimiento reciente: el promedio de perforación ejecutada vs plan está en {latest_comp:.2f}%.")

        if not loss_summary.empty:
            worst = loss_summary.sort_values("Relacion", ascending=True).iloc[0]
            lines.append(f"Principal penalizador: {worst['Factor']} muestra la relación más negativa con la productividad ({worst['Relacion']:.3f}).")

        self.report_main_box.configure(state="normal")
        self.report_main_box.delete("1.0", tk.END)
        self.report_main_box.insert("1.0", "\n".join(lines))
        self.report_main_box.configure(state="disabled")

    def render_report_chart(self):
        for child in self.report_chart_frame.winfo_children():
            child.destroy()

        summary = self.get_operator_summary()
        if summary.empty:
            self.render_chart_placeholder(
                self.report_chart_frame,
                "Visual principal de soporte",
                "No hay datos suficientes para construir el reporte."
            )
            return

        palette = self.get_palette()
        top = summary.head(self.safe_top_n()).sort_values("productivity", ascending=True)

        fig = create_figure(palette, figsize=(7.2, 4.2), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        bars = ax.barh(
            top["operator"].astype(str),
            top["productivity"],
            color=palette["series_2"],
            edgecolor=palette["accent"],
            alpha=0.90,
        )

        if len(bars) > 0:
            bars[-1].set_color(palette["series_5"])

        ax.set_title(f"Operadores benchmark por {self.metric_label()}")
        ax.set_xlabel(self.metric_label())
        ax.set_ylabel("Operador")

        max_val = top["productivity"].max() if len(top) else 0
        offset = max_val * 0.02 if max_val else 0.1

        for bar, value in zip(bars, top["productivity"].values):
            ax.text(
                value + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                va="center",
                fontsize=8.5,
                color=palette["text"],
            )

        canvas = FigureCanvasTkAgg(fig, master=self.report_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_conclusions(self, initial):
        df = self.get_filtered_df()
        if df is None or df.empty:
            return

        metric = self.metric_label()
        operator_summary = self.get_operator_summary(df)
        bench_summary = self.get_bench_summary(df)
        compliance_daily = self.get_compliance_daily(df)
        loss_summary = self.get_loss_summary(df)

        lines = []

        prod = self.to_numeric_col(df, metric)
        eff = self.efficiency_series(df)
        compliance = self.compliance_series(df)

        if not prod.dropna().empty:
            lines.append(f"- La productividad promedio actual de {metric} es {prod.mean():.2f}.")
            lines.append(f"- La dispersión de {metric} es {prod.std():.2f}.")

        if not eff.dropna().empty:
            lines.append(f"- La eficiencia operativa promedio ({metric}/min) es {eff.mean():.3f}.")

        if not compliance.dropna().empty:
            lines.append(f"- El cumplimiento promedio de perforación es {compliance.mean():.2f}%.")

        if not operator_summary.empty:
            lines.append(f"- El operador benchmark actual es {operator_summary.iloc[0]['operator']}.")

        if not bench_summary.empty:
            lines.append(f"- El banco con mejor rendimiento actual es {bench_summary.iloc[0][self.bench_col()]}.")
            lines.append(f"- El banco más rezagado dentro del grupo analizado es {bench_summary.iloc[-1][self.bench_col()]}.")

        if not compliance_daily.empty and len(compliance_daily) >= 7:
            recent_comp = compliance_daily["compliance"].tail(7).mean()
            lines.append(f"- El cumplimiento reciente de perforación se ubica en {recent_comp:.2f}%.")

        if not loss_summary.empty:
            for _, row in loss_summary.iterrows():
                lines.append(f"- {row['Factor']}: relación con productividad de {row['Relacion']:.3f} ({row['Lectura']}).")

        if self.profile and not self.profile["missing_df"].empty:
            top_missing = self.profile["missing_df"].iloc[0]
            lines.append(f"- La principal alerta de calidad está en {top_missing['column']} con {int(top_missing['missing'])} faltantes.")

        if initial:
            lines.append("- Acción sugerida: validar primero la calidad del dataset antes de tomar comparaciones definitivas.")
        else:
            action = "- Acción sugerida: "
            if not operator_summary.empty and not bench_summary.empty:
                action += (
                    f"usar como referencia a {operator_summary.iloc[0]['operator']} y revisar condiciones operativas "
                    f"del banco {bench_summary.iloc[-1][self.bench_col()]} si mantiene menor productividad."
                )
            elif not operator_summary.empty:
                action += f"tomar como referencia operativa a {operator_summary.iloc[0]['operator']}."
            else:
                action += "revisar productividad, cumplimiento y bancos para ubicar el principal desvío."
            lines.append(action)

        self.conclusion_box.configure(state="normal")
        self.conclusion_box.delete("1.0", tk.END)
        self.conclusion_box.insert("1.0", "\n".join(lines))
        self.conclusion_box.configure(state="disabled")