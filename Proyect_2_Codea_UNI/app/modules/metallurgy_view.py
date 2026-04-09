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

        self.drop_duplicates_var = tk.BooleanVar(value=True)
        self.convert_numeric_var = tk.BooleanVar(value=True)
        self.convert_dates_var = tk.BooleanVar(value=True)
        self.drop_high_null_rows_var = tk.BooleanVar(value=False)
        self.fill_numeric_var = tk.StringVar(value="None")
        self.fill_categorical_var = tk.StringVar(value="None")

        self.metric_var = tk.StringVar(value="% Silica Concentrate")
        self.x_var = tk.StringVar(value="% Iron Concentrate")
        self.y_var = tk.StringVar(value="% Silica Concentrate")
        self.top_n_var = tk.StringVar(value="10")
        self.sort_by_var = tk.StringVar(value="date")
        self.sort_order_var = tk.StringVar(value="Asc")
        self.view_mode_var = tk.StringVar(value="Analisis")

        configure_treeview_style()
        self.build_ui()

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
            n = int(self.top_n_var.get())
            return max(3, min(n, 20))
        except Exception:
            return 10

    def get_filtered_df(self):
        if self.df is None:
            return None

        df = self.df.copy()

        sort_col = self.sort_by_var.get()
        if sort_col in df.columns:
            ascending = self.sort_order_var.get() == "Asc"
            try:
                df = df.sort_values(sort_col, ascending=ascending)
            except Exception:
                pass

        return df

    def build_ui(self):
        palette = self.get_palette()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        make_title(header, "Metallurgy Module").pack(anchor="w")
        make_subtitle(
            header,
            "Control de flotación, calidad del concentrado y apoyo para toma de decisiones.",
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

        self.main_kpis = {}
        main_labels = [
            ("silica", "Sílice promedio"),
            ("iron", "Hierro promedio"),
            ("driver", "Variable clave"),
            ("peak", "Pico de sílice"),
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

        ctk.CTkLabel(filter_box, text="Ordenar por", text_color=palette["muted"]).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(filter_box, values=["date"], variable=self.sort_by_var, command=lambda _: self.refresh_all())
        self.sort_menu.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Orden", text_color=palette["muted"]).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["Asc", "Desc"], variable=self.sort_order_var, command=lambda _: self.refresh_all(), width=90).grid(row=0, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable X", text_color=palette["muted"]).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.x_menu = ctk.CTkOptionMenu(filter_box, values=["% Iron Concentrate"], variable=self.x_var, command=lambda _: self.refresh_all())
        self.x_menu.grid(row=1, column=1, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Variable Y", text_color=palette["muted"]).grid(row=1, column=2, padx=8, pady=6, sticky="w")
        self.y_menu = ctk.CTkOptionMenu(filter_box, values=["% Silica Concentrate"], variable=self.y_var, command=lambda _: self.refresh_all())
        self.y_menu.grid(row=1, column=3, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Métrica principal", text_color=palette["muted"]).grid(row=1, column=4, padx=8, pady=6, sticky="w")
        self.metric_menu = ctk.CTkOptionMenu(filter_box, values=["% Silica Concentrate"], variable=self.metric_var, command=lambda _: self.refresh_all())
        self.metric_menu.grid(row=1, column=5, padx=8, pady=6, sticky="w")

        ctk.CTkLabel(filter_box, text="Top N", text_color=palette["muted"]).grid(row=1, column=6, padx=8, pady=6, sticky="w")
        ctk.CTkOptionMenu(filter_box, values=["5", "8", "10", "12", "15", "20"], variable=self.top_n_var, command=lambda _: self.refresh_all(), width=80).grid(row=1, column=7, padx=8, pady=6, sticky="w")

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

        self.profile_box = ctk.CTkTextbox(self.profile_card, height=150)
        self.profile_box.pack(fill="x", padx=12, pady=(0, 12))
        self.profile_box.insert("1.0", "Aquí aparecerá el diagnóstico y los cambios aplicados.")
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

        self.hist_card = make_card(grid)
        self.hist_card.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for card, txt in [
            (self.scatter_card, "Relación entre variables"),
            (self.line_card, "Tendencia temporal"),
            (self.bar_card, "Variables más asociadas"),
            (self.hist_card, "Distribución principal"),
        ]:
            ctk.CTkLabel(
                card,
                text=txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 6))

        self.scatter_frame = ctk.CTkFrame(self.scatter_card, fg_color="transparent")
        self.scatter_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.line_frame = ctk.CTkFrame(self.line_card, fg_color="transparent")
        self.line_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bar_frame = ctk.CTkFrame(self.bar_card, fg_color="transparent")
        self.bar_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.hist_frame = ctk.CTkFrame(self.hist_card, fg_color="transparent")
        self.hist_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.summary_card = make_card(self.analysis_zone)
        self.summary_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.summary_card,
            text="Resumen operativo",
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

        self.report_main_box = ctk.CTkTextbox(self.report_main_card, height=120)
        self.report_main_box.pack(fill="x", padx=12, pady=(0, 12))
        self.report_main_box.insert("1.0", "Aquí aparecerá la lectura principal.")
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

        self.conclusion_box = ctk.CTkTextbox(self.conclusion_card, height=150)
        self.conclusion_box.pack(fill="x", padx=12, pady=(0, 12))
        self.conclusion_box.insert("1.0", "Aquí aparecerán las conclusiones.")
        self.conclusion_box.configure(state="disabled")

    """def toggle_mode(self):
        if self.view_mode_var.get() == "Analisis":
            self.report_zone.pack_forget()
            self.analysis_zone.pack(fill="both", expand=True, pady=(0, 0))
        else:
            self.analysis_zone.pack_forget()
            self.report_zone.pack(fill="both", expand=True, pady=(0, 0))"""
            
    def toggle_mode(self):
        if self.view_mode_var.get() == "Analisis":
            self.report_zone.pack_forget()
            self.analysis_zone.pack(fill="both", expand=True, pady=(0, 0))
        else:
            self.analysis_zone.pack_forget()
            self.report_zone.pack(fill="both", expand=True, pady=(0, 0))

        if self.df is not None:
            self.refresh_all(initial=False)

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
                MODULE_CONFIG["Metallurgy"]["required_columns"]
            )

            if not is_valid:
                messagebox.showerror("Archivo inválido", f"Faltan columnas requeridas: {missing}")
                return

            self.raw_df = raw_df.copy()
            self.df = raw_df.copy()
            self.profile = profile_dataframe(self.raw_df)
            self.clean_summary = None

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
        self.app_state.set_dataset("Metallurgy", self.raw_df, self.df)

        self.update_controls()
        self.refresh_all(initial=False)

    def update_controls(self):
        if self.df is None:
            return

        cols = list(self.df.columns)
        self.sort_menu.configure(values=cols)
        self.sort_by_var.set("date" if "date" in cols else cols[0])

        num_cols = self.numeric_columns(self.df)
        if num_cols:
            self.x_menu.configure(values=num_cols)
            self.y_menu.configure(values=num_cols)
            self.metric_menu.configure(values=num_cols)

            self.x_var.set("% Iron Concentrate" if "% Iron Concentrate" in num_cols else num_cols[0])
            self.y_var.set("% Silica Concentrate" if "% Silica Concentrate" in num_cols else num_cols[min(1, len(num_cols)-1)])
            self.metric_var.set("% Silica Concentrate" if "% Silica Concentrate" in num_cols else num_cols[0])

    """def refresh_all(self, initial=False):
        if self.df is None:
            return
        self.render_kpis()
        self.render_profile_box(initial)
        self.render_preview_table()
        self.render_summary_table()
        self.render_all_charts()
        self.render_report_main()
        self.render_report_chart()
        self.render_conclusions(initial)"""
    def refresh_all(self, initial=False):
        if self.df is None:
            return

        self.render_kpis()
        self.render_profile_box(initial)

        if self.view_mode_var.get() == "Analisis":
            self.render_preview_table()
            self.render_summary_table()
            self.render_all_charts()
        else:
            self.render_report_main()
            self.render_report_chart()
            self.render_conclusions(initial)

    def render_kpis(self):
        df = self.get_filtered_df()
        metric = self.metric_var.get()

        self.tech_kpis["rows"].configure(text=f"{len(df):,}")
        self.tech_kpis["cols"].configure(text=str(df.shape[1]))
        self.tech_kpis["duplicates"].configure(text=str(self.profile["duplicates"]))
        self.tech_kpis["nulls"].configure(text=str(self.profile["total_nulls"]))

        silica_col = "% Silica Concentrate"
        iron_col = "% Iron Concentrate"

        self.main_kpis["silica"].configure(
            text=f"{df[silica_col].mean():.2f}" if silica_col in df.columns else "N/D"
        )
        self.main_kpis["iron"].configure(
            text=f"{df[iron_col].mean():.2f}" if iron_col in df.columns else "N/D"
        )

        driver = "N/D"
        if silica_col in df.columns:
            numeric_cols = self.numeric_columns(df)
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr(numeric_only=True)[silica_col].dropna().sort_values(key=lambda s: s.abs(), ascending=False)
                corr = corr.drop(labels=[silica_col], errors="ignore")
                if not corr.empty:
                    driver = f"{corr.index[0]} ({corr.iloc[0]:.3f})"
        self.main_kpis["driver"].configure(text=driver)

        peak = "N/D"
        if silica_col in df.columns:
            peak = f"{df[silica_col].max():.2f}"
        self.main_kpis["peak"].configure(text=peak)

    def render_profile_box(self, initial):
        lines = [
            "Diagnóstico general",
            "",
            f"- Filas: {self.profile['rows']}",
            f"- Columnas: {self.profile['cols']}",
            f"- Duplicados detectados: {self.profile['duplicates']}",
            f"- Nulos totales: {self.profile['total_nulls']}",
            f"- Columnas numéricas detectables: {len(self.profile['numeric_like_cols'])}",
            f"- Columnas fecha detectables: {len(self.profile['date_like_cols'])}",
            "",
            "Sugerencias:",
        ]

        if self.profile["suggestions"]:
            lines.extend([f"  • {s}" for s in self.profile["suggestions"]])
        else:
            lines.append("  • No se detectaron problemas relevantes.")

        if not initial and self.clean_summary:
            lines.extend([
                "",
                "Cambios aplicados:",
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
        df = self.get_filtered_df().head(15)

        self.tree.delete(*self.tree.get_children())
        cols = list(df.columns)
        self.tree["columns"] = cols

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")

        for _, row in df.iterrows():
            self.tree.insert("", "end", values=[str(v) for v in row.tolist()])

    def render_summary_table(self):
        df = self.get_filtered_df()
        silica_col = "% Silica Concentrate"
        iron_col = "% Iron Concentrate"

        cols = [c for c in [silica_col, iron_col, "Amina Flow", "Starch Flow", "Ore Pulp Density", "Ore Pulp pH"] if c in df.columns]
        if not cols:
            return

        summary = pd.DataFrame({
            "Variable": cols,
            "Media": [df[c].mean() for c in cols],
            "DesvStd": [df[c].std() for c in cols],
            "Min": [df[c].min() for c in cols],
            "Max": [df[c].max() for c in cols],
        })

        self.summary_table.delete(*self.summary_table.get_children())
        table_cols = list(summary.columns)
        self.summary_table["columns"] = table_cols

        for col in table_cols:
            self.summary_table.heading(col, text=col)
            self.summary_table.column(col, width=120, anchor="center")

        for _, row in summary.iterrows():
            vals = []
            for v in row.tolist():
                vals.append(f"{v:.2f}" if isinstance(v, float) else str(v))
            self.summary_table.insert("", "end", values=vals)

    def clear_chart_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    """def style_axes(self, fig, ax):
        palette = self.get_palette()
        fig.patch.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.grid(True, color=palette.get("chart_grid", palette["border"]), alpha=0.35, linestyle="--", linewidth=0.7)

        for spine in ax.spines.values():
            spine.set_color(palette["muted"])

        ax.tick_params(axis="x", colors=palette["text"])
        ax.tick_params(axis="y", colors=palette["text"])
        ax.title.set_color(palette["text"])
        ax.xaxis.label.set_color(palette["text"])
        ax.yaxis.label.set_color(palette["text"])"""

    def render_all_charts(self):
        self.render_scatter_chart()
        self.render_line_chart()
        self.render_bar_chart()
        self.render_hist_chart()

    def render_scatter_chart(self):
        self.clear_chart_frame(self.scatter_frame)
        df = self.get_filtered_df()
        x, y = self.x_var.get(), self.y_var.get()
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if {x, y}.issubset(df.columns):
            sample = df[[x, y]].dropna().head(2000)
            #ax.scatter(sample[x], sample[y], s=18, alpha=0.7, color=palette["primary"], edgecolors="none")
            ax.scatter(
                sample[x],
                sample[y],
                s=18,
                alpha=0.72,
                color=palette["series_1"],
                edgecolors="none"
            )
            ax.set_title(f"{x} vs {y}")
            ax.set_xlabel(x)
            ax.set_ylabel(y)

        canvas = FigureCanvasTkAgg(fig, master=self.scatter_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_line_chart(self):
        self.clear_chart_frame(self.line_frame)
        df = self.get_filtered_df()
        metric = self.metric_var.get()
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if "date" in df.columns and metric in df.columns:
            temp = df[["date", metric]].dropna().copy()
            temp["day"] = pd.to_datetime(temp["date"], errors="coerce").dt.date
            agg = temp.groupby("day")[metric].mean().reset_index()
            #ax.plot(agg["day"], agg[metric], color=palette["primary"], linewidth=2)
            ax.plot(agg["day"], agg[metric], color=palette["series_1"], linewidth=2)
            ax.set_title(f"Tendencia temporal de {metric}")
            #ax.tick_params(axis="x", rotation=35)
            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")
            
        canvas = FigureCanvasTkAgg(fig, master=self.line_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_bar_chart(self):
        self.clear_chart_frame(self.bar_frame)
        df = self.get_filtered_df()
        silica_col = "% Silica Concentrate"
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if silica_col in df.columns:
            numeric_cols = self.numeric_columns(df)
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr(numeric_only=True)[silica_col].dropna().sort_values(key=lambda s: s.abs(), ascending=False)
                corr = corr.drop(labels=[silica_col], errors="ignore").head(self.safe_top_n())
                bars = ax.bar(
                    corr.index.astype(str),
                    corr.values,
                    color=palette["series_2"],
                    edgecolor=palette["accent"]
                )

                if len(bars) > 0:
                    bars[0].set_color(palette["series_5"])

                ax.set_title(f"Top {self.safe_top_n()} variables asociadas a sílice")

                for label in ax.get_xticklabels():
                    label.set_rotation(35)
                    label.set_ha("right")

                ax.margins(x=0.05)

        canvas = FigureCanvasTkAgg(fig, master=self.bar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_hist_chart(self):
        self.clear_chart_frame(self.hist_frame)
        df = self.get_filtered_df()
        metric = self.metric_var.get()
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(6.0, 3.9), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if metric in df.columns:
            data = df[metric].dropna()
            ax.hist(
                data,
                bins=30,
                color=palette["series_1"],
                alpha=0.80,
                edgecolor=palette["chart_axis"]
            )

        canvas = FigureCanvasTkAgg(fig, master=self.hist_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_report_main(self):
        df = self.get_filtered_df()
        silica_col = "% Silica Concentrate"
        iron_col = "% Iron Concentrate"
        lines = []

        if silica_col in df.columns:
            lines.append(f"Resultado principal: el promedio de sílice en concentrado es {df[silica_col].mean():.2f}.")
            lines.append(f"Pico observado de sílice: {df[silica_col].max():.2f}.")

        if iron_col in df.columns:
            lines.append(f"Calidad del hierro: el promedio de hierro en concentrado es {df[iron_col].mean():.2f}.")

        if silica_col in df.columns:
            numeric_cols = self.numeric_columns(df)
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr(numeric_only=True)[silica_col].dropna().sort_values(key=lambda s: s.abs(), ascending=False)
                corr = corr.drop(labels=[silica_col], errors="ignore")
                if not corr.empty:
                    lines.append(f"Variable más asociada a sílice: {corr.index[0]} ({corr.iloc[0]:.3f}).")

        self.report_main_box.configure(state="normal")
        self.report_main_box.delete("1.0", tk.END)
        self.report_main_box.insert("1.0", "\n".join(lines))
        self.report_main_box.configure(state="disabled")

    def render_report_chart(self):
        for child in self.report_chart_frame.winfo_children():
            child.destroy()

        df = self.get_filtered_df()
        silica_col = "% Silica Concentrate"
        palette = self.get_palette()

        fig = create_figure(palette, figsize=(7.2, 4.2), dpi=100)
        ax = fig.add_subplot(111)
        style_axes(fig, ax, palette)

        if "date" in df.columns and silica_col in df.columns:
            temp = df[["date", silica_col]].dropna().copy()
            temp["day"] = pd.to_datetime(temp["date"], errors="coerce").dt.date
            agg = temp.groupby("day")[silica_col].mean().reset_index()
            ax.plot(agg["day"], agg[silica_col], color=palette["series_1"], linewidth=2)
            ax.set_title("Tendencia principal de sílice")
            for label in ax.get_xticklabels():
                label.set_rotation(35)
                label.set_ha("right")

        canvas = FigureCanvasTkAgg(fig, master=self.report_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def render_conclusions(self, initial):
        df = self.get_filtered_df()
        silica_col = "% Silica Concentrate"
        iron_col = "% Iron Concentrate"
        x, y = self.x_var.get(), self.y_var.get()

        lines = []

        if silica_col in df.columns:
            lines.append(f"Hallazgo principal: la sílice promedio se ubica en {df[silica_col].mean():.2f}.")

        if iron_col in df.columns:
            lines.append(f"Soporte operativo: el hierro promedio en concentrado es {df[iron_col].mean():.2f}.")

        if {x, y}.issubset(df.columns):
            corr = df[[x, y]].corr(numeric_only=True).iloc[0, 1]
            if abs(corr) >= 0.7:
                strength = "fuerte"
            elif abs(corr) >= 0.4:
                strength = "moderada"
            else:
                strength = "débil"
            lines.append(f"Relación clave: la asociación entre {x} y {y} es {strength} ({corr:.3f}).")

        if self.profile and not self.profile["missing_df"].empty:
            top_missing = self.profile["missing_df"].iloc[0]
            lines.append(f"Alerta de calidad: la columna {top_missing['column']} concentra {int(top_missing['missing'])} valores faltantes.")

        if initial:
            lines.append("Acción sugerida: revisar el perfil y decidir si conviene aplicar limpieza adicional antes de interpretar.")
        else:
            lines.append("Acción sugerida: interpretar estos resultados considerando la limpieza y el contexto operativo actual.")

        self.conclusion_box.configure(state="normal")
        self.conclusion_box.delete("1.0", tk.END)
        self.conclusion_box.insert("1.0", "\n".join(lines))
        self.conclusion_box.configure(state="disabled")