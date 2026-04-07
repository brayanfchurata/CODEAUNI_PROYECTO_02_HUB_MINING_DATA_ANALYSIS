import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.ui.chart_theme import create_figure, style_axes, style_legend 
#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.figure import Figure

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


class GeologyView(ctk.CTkScrollableFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        self.app_state = app_state

        self.raw_df = None
        self.df = None
        self.profile = None
        self.clean_summary = None

        self.preview_canvas = None
        self.scatter_canvas = None
        self.box_canvas = None
        self.bar_canvas = None
        self.corr_canvas = None

        # Limpieza
        self.drop_duplicates_var = tk.BooleanVar(value=True)
        self.convert_numeric_var = tk.BooleanVar(value=True)
        self.convert_dates_var = tk.BooleanVar(value=True)
        self.drop_high_null_rows_var = tk.BooleanVar(value=False)
        self.fill_numeric_var = tk.StringVar(value="None")
        self.fill_categorical_var = tk.StringVar(value="None")

        # Filtros y controles dinámicos
        self.selected_rock_var = tk.StringVar(value="Todas")
        self.sort_by_var = tk.StringVar(value="rock_name")
        self.sort_order_var = tk.StringVar(value="Asc")
        self.x_var = tk.StringVar(value="SiO2n")
        self.y_var = tk.StringVar(value="TiO2n")
        self.metric_var = tk.StringVar(value="SiO2n")
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

    def get_filtered_df(self):
        if self.df is None:
            return None

        df = self.df.copy()

        if "rock_name" in df.columns and self.selected_rock_var.get() != "Todas":
            df = df[df["rock_name"].astype(str) == self.selected_rock_var.get()].copy()

        sort_col = self.sort_by_var.get()
        if sort_col in df.columns:
            ascending = self.sort_order_var.get() == "Asc"
            try:
                df = df.sort_values(sort_col, ascending=ascending)
            except Exception:
                pass

        return df

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

    # -------------------------------------------------
    # UI
    # -------------------------------------------------
    def build_ui(self):
        palette = self.get_palette()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        make_title(header, "Geology Module").pack(anchor="w")
        make_subtitle(
            header,
            "Perfilado, limpieza asistida, exploración geoquímica y apoyo para toma de decisiones.",
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
            ("samples", "Muestras válidas"),
            ("dominant", "Litología dominante"),
            ("avg_metric", "Promedio métrico"),
            ("best_group", "Grupo líder"),
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

        # Limpieza
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

        # Filtros dinámicos
        filter_box = ctk.CTkFrame(self.prep_card, fg_color="transparent")
        filter_box.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(filter_box, text="Litología", text_color=palette["muted"]).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.rock_menu = ctk.CTkOptionMenu(filter_box, values=["Todas"], variable=self.selected_rock_var, command=lambda _: self.refresh_analysis())
        self.rock_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(filter_box, values=["rock_name"], variable=self.sort_by_var, command=lambda _: self.refresh_analysis())
        self.sort_menu.grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=4, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["Asc", "Desc"], variable=self.sort_order_var, command=lambda _: self.refresh_analysis(), width=90).grid(row=0, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable X", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.x_menu = ctk.CTkOptionMenu(filter_box, values=["SiO2n"], variable=self.x_var, command=lambda _: self.refresh_analysis())
        self.x_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable Y", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        self.y_menu = ctk.CTkOptionMenu(filter_box, values=["TiO2n"], variable=self.y_var, command=lambda _: self.refresh_analysis())
        self.y_menu.grid(row=1, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica KPI", text_color=palette["muted"]).grid(row=1, column=4, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(filter_box, values=["SiO2n"], variable=self.metric_var, command=lambda _: self.refresh_analysis())
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
            text="Dashboard geoquímico",
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
            (self.scatter_card, "Relación entre variables"),
            (self.box_card, "Distribución por litología"),
            (self.bar_card, "Promedios por litología"),
            (self.corr_card, "Correlación geoquímica"),
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
            text="Resumen por litología",
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

        self.conclusion_box = ctk.CTkTextbox(self.conclusion_card, height=150)
        self.conclusion_box.pack(fill="x", padx=12, pady=(0, 12))
        self.conclusion_box.insert("1.0", "Aquí aparecerán hallazgos y apoyo para decisión.")
        self.conclusion_box.configure(state="disabled")

    # -------------------------------------------------
    # Lógica
    # -------------------------------------------------
    def import_file(self):
        path = filedialog.askopenfilename(
            title="Selecciona archivo de Geology",
            filetypes=[("Datos", "*.csv *.xlsx *.xls")],
        )
        if not path:
            return

        try:
            raw_df = load_file(path)
            is_valid, missing = validate_module_file(
                raw_df,
                MODULE_CONFIG["Geology"]["required_columns"]
            )

            if not is_valid:
                messagebox.showerror("Archivo inválido", f"Faltan columnas requeridas: {missing}")
                return

            self.raw_df = raw_df.copy()
            self.df = raw_df.copy()
            self.profile = profile_dataframe(self.raw_df)
            self.clean_summary = None

            self.info_label.configure(text=os.path.basename(path))
            self.app_state.set_dataset("Geology", self.raw_df, self.df)

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
        self.app_state.set_dataset("Geology", self.raw_df, self.df)

        self.update_controls()
        self.refresh_all(initial=False)

    def update_controls(self):
        if self.df is None:
            return

        # Litologías
        if "rock_name" in self.df.columns:
            rocks = sorted(self.df["rock_name"].dropna().astype(str).unique().tolist())
            self.rock_menu.configure(values=["Todas"] + rocks[:200])
            self.selected_rock_var.set("Todas")

        # Ordenamiento
        cols = list(self.df.columns)
        self.sort_menu.configure(values=cols)
        self.sort_by_var.set(cols[0])

        # Variables numéricas
        num_cols = self.numeric_columns(self.df)
        if num_cols:
            self.x_menu.configure(values=num_cols)
            self.y_menu.configure(values=num_cols)
            self.metric_menu.configure(values=num_cols)

            self.x_var.set("SiO2n" if "SiO2n" in num_cols else num_cols[0])
            self.y_var.set("TiO2n" if "TiO2n" in num_cols else num_cols[min(1, len(num_cols)-1)])
            self.metric_var.set("SiO2n" if "SiO2n" in num_cols else num_cols[0])

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

        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        self.kpi_cards["samples"].configure(text=f"{len(df):,}")

        if "rock_name" in df.columns and not df.empty:
            dominant = df["rock_name"].astype(str).value_counts().idxmax()
            self.kpi_cards["dominant"].configure(text=dominant)
        else:
            self.kpi_cards["dominant"].configure(text="N/D")

        if metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            self.kpi_cards["avg_metric"].configure(text=f"{metric}: {df[metric].mean():.2f}")
        else:
            self.kpi_cards["avg_metric"].configure(text="N/D")

        if "rock_name" in df.columns and metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            grouped = df.groupby("rock_name")[metric].mean(numeric_only=True).sort_values(ascending=False)
            best_group = grouped.index[0] if not grouped.empty else "N/D"
            self.kpi_cards["best_group"].configure(text=str(best_group))
        else:
            self.kpi_cards["best_group"].configure(text="N/D")

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
            self.tree.column(col, width=100, anchor="center")

        for _, row in preview.iterrows():
            self.tree.insert("", "end", values=[str(v) for v in row.tolist()])

    def render_summary_table(self):
        df = self.get_filtered_df()
        metric = self.metric_var.get()

        if "rock_name" not in df.columns:
            return

        summary_cols = [c for c in ["SiO2n", "TiO2n", "FeO*n", "MgOn", "CaOn", "K2On"] if c in df.columns]
        if metric in df.columns and metric not in summary_cols:
            summary_cols.insert(0, metric)

        grouped = df.groupby("rock_name")[summary_cols].agg(["mean", "std"]).reset_index()
        grouped.columns = ["_".join(col).strip("_") for col in grouped.columns.values]
        grouped = grouped.head(30)

        self.summary_table.delete(*self.summary_table.get_children())
        cols = list(grouped.columns)
        self.summary_table["columns"] = cols

        for col in cols:
            self.summary_table.heading(col, text=col)
            self.summary_table.column(col, width=110, anchor="center")

        for _, row in grouped.iterrows():
            vals = []
            for v in row.tolist():
                if isinstance(v, float):
                    vals.append(f"{v:.2f}")
                else:
                    vals.append(str(v))
            self.summary_table.insert("", "end", values=vals)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()
#Cambiando ejes de cambio 
    """def style_axes(self, fig, ax):
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
        ax.yaxis.label.set_color(palette["text"])"""

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

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        """fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)"""

        if x in df.columns and y in df.columns:
            sample = df[[x, y]].dropna().head(1500)
            ax.scatter(
                sample[x],
                sample[y],
                s=18,
                alpha=0.72,
                color=palette["series_1"],
                edgecolors="none"
                )
            #ax.scatter(sample[x], sample[y], s=18, alpha=0.7, color=palette["accent"], edgecolors="none")
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

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        """fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)"""

        if {"rock_name", metric}.issubset(df.columns):
            common = df["rock_name"].astype(str).value_counts().head(8).index
            subset = df[df["rock_name"].astype(str).isin(common)]
            data = [subset[subset["rock_name"].astype(str) == r][metric].dropna().values for r in common]
            
            box = ax.boxplot(data, labels=list(common), patch_artist=True)

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

            ax.tick_params(axis="x")
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_ha("right")
            
            """box = ax.boxplot(data, labels=list(common), patch_artist=True)
            for patch in box["boxes"]:
                patch.set_facecolor(palette["primary"])
                patch.set_alpha(0.75)
                patch.set_edgecolor(palette["accent"])
            for median in box["medians"]:
                median.set_color(palette["text"])
            ax.set_title(f"Distribución de {metric} por litología")
            ax.set_ylabel(metric)
            ax.tick_params(axis="x", rotation=30)"""

        canvas = FigureCanvasTkAgg(fig, master=self.box_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_bar_chart(self):
        self.clear_chart_frame(self.bar_frame)
        df = self.get_filtered_df()
        metric = self.metric_var.get()
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        """fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)"""

        if {"rock_name", metric}.issubset(df.columns):
            top_n = self.safe_top_n()
            grouped = df.groupby("rock_name")[metric].mean(numeric_only=True).sort_values(ascending=False).head(top_n)
            ax.bar(grouped.index.astype(str), grouped.values, color=palette["primary"], edgecolor=palette["accent"])
            ax.set_title(f"Top {top_n} litologías por {metric}")
            ax.set_ylabel(metric)
            ax.tick_params(axis="x", rotation=35)

        canvas = FigureCanvasTkAgg(fig, master=self.bar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_corr_chart(self):
        self.clear_chart_frame(self.corr_frame)
        df = self.get_filtered_df()
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        """fig = Figure(figsize=(5.2, 3.4), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)"""

        numeric_cols = self.numeric_columns(df)
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr(numeric_only=True)
            img = ax.imshow(corr.values, aspect="auto", cmap="YlGnBu")
            #img = ax.imshow(corr.values, aspect="auto")
            ax.set_title("Correlación geoquímica")
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

        if "rock_name" in df.columns and not df.empty:
            dominant = df["rock_name"].astype(str).value_counts().idxmax()
            lines.append(f"- La litología dominante es: {dominant}")

        if metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            lines.append(f"- El promedio de {metric} es: {df[metric].mean():.2f}")
            lines.append(f"- La desviación estándar de {metric} es: {df[metric].std():.2f}")

            if "rock_name" in df.columns:
                grouped = df.groupby("rock_name")[metric].mean(numeric_only=True).sort_values(ascending=False)
                if not grouped.empty:
                    lines.append(f"- La litología con mayor {metric} es: {grouped.index[0]}")

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