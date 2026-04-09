import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.shared_widgets import make_title, make_subtitle
from app.core.constants import MODULE_CONFIG
from app.ui.styles import PALETTE


class HomeView(ctk.CTkFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        self.app_state = app_state
        self.chart_canvases = {}
        self.chart_frames = {}
        self.chart_options = {
            "Mining": ctk.StringVar(value="Top operadores"),
            "Geology": ctk.StringVar(value="Boxplot SiO2"),
            "Metallurgy": ctk.StringVar(value="Tendencia sílice"),
            "Maintenance": ctk.StringVar(value="Equipos con fallas"),
        }
        self.build_ui()

    def get_palette(self):
        try:
            return self.master.master.palette
        except Exception:
            return PALETTE

    def get_dataset(self, module_name):
        return self.app_state.get_dataset(module_name)

    def module_status_data(self):
        rows = []
        datasets_loaded = 0
        total_records = 0
        alerts = 0
        max_module = "-"
        max_records = 0

        for module_name in ["Mining", "Geology", "Metallurgy", "Maintenance"]:
            df = self.get_dataset(module_name)

            if df is None:
                status = "Sin cargar"
                records = 0
                action = "-"
            else:
                status = "Cargado"
                records = len(df)
                action = "Disponible"
                datasets_loaded += 1
                total_records += records

                if records > max_records:
                    max_records = records
                    max_module = module_name

                try:
                    if int(df.isna().sum().sum()) > 0:
                        alerts += 1
                except Exception:
                    pass

            rows.append((module_name, status, str(records), action))

        return {
            "rows": rows,
            "datasets_loaded": datasets_loaded,
            "total_records": total_records,
            "alerts": alerts,
            "largest_module": max_module,
            "largest_records": max_records,
        }

    def build_ui(self):
        palette = self.get_palette()
        status_info = self.module_status_data()

        make_title(self, "MineData Hub").pack(anchor="w", padx=20, pady=(18, 4))
        make_subtitle(
            self,
            "Plataforma integrada de analítica minera con módulos de Mining, Geology, Metallurgy y Maintenance.",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        loaded = status_info["datasets_loaded"]
        total_records = status_info["total_records"]

        if loaded == 0:
            headline = "Sistema listo para comenzar. Aún no hay datasets cargados."
        else:
            headline = f"Sistema activo: {loaded}/4 módulos con data cargada, {total_records:,} registros acumulados."

        headline_card = ctk.CTkFrame(
            self,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        headline_card.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            headline_card,
            text="Estado general del sistema",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            headline_card,
            text=headline,
            text_color=palette["muted"],
            wraplength=1300,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Accesos rápidos compactos
        modules_grid = ctk.CTkFrame(self, fg_color="transparent")
        modules_grid.pack(fill="x", padx=14, pady=(0, 8))
        modules_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        modules = [m for m in MODULE_CONFIG.keys() if m != "Inicio"]
        for i, module_name in enumerate(modules):
            cfg = MODULE_CONFIG[module_name]

            card = ctk.CTkFrame(
                modules_grid,
                fg_color=palette["card_alt"],
                corner_radius=12,
                border_width=1,
                border_color=palette["border"],
                height=74,
            )
            card.grid(row=0, column=i, sticky="nsew", padx=5, pady=4)
            card.grid_propagate(False)

            ctk.CTkLabel(
                card,
                text=f"{cfg.get('icon_text', '•')} {module_name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                card,
                text=cfg["description"],
                wraplength=240,
                justify="left",
                text_color=palette["muted"],
            ).pack(anchor="w", padx=12, pady=(0, 6))

        # Cuerpo principal
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        # =========================
        # COLUMNA IZQUIERDA
        # =========================
        left_col = ctk.CTkFrame(body, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_col.grid_rowconfigure(2, weight=1)

        contact_card = ctk.CTkFrame(
            left_col,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        contact_card.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            contact_card,
            text="Project / Contact",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(10, 8))

        contact_lines = [
            ("Autor", "Brayan Churata"),
            ("Programa", "CODEa UNI"),
            ("Versión", "1.0"),
            ("Correo", "brayan.churata@dataminesoftware.com"),
        ]

        for label, value in contact_lines:
            row = ctk.CTkFrame(contact_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=68,
                anchor="w",
                text_color=palette["muted"],
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                anchor="w",
                wraplength=180,
                justify="left",
                text_color=palette["text"],
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            contact_card,
            text="Hub de analítica para exploración, operación, planta y mantenimiento.",
            wraplength=220,
            justify="left",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=12, pady=(8, 10))

        insights_card = ctk.CTkFrame(
            left_col,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        insights_card.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            insights_card,
            text="Quick Insights",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(10, 8))

        insights = [
            ("Módulos cargados", str(status_info["datasets_loaded"])),
            ("Más registros", status_info["largest_module"]),
            ("Registros máx.", f"{status_info['largest_records']:,}"),
            ("Alertas", str(status_info["alerts"])),
        ]

        for label, value in insights:
            row = ctk.CTkFrame(insights_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=95,
                anchor="w",
                text_color=palette["muted"],
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                anchor="w",
                text_color=palette["text"],
            ).pack(side="left")

        status_card = ctk.CTkFrame(
            left_col,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        status_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            status_card,
            text="Module Status",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(10, 8))

        header = ctk.CTkFrame(status_card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(0, 4))

        headers = ["Módulo", "Estado", "Reg."]
        widths = [95, 75, 55]

        for text, width in zip(headers, widths):
            ctk.CTkLabel(
                header,
                text=text,
                width=width,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
                text_color=palette["muted"],
            ).pack(side="left", padx=(0, 4))

        for module, status, records, _ in status_info["rows"]:
            row = ctk.CTkFrame(status_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)

            values = [module, status, records]
            for value, width in zip(values, widths):
                ctk.CTkLabel(
                    row,
                    text=value,
                    width=width,
                    anchor="w",
                    text_color=palette["text"],
                ).pack(side="left", padx=(0, 4))

        # =========================
        # COLUMNA DERECHA
        # =========================
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(1, weight=1)

        overview_card = ctk.CTkFrame(
            right_col,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        overview_card.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            overview_card,
            text="System Overview",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            overview_card,
            text="Resumen ejecutivo del sistema y referencias visuales por módulo.",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 8))

        kpi_wrap = ctk.CTkFrame(overview_card, fg_color="transparent")
        kpi_wrap.pack(fill="x", padx=10, pady=(0, 10))
        kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        summary_cards = [
            ("Módulos", "4"),
            ("Datasets cargados", str(status_info["datasets_loaded"])),
            ("Registros totales", f"{status_info['total_records']:,}"),
            ("Alertas activas", str(status_info["alerts"])),
        ]

        for i, (label, value) in enumerate(summary_cards):
            card = ctk.CTkFrame(
                kpi_wrap,
                fg_color=palette["panel"],
                corner_radius=12,
                border_width=1,
                border_color=palette["border"],
            )
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=3)

            ctk.CTkLabel(
                card,
                text=label,
                text_color=palette["muted"],
            ).pack(anchor="w", padx=10, pady=(8, 2))

            ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=10, pady=(0, 8))

        charts_card = ctk.CTkFrame(
            right_col,
            fg_color=palette["card_alt"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        charts_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            charts_card,
            text="Visual Summary",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            charts_card,
            text="Cada módulo muestra una visual de referencia. Puedes cambiar el tipo de gráfica desde el selector.",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 8))

        charts_grid = ctk.CTkFrame(charts_card, fg_color="transparent")
        charts_grid.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        charts_grid.grid_columnconfigure((0, 1), weight=1)
        charts_grid.grid_rowconfigure((0, 1), weight=1)

        modules_chart_order = ["Mining", "Geology", "Metallurgy", "Maintenance"]
        for i, module_name in enumerate(modules_chart_order):
            row = i // 2
            col = i % 2

            chart_card = ctk.CTkFrame(
                charts_grid,
                fg_color=palette["panel"],
                corner_radius=14,
                border_width=1,
                border_color=palette["border"],
            )
            chart_card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

            topbar = ctk.CTkFrame(chart_card, fg_color="transparent")
            topbar.pack(fill="x", padx=10, pady=(10, 6))

            ctk.CTkLabel(
                topbar,
                text=f"{MODULE_CONFIG[module_name].get('icon_text', '•')} {module_name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(side="left")

            selector = ctk.CTkOptionMenu(
                topbar,
                values=self.get_chart_options(module_name),
                variable=self.chart_options[module_name],
                command=lambda _, m=module_name: self.render_module_chart(m),
                width=160,
            )
            selector.pack(side="right")

            frame = ctk.CTkFrame(chart_card, fg_color="transparent")
            frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.chart_frames[module_name] = frame

        for module_name in modules_chart_order:
            self.render_module_chart(module_name)

    def get_chart_options(self, module_name):
        return {
            "Mining": ["Top operadores", "Turnos", "Distribución M3"],
            "Geology": ["Boxplot SiO2", "SiO2 vs TiO2", "Top litologías"],
            "Metallurgy": ["Tendencia sílice", "Hierro vs sílice", "Distribución sílice"],
            "Maintenance": ["Equipos con fallas", "Falla vs no falla", "Distribución métrica"],
        }[module_name]

    def clear_chart(self, module_name):
        frame = self.chart_frames[module_name]
        for child in frame.winfo_children():
            child.destroy()

    def style_axes(self, fig, ax):
        palette = self.get_palette()
        fig.patch.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.grid(True, color=palette.get("chart_grid", palette["border"]), alpha=0.35, linestyle="--", linewidth=0.7)

        for spine in ax.spines.values():
            spine.set_color(palette["chart_axis"])

        ax.tick_params(axis="x", colors=palette["chart_text"], labelsize=8)
        ax.tick_params(axis="y", colors=palette["chart_text"], labelsize=8)
        ax.title.set_color(palette["chart_text"])
        ax.title.set_fontsize(11)
        ax.xaxis.label.set_color(palette["chart_text"])
        ax.yaxis.label.set_color(palette["chart_text"])

    def render_module_chart(self, module_name):
        self.clear_chart(module_name)
        palette = self.get_palette()
        df = self.get_dataset(module_name)
        chart_type = self.chart_options[module_name].get()

        fig = Figure(figsize=(5.8, 3.2), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        if df is None or df.empty:
            ax.text(0.5, 0.5, "Sin datos cargados", ha="center", va="center", fontsize=11)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            try:
                if module_name == "Mining":
                    if chart_type == "Top operadores" and {"operator", "M3_volado"}.issubset(df.columns):
                        grouped = df.groupby("operator")["M3_volado"].mean().sort_values(ascending=False).head(6)
                        ax.bar(grouped.index.astype(str), grouped.values, color=palette["series_1"])
                        ax.set_title("Top operadores")
                        ax.tick_params(axis="x", rotation=18)

                    elif chart_type == "Turnos" and {"shift", "M3_volado"}.issubset(df.columns):
                        grouped = df.groupby("shift")["M3_volado"].mean().sort_values(ascending=False)
                        ax.bar(grouped.index.astype(str), grouped.values, color=palette["series_4"])
                        ax.set_title("Rendimiento por turno")

                    elif chart_type == "Distribución M3" and "M3_volado" in df.columns:
                        ax.hist(df["M3_volado"].dropna(), bins=20, color=palette["series_2"])
                        ax.set_title("Distribución M3_volado")

                elif module_name == "Geology":
                    if chart_type == "Boxplot SiO2" and {"rock_name", "SiO2n"}.issubset(df.columns):
                        common = df["rock_name"].astype(str).value_counts().head(5).index
                        subset = df[df["rock_name"].astype(str).isin(common)]
                        data = [subset[subset["rock_name"].astype(str) == r]["SiO2n"].dropna().values for r in common]
                        ax.boxplot(data, labels=list(common))
                        ax.set_title("Variabilidad SiO2")
                        ax.tick_params(axis="x", rotation=18)

                    elif chart_type == "SiO2 vs TiO2" and {"SiO2n", "TiO2n"}.issubset(df.columns):
                        sample = df[["SiO2n", "TiO2n"]].dropna().head(1200)
                        ax.scatter(sample["SiO2n"], sample["TiO2n"], s=12, alpha=0.6, color=palette["series_3"])
                        ax.set_title("SiO2 vs TiO2")
                        ax.set_xlabel("SiO2")
                        ax.set_ylabel("TiO2")

                    elif chart_type == "Top litologías" and {"rock_name", "SiO2n"}.issubset(df.columns):
                        grouped = df.groupby("rock_name")["SiO2n"].mean().sort_values(ascending=False).head(6)
                        ax.bar(grouped.index.astype(str), grouped.values, color=palette["series_2"])
                        ax.set_title("Top litologías")
                        ax.tick_params(axis="x", rotation=18)

                elif module_name == "Metallurgy":
                    if chart_type == "Tendencia sílice" and {"date", "% Silica Concentrate"}.issubset(df.columns):
                        temp = df[["date", "% Silica Concentrate"]].dropna().copy()
                        temp["day"] = pd.to_datetime(temp["date"], errors="coerce").dt.date
                        agg = temp.groupby("day")["% Silica Concentrate"].mean().reset_index()
                        ax.plot(agg["day"], agg["% Silica Concentrate"], color=palette["series_3"], linewidth=2)
                        ax.set_title("Tendencia sílice")
                        ax.tick_params(axis="x", rotation=18)

                    elif chart_type == "Hierro vs sílice" and {"% Iron Concentrate", "% Silica Concentrate"}.issubset(df.columns):
                        sample = df[["% Iron Concentrate", "% Silica Concentrate"]].dropna().head(1200)
                        ax.scatter(sample["% Iron Concentrate"], sample["% Silica Concentrate"], s=12, alpha=0.6, color=palette["series_1"])
                        ax.set_title("Hierro vs sílice")
                        ax.set_xlabel("% Fe")
                        ax.set_ylabel("% SiO2")

                    elif chart_type == "Distribución sílice" and "% Silica Concentrate" in df.columns:
                        ax.hist(df["% Silica Concentrate"].dropna(), bins=20, color=palette["series_2"])
                        ax.set_title("Distribución sílice")

                elif module_name == "Maintenance":
                    if chart_type == "Equipos con fallas" and {"device", "failure"}.issubset(df.columns):
                        grouped = df.groupby("device")["failure"].sum().sort_values(ascending=False).head(6)
                        ax.bar(grouped.index.astype(str), grouped.values, color=palette["series_5"])
                        ax.set_title("Equipos con fallas")
                        ax.tick_params(axis="x", rotation=18)

                    elif chart_type == "Falla vs no falla" and {"failure", "metric1"}.issubset(df.columns):
                        grouped = df.groupby("failure")["metric1"].mean()
                        labels = ["Sin falla" if i == 0 else "Con falla" for i in grouped.index.tolist()]
                        ax.bar(labels, grouped.values, color=[palette["series_1"], palette["series_5"]][:len(labels)])
                        ax.set_title("Metric1 por estado")

                    elif chart_type == "Distribución métrica":
                        metric_cols = [c for c in df.columns if str(c).lower().startswith("metric")]
                        if metric_cols:
                            metric = metric_cols[0]
                            ax.hist(df[metric].dropna(), bins=20, color=palette["series_4"])
                            ax.set_title(f"Distribución {metric}")

            except Exception:
                ax.text(0.5, 0.5, "No se pudo renderizar", ha="center", va="center", fontsize=11)
                ax.set_xticks([])
                ax.set_yticks([])

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frames[module_name])
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.chart_canvases[module_name] = canvas