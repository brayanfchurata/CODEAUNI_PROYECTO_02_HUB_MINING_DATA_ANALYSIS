import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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
        self.x_var = tk.StringVar(value="metric1")
        self.y_var = tk.StringVar(value="metric2")
        self.metric_var = tk.StringVar(value="metric1")
        self.top_n_var = tk.StringVar(value="10")

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

    def numeric_columns(self, df):
        if df is None:
            return []
        return df.select_dtypes(include=["number"]).columns.tolist()

    def safe_top_n(self):
        try:
            v = int(self.top_n_var.get())
            return max(3, min(v, 30))
        except Exception:
            return 10

    def get_failure_series(self, df):
        if df is None or "failure" not in df.columns:
            return pd.Series(dtype="float64")

        s = df["failure"].copy()

        if pd.api.types.is_numeric_dtype(s):
            return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

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
        return mapped.fillna(0).astype(int)

    def get_filtered_df(self):
        if self.df is None:
            return None

        df = self.df.copy()

        if "device" in df.columns and self.selected_device_var.get() != "Todos":
            df = df[df["device"].astype(str) == self.selected_device_var.get()].copy()

        if "failure" in df.columns and self.selected_failure_var.get() != "Todos":
            failure_series = self.get_failure_series(df)
            desired = 1 if self.selected_failure_var.get() == "Con falla" else 0
            df = df[failure_series == desired].copy()

        sort_col = self.sort_by_var.get()
        if sort_col in df.columns:
            ascending = self.sort_order_var.get() == "Asc"
            try:
                df = df.sort_values(sort_col, ascending=ascending)
            except Exception:
                pass

        return df

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
            "Perfilado, limpieza asistida, exploración de fallas y análisis de métricas de sensores.",
        ).pack(anchor="w", pady=(4, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 10))

        make_button(actions, "Importar CSV/Excel", self.import_file).pack(side="left")
        make_button(actions, "Aplicar limpieza", self.apply_cleaning).pack(side="left", padx=10)

        self.info_label = ctk.CTkLabel(actions, text="Sin archivo cargado", text_color=palette["muted"])
        self.info_label.pack(side="left", padx=8)

        self.build_kpi_section()
        self.build_prep_section()
        self.build_profile_section()
        self.build_preview_section()
        self.build_dashboard_section()
        self.build_summary_section()
        self.build_conclusion_section()

    def build_kpi_section(self):
        palette = self.get_palette()

        self.kpi_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_wrap.pack(fill="x", padx=20, pady=(0, 10))
        self.kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_cards = {}
        labels = [
            ("samples", "Registros activos"),
            ("failure_rate", "Tasa de falla"),
            ("critical_device", "Dispositivo crítico"),
            ("metric_signal", "Métrica sensible"),
        ]

        for i, (key, title_txt) in enumerate(labels):
            card = make_card(self.kpi_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            title = ctk.CTkLabel(card, text=title_txt, text_color=palette["muted"])
            title.pack(anchor="w", padx=12, pady=(10, 2))

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
        labels = [
            ("rows", "Filas"),
            ("cols", "Columnas"),
            ("duplicates", "Duplicados"),
            ("nulls", "Nulos"),
        ]

        for i, (key, title_txt) in enumerate(labels):
            card = make_card(self.tech_kpi_wrap)
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            title = ctk.CTkLabel(card, text=title_txt, text_color=palette["muted"])
            title.pack(anchor="w", padx=12, pady=(10, 2))

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
        self.device_menu = ctk.CTkOptionMenu(filter_box, values=["Todos"], variable=self.selected_device_var, command=lambda _: self.refresh_analysis())
        self.device_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Estado falla", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        self.failure_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Todos", "Con falla", "Sin falla"],
            variable=self.selected_failure_var,
            command=lambda _: self.refresh_analysis(),
        )
        self.failure_menu.grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=4, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(filter_box, values=["date"], variable=self.sort_by_var, command=lambda _: self.refresh_analysis())
        self.sort_menu.grid(row=0, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["Asc", "Desc"], variable=self.sort_order_var, command=lambda _: self.refresh_analysis(), width=90).grid(row=0, column=7, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable X", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.x_menu = ctk.CTkOptionMenu(filter_box, values=["metric1"], variable=self.x_var, command=lambda _: self.refresh_analysis())
        self.x_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable Y", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        self.y_menu = ctk.CTkOptionMenu(filter_box, values=["metric2"], variable=self.y_var, command=lambda _: self.refresh_analysis())
        self.y_menu.grid(row=1, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica KPI", text_color=palette["muted"]).grid(row=1, column=4, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(filter_box, values=["metric1"], variable=self.metric_var, command=lambda _: self.refresh_analysis())
        self.metric_menu.grid(row=1, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Top N", text_color=palette["muted"]).grid(row=1, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["5", "8", "10", "12", "15", "20"], variable=self.top_n_var, command=lambda _: self.refresh_analysis(), width=80).grid(row=1, column=7, padx=8, pady=6, sticky="w")

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

    def build_preview_section(self):
        palette = self.get_palette()

        self.preview_card = make_card(self)
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

    def build_dashboard_section(self):
        palette = self.get_palette()

        self.dashboard_card = make_card(self)
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

        self.scatter_card = make_card(grid)
        self.scatter_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.box_card = make_card(grid)
        self.box_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.bar_card = make_card(grid)
        self.bar_card.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self.corr_card = make_card(grid)
        self.corr_card.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for card, txt in [
            (self.scatter_card, "Relación entre métricas"),
            (self.box_card, "Distribución por estado de falla"),
            (self.bar_card, "Top dispositivos con fallas"),
            (self.corr_card, "Correlación sensores vs falla"),
        ]:
            ctk.CTkLabel(
                card,
                text=txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 6))

        self.scatter_frame = ctk.CTkFrame(self.scatter_card, fg_color="transparent")
        self.scatter_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.box_frame = ctk.CTkFrame(self.box_card, fg_color="transparent")
        self.box_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bar_frame = ctk.CTkFrame(self.bar_card, fg_color="transparent")
        self.bar_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.corr_frame = ctk.CTkFrame(self.corr_card, fg_color="transparent")
        self.corr_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def build_summary_section(self):
        palette = self.get_palette()

        self.summary_card = make_card(self)
        self.summary_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.summary_card,
            text="Resumen por dispositivo",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        wrap = ctk.CTkFrame(self.summary_card, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.summary_table = ttk.Treeview(wrap, show="headings", height=12)
        self.summary_table.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.summary_table.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.summary_table.configure(yscrollcommand=sb.set)

    def build_conclusion_section(self):
        palette = self.get_palette()

        self.conclusion_card = make_card(self)
        self.conclusion_card.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            self.conclusion_card,
            text="Hallazgos automáticos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.conclusion_box = ctk.CTkTextbox(self.conclusion_card, height=160)
        self.conclusion_box.pack(fill="x", padx=12, pady=(0, 12))
        self.conclusion_box.insert("1.0", "Aquí aparecerán hallazgos y apoyo para decisión.")
        self.conclusion_box.configure(state="disabled")

    # -------------------------------------------------
    # Lógica
    # -------------------------------------------------
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

        num_cols = [c for c in self.numeric_columns(self.df) if c != "failure"]
        if not num_cols:
            num_cols = self.numeric_columns(self.df)

        if num_cols:
            self.x_menu.configure(values=num_cols)
            self.y_menu.configure(values=num_cols)
            self.metric_menu.configure(values=num_cols)

            self.x_var.set("metric1" if "metric1" in num_cols else num_cols[0])
            self.y_var.set("metric2" if "metric2" in num_cols else num_cols[min(1, len(num_cols) - 1)])
            self.metric_var.set("metric1" if "metric1" in num_cols else num_cols[0])

    def refresh_all(self, initial=False):
        if self.df is None:
            return
        self.render_kpis()
        self.render_profile_box(initial=initial)
        self.render_preview_table()
        self.render_summary_table()
        self.render_all_charts()
        self.render_conclusions(initial=initial)

    def refresh_analysis(self):
        if self.df is None:
            return
        self.render_kpis()
        self.render_preview_table()
        self.render_summary_table()
        self.render_all_charts()
        self.render_conclusions(initial=False)

    # -------------------------------------------------
    # Render
    # -------------------------------------------------
    def render_kpis(self):
        df = self.get_filtered_df()
        metric = self.metric_var.get()
        failure_series = self.get_failure_series(df)

        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        self.kpi_cards["samples"].configure(text=f"{len(df):,}")

        if len(df) > 0 and len(failure_series) == len(df):
            rate = failure_series.mean() * 100
            self.kpi_cards["failure_rate"].configure(text=f"{rate:.2f}%")
        else:
            self.kpi_cards["failure_rate"].configure(text="N/D")

        if {"device", "failure"}.issubset(df.columns) and not df.empty:
            tmp = df.copy()
            tmp["_failure_num"] = self.get_failure_series(tmp)
            grouped = tmp.groupby("device")["_failure_num"].sum().sort_values(ascending=False)
            critical_device = grouped.index[0] if not grouped.empty else "N/D"
            self.kpi_cards["critical_device"].configure(text=str(critical_device))
        else:
            self.kpi_cards["critical_device"].configure(text="N/D")

        metric_signal = "N/D"
        if metric in df.columns and "failure" in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            tmp = df[[metric]].copy()
            tmp["failure_num"] = self.get_failure_series(df)
            if tmp["failure_num"].nunique() > 1:
                mean_fail = tmp.loc[tmp["failure_num"] == 1, metric].mean()
                mean_ok = tmp.loc[tmp["failure_num"] == 0, metric].mean()
                if pd.notna(mean_fail) and pd.notna(mean_ok):
                    delta = mean_fail - mean_ok
                    metric_signal = f"{metric} ({delta:+.2f})"
        self.kpi_cards["metric_signal"].configure(text=metric_signal)

    def render_profile_box(self, initial=False):
        profile = self.profile

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
        preview = df.head(15)

        self.tree.delete(*self.tree.get_children())
        cols = list(preview.columns)
        self.tree["columns"] = cols

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")

        for _, row in preview.iterrows():
            self.tree.insert("", "end", values=[str(v) for v in row.tolist()])

    def render_summary_table(self):
        df = self.get_filtered_df()

        if "device" not in df.columns:
            return

        tmp = df.copy()
        if "failure" in tmp.columns:
            tmp["failure_num"] = self.get_failure_series(tmp)

        metric = self.metric_var.get()
        agg_map = {}

        if "failure_num" in tmp.columns:
            agg_map["failure_num"] = ["count", "sum", "mean"]

        if metric in tmp.columns and pd.api.types.is_numeric_dtype(tmp[metric]):
            agg_map[metric] = ["mean", "std", "max"]

        if not agg_map:
            return

        grouped = tmp.groupby("device").agg(agg_map).reset_index()
        grouped.columns = ["_".join(col).strip("_") for col in grouped.columns.values]

        rename_map = {
            "failure_num_count": "records",
            "failure_num_sum": "failures",
            "failure_num_mean": "failure_rate",
        }
        grouped = grouped.rename(columns=rename_map)

        if "failures" in grouped.columns:
            grouped = grouped.sort_values("failures", ascending=False)

        grouped = grouped.head(30)

        self.summary_table.delete(*self.summary_table.get_children())
        cols = list(grouped.columns)
        self.summary_table["columns"] = cols

        for col in cols:
            self.summary_table.heading(col, text=col)
            self.summary_table.column(col, width=120, anchor="center")

        for _, row in grouped.iterrows():
            vals = []
            for v in row.tolist():
                if isinstance(v, float):
                    if "rate" in str(cols[len(vals)]).lower():
                        vals.append(f"{v * 100:.2f}%")
                    else:
                        vals.append(f"{v:.2f}")
                else:
                    vals.append(str(v))
            self.summary_table.insert("", "end", values=vals)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def style_axes(self, fig, ax):
        palette = self.get_palette()
        fig.patch.set_facecolor(palette["chart_bg"])
        ax.set_facecolor(palette["chart_bg"])
        ax.grid(True, color=palette["chart_grid"], alpha=0.35, linestyle="--", linewidth=0.7)

        for spine in ax.spines.values():
            spine.set_color(palette["muted"])

        ax.tick_params(axis="x", colors=palette["text"])
        ax.tick_params(axis="y", colors=palette["text"])
        ax.title.set_color(palette["text"])
        ax.xaxis.label.set_color(palette["text"])
        ax.yaxis.label.set_color(palette["text"])

    def render_all_charts(self):
        self.render_scatter_chart()
        self.render_box_chart()
        self.render_bar_chart()
        self.render_corr_chart()

    def render_scatter_chart(self):
        self.clear_chart_frame(self.scatter_frame)
        df = self.get_filtered_df()
        x = self.x_var.get()
        y = self.y_var.get()
        palette = self.get_palette()

        fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        if x in df.columns and y in df.columns:
            sample = df[[x, y]].dropna().head(1500).copy()

            if "failure" in df.columns:
                sample["failure_num"] = self.get_failure_series(df.loc[sample.index])
                fail_df = sample[sample["failure_num"] == 1]
                ok_df = sample[sample["failure_num"] == 0]

                ax.scatter(ok_df[x], ok_df[y], s=18, alpha=0.55, color=palette["primary"], edgecolors="none", label="Sin falla")
                ax.scatter(fail_df[x], fail_df[y], s=22, alpha=0.80, color=palette["accent"], edgecolors="none", label="Con falla")
                ax.legend()
            else:
                ax.scatter(sample[x], sample[y], s=18, alpha=0.7, color=palette["accent"], edgecolors="none")

            ax.set_title(f"{x} vs {y}")
            ax.set_xlabel(x)
            ax.set_ylabel(y)

        canvas = FigureCanvasTkAgg(fig, master=self.scatter_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_box_chart(self):
        self.clear_chart_frame(self.box_frame)
        df = self.get_filtered_df()
        metric = self.metric_var.get()
        palette = self.get_palette()

        fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        if metric in df.columns and "failure" in df.columns:
            tmp = df[[metric]].copy()
            tmp["failure_num"] = self.get_failure_series(df)
            data_ok = tmp.loc[tmp["failure_num"] == 0, metric].dropna().values
            data_fail = tmp.loc[tmp["failure_num"] == 1, metric].dropna().values

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
                    patch.set_facecolor(palette["primary"])
                    patch.set_alpha(0.75)
                    patch.set_edgecolor(palette["accent"])
                for median in box["medians"]:
                    median.set_color(palette["text"])

                ax.set_title(f"Distribución de {metric} por estado")
                ax.set_ylabel(metric)

        canvas = FigureCanvasTkAgg(fig, master=self.box_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_bar_chart(self):
        self.clear_chart_frame(self.bar_frame)
        df = self.get_filtered_df()
        palette = self.get_palette()

        fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        if {"device", "failure"}.issubset(df.columns):
            tmp = df.copy()
            tmp["failure_num"] = self.get_failure_series(tmp)

            top_n = self.safe_top_n()
            grouped = tmp.groupby("device")["failure_num"].sum().sort_values(ascending=False).head(top_n)

            ax.bar(grouped.index.astype(str), grouped.values, color=palette["primary"], edgecolor=palette["accent"])
            ax.set_title(f"Top {top_n} dispositivos con fallas")
            ax.set_ylabel("Cantidad de fallas")
            ax.tick_params(axis="x", rotation=35)

        canvas = FigureCanvasTkAgg(fig, master=self.bar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_corr_chart(self):
        self.clear_chart_frame(self.corr_frame)
        df = self.get_filtered_df()
        palette = self.get_palette()

        fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        tmp = df.copy()
        if "failure" in tmp.columns:
            tmp["failure_num"] = self.get_failure_series(tmp)

        numeric_cols = tmp.select_dtypes(include=["number"]).columns.tolist()

        if len(numeric_cols) >= 2:
            corr = tmp[numeric_cols].corr(numeric_only=True)
            img = ax.imshow(corr.values, aspect="auto")
            ax.set_title("Correlación métricas vs falla")
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels(corr.columns, fontsize=8)

            cbar = fig.colorbar(img, ax=ax, fraction=0.046, pad=0.04)
            cbar.ax.yaxis.set_tick_params(color=palette["text"])
            for label in cbar.ax.get_yticklabels():
                label.set_color(palette["text"])

        canvas = FigureCanvasTkAgg(fig, master=self.corr_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_conclusions(self, initial=False):
        df = self.get_filtered_df()
        metric = self.metric_var.get()

        lines = []

        if "failure" in df.columns and not df.empty:
            failure_series = self.get_failure_series(df)
            lines.append(f"- La tasa de falla del conjunto filtrado es: {failure_series.mean() * 100:.2f}%")

        if {"device", "failure"}.issubset(df.columns) and not df.empty:
            tmp = df.copy()
            tmp["failure_num"] = self.get_failure_series(tmp)
            grouped = tmp.groupby("device")["failure_num"].sum().sort_values(ascending=False)
            if not grouped.empty:
                lines.append(f"- El dispositivo con más fallas es: {grouped.index[0]}")

        if metric in df.columns and "failure" in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            tmp = df[[metric]].copy()
            tmp["failure_num"] = self.get_failure_series(df)

            mean_fail = tmp.loc[tmp["failure_num"] == 1, metric].mean()
            mean_ok = tmp.loc[tmp["failure_num"] == 0, metric].mean()

            if pd.notna(mean_fail) and pd.notna(mean_ok):
                lines.append(f"- Promedio de {metric} con falla: {mean_fail:.2f}")
                lines.append(f"- Promedio de {metric} sin falla: {mean_ok:.2f}")

        x = self.x_var.get()
        y = self.y_var.get()
        if {x, y}.issubset(df.columns):
            corr = df[[x, y]].corr(numeric_only=True).iloc[0, 1]
            lines.append(f"- La correlación entre {x} y {y} es: {corr:.3f}")

        if self.profile and not self.profile["missing_df"].empty:
            top_missing = self.profile["missing_df"].iloc[0]
            lines.append(f"- La columna con más nulos es: {top_missing['column']} ({int(top_missing['missing'])})")

        if initial:
            lines.append("- El dataset fue cargado y perfilado. Falta decidir si aplicas limpieza adicional.")
        else:
            lines.append("- El análisis refleja los filtros, orden y limpieza actualmente aplicados.")

        self.conclusion_box.configure(state="normal")
        self.conclusion_box.delete("1.0", tk.END)
        self.conclusion_box.insert("1.0", "\n".join(lines))
        self.conclusion_box.configure(state="disabled")