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

        # =========================
        # HEADER
        # =========================
        make_title(self, "MineData Hub").pack(anchor="w", padx=18, pady=(16, 4))
        make_subtitle(
            self,
            "Plataforma integrada de analítica minera con módulos de Mining, Geology, Metallurgy y Maintenance.",
        ).pack(anchor="w", padx=18, pady=(0, 8))

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
        headline_card.pack(fill="x", padx=12, pady=(0, 8))

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
            wraplength=1400,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # =========================
        # QUICK ACCESS
        # =========================
        modules_grid = ctk.CTkFrame(self, fg_color="transparent")
        modules_grid.pack(fill="x", padx=12, pady=(0, 8))
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
                height=62,
            )
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=3)
            card.grid_propagate(False)

            ctk.CTkLabel(
                card,
                text=f"{cfg.get('icon_text', '•')} {module_name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(8, 1))

            ctk.CTkLabel(
                card,
                text=cfg["description"],
                wraplength=220,
                justify="left",
                text_color=palette["muted"],
            ).pack(anchor="w", padx=12, pady=(0, 4))

        # =========================
        # MAIN BODY
        # =========================
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(2, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        # =========================
        # LEFT COLUMN
        # =========================
        left_col = ctk.CTkFrame(body, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_col.grid_rowconfigure(2, weight=1)

        contact_card = ctk.CTkFrame(
            left_col,
            fg_color=palette["card_alt"],
            corner_radius=12,
            border_width=1,
            border_color=palette["border"],
        )
        contact_card.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            contact_card,
            text="Project / Contact",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(9, 6))

        contact_lines = [
            ("Autor", "Brayan Churata"),
            ("Programa", "CODEa UNI"),
            ("Versión", "1.0"),
            ("Correo", "brayan.churata@dataminesoftware.com"),
        ]

        for label, value in contact_lines:
            row = ctk.CTkFrame(contact_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=66,
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

        insights_card = ctk.CTkFrame(
            left_col,
            fg_color=palette["card_alt"],
            corner_radius=12,
            border_width=1,
            border_color=palette["border"],
        )
        insights_card.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            insights_card,
            text="Quick Insights",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(9, 6))

        insights = [
            ("Módulos", str(status_info["datasets_loaded"])),
            ("Mayor volumen", status_info["largest_module"]),
            ("Registros", f"{status_info['largest_records']:,}"),
            ("Alertas", str(status_info["alerts"])),
        ]

        for label, value in insights:
            row = ctk.CTkFrame(insights_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=88,
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
            corner_radius=12,
            border_width=1,
            border_color=palette["border"],
        )
        status_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            status_card,
            text="Module Status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(9, 6))

        header = ctk.CTkFrame(status_card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(0, 4))

        headers = ["Módulo", "Estado", "Reg."]
        widths = [88, 72, 54]

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
            row.pack(fill="x", padx=12, pady=2)

            values = [module, status, records]
            for idx, (value, width) in enumerate(zip(values, widths)):
                if idx == 1:
                    color = palette["success"] if value == "Cargado" else palette["muted"]
                else:
                    color = palette["text"]

                ctk.CTkLabel(
                    row,
                    text=value,
                    width=width,
                    anchor="w",
                    text_color=color,
                ).pack(side="left", padx=(0, 4))

        # =========================
        # RIGHT COLUMN
        # =========================
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(1, weight=1)

        # KPI SECTION
        overview_card = ctk.CTkFrame(
            right_col,
            fg_color=palette["card_alt"],
            corner_radius=12,
            border_width=1,
            border_color=palette["border"],
        )
        overview_card.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            overview_card,
            text="System Overview",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(9, 3))

        ctk.CTkLabel(
            overview_card,
            text="Resumen ejecutivo del sistema y referencias visuales por módulo.",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 7))

        kpi_wrap = ctk.CTkFrame(overview_card, fg_color="transparent")
        kpi_wrap.pack(fill="x", padx=10, pady=(0, 10))
        kpi_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        kpi_items = [
            ("Módulos", "4", palette.get("kpi_info", palette["primary"])),
            ("Datasets cargados", str(status_info["datasets_loaded"]), palette.get("kpi_ok", palette["success"])),
            ("Registros totales", f"{status_info['total_records']:,}", palette.get("kpi_info", palette["primary"])),
            (
                "Alertas activas",
                str(status_info["alerts"]),
                palette.get("kpi_alert", palette["danger"]) if status_info["alerts"] > 0 else palette.get("kpi_ok", palette["success"]),
            ),
        ]

        for i, (label, value, accent) in enumerate(kpi_items):
            outer = ctk.CTkFrame(
                kpi_wrap,
                fg_color=palette["panel"],
                corner_radius=12,
                border_width=1,
                border_color=palette["border"],
            )
            outer.grid(row=0, column=i, sticky="nsew", padx=4, pady=3)

            top_line = ctk.CTkFrame(outer, fg_color=accent, height=4, corner_radius=8)
            top_line.pack(fill="x", padx=0, pady=(0, 6))

            ctk.CTkLabel(
                outer,
                text=label,
                text_color=palette["muted"],
            ).pack(anchor="w", padx=10, pady=(0, 2))

            ctk.CTkLabel(
                outer,
                text=value,
                font=ctk.CTkFont(size=17, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=10, pady=(0, 8))

        # CHARTS SECTION
        charts_card = ctk.CTkFrame(
            right_col,
            fg_color=palette["card_alt"],
            corner_radius=12,
            border_width=1,
            border_color=palette["border"],
        )
        charts_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            charts_card,
            text="Visual Summary",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(9, 3))

        ctk.CTkLabel(
            charts_card,
            text="Cada módulo muestra una visual de referencia. Puedes cambiar el tipo de gráfica desde el selector.",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(0, 7))

        charts_grid = ctk.CTkFrame(charts_card, fg_color="transparent")
        charts_grid.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        charts_grid.grid_columnconfigure((0, 1), weight=1)
        charts_grid.grid_rowconfigure((0, 1), weight=1)

        modules_chart_order = ["Mining", "Geology", "Metallurgy", "Maintenance"]
        for i, module_name in enumerate(modules_chart_order):
            row = i // 2
            col = i % 2

            chart_card = ctk.CTkFrame(
                charts_grid,
                fg_color=palette["panel"],
                corner_radius=12,
                border_width=1,
                border_color=palette["border"],
            )
            chart_card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

            topbar = ctk.CTkFrame(chart_card, fg_color="transparent")
            topbar.pack(fill="x", padx=10, pady=(8, 4))

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
                width=150,
                height=28,
            )
            selector.pack(side="right")

            frame = ctk.CTkFrame(chart_card, fg_color="transparent")
            frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
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

    def find_column(self, df, candidates):
        normalized = {str(col).strip().lower(): col for col in df.columns}
        for cand in candidates:
            key = cand.strip().lower()
            if key in normalized:
                return normalized[key]

        for cand in candidates:
            key = cand.strip().lower()
            for norm_name, original in normalized.items():
                if key in norm_name or norm_name in key:
                    return original
        return None

    def to_numeric_series(self, series):
        return pd.to_numeric(series, errors="coerce")

    def shorten_labels(self, labels, max_len=14):
        out = []
        for x in labels:
            s = str(x)
            out.append(s if len(s) <= max_len else s[:max_len - 3] + "...")
        return out

    def empty_chart_message(self, ax, message):
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])

    def clear_chart(self, module_name):
        frame = self.chart_frames[module_name]
        for child in frame.winfo_children():
            child.destroy()

    def style_axes(self, fig, ax):
        palette = self.get_palette()
        fig.patch.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.grid(True, color=palette.get("chart_grid", palette["border"]), alpha=0.30, linestyle="--", linewidth=0.6)

        for spine in ax.spines.values():
            spine.set_color(palette["chart_axis"])

        ax.tick_params(axis="x", colors=palette["chart_text"], labelsize=8)
        ax.tick_params(axis="y", colors=palette["chart_text"], labelsize=8)
        ax.title.set_color(palette["chart_text"])
        ax.title.set_fontsize(10.5)
        ax.xaxis.label.set_color(palette["chart_text"])
        ax.yaxis.label.set_color(palette["chart_text"])

    def render_module_chart(self, module_name):
        self.clear_chart(module_name)
        palette = self.get_palette()
        df = self.get_dataset(module_name)
        chart_type = self.chart_options[module_name].get()

        fig = Figure(figsize=(6.4, 3.8), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax)

        if df is None or df.empty:
            self.empty_chart_message(ax, "Sin datos cargados")
        else:
            try:
                rendered = False

                if module_name == "Mining":
                    operator_col = self.find_column(df, ["operator", "operador"])
                    shift_col = self.find_column(df, ["shift", "turno"])
                    m3_col = self.find_column(df, ["M3_volado", "m3_volado", "m3", "volume", "volumen"])

                    if chart_type == "Top operadores" and operator_col and m3_col:
                        temp = df[[operator_col, m3_col]].copy()
                        temp[m3_col] = self.to_numeric_series(temp[m3_col])
                        temp = temp.dropna(subset=[operator_col, m3_col])

                        if not temp.empty:
                            grouped = temp.groupby(operator_col)[m3_col].mean().sort_values(ascending=False).head(6)
                            labels = self.shorten_labels(grouped.index.tolist(), 12)
                            ax.bar(labels, grouped.values, color=palette["series_1"])
                            ax.set_title("Top operadores")
                            ax.tick_params(axis="x", rotation=16)
                            rendered = True

                    elif chart_type == "Turnos" and shift_col and m3_col:
                        temp = df[[shift_col, m3_col]].copy()
                        temp[m3_col] = self.to_numeric_series(temp[m3_col])
                        temp = temp.dropna(subset=[shift_col, m3_col])

                        if not temp.empty:
                            grouped = temp.groupby(shift_col)[m3_col].mean().sort_values(ascending=False)
                            labels = self.shorten_labels(grouped.index.tolist(), 12)
                            ax.bar(labels, grouped.values, color=palette["series_4"])
                            ax.set_title("Rendimiento por turno")
                            rendered = True

                    elif chart_type == "Distribución M3" and m3_col:
                        data = self.to_numeric_series(df[m3_col]).dropna()
                        if not data.empty:
                            ax.hist(data, bins=20, color=palette["series_2"])
                            ax.set_title("Distribución M3")
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Mining: faltan columnas válidas")

                elif module_name == "Geology":
                    rock_col = self.find_column(df, ["rock_name", "rock", "litologia", "lithology"])
                    sio2_col = self.find_column(df, ["SiO2n", "SiO2", "sio2"])
                    tio2_col = self.find_column(df, ["TiO2n", "TiO2", "tio2"])

                    if chart_type == "Boxplot SiO2" and rock_col and sio2_col:
                        temp = df[[rock_col, sio2_col]].copy()
                        temp[sio2_col] = self.to_numeric_series(temp[sio2_col])
                        temp = temp.dropna(subset=[rock_col, sio2_col])

                        if not temp.empty:
                            common = temp[rock_col].astype(str).value_counts().head(4).index.tolist()
                            subset = temp[temp[rock_col].astype(str).isin(common)]
                            data = [subset[subset[rock_col].astype(str) == r][sio2_col].dropna().values for r in common]
                            labels = self.shorten_labels(common, 12)
                            ax.boxplot(data, labels=labels)
                            ax.set_title("Variabilidad SiO2")
                            ax.tick_params(axis="x", rotation=14)
                            rendered = True

                    elif chart_type == "SiO2 vs TiO2" and sio2_col and tio2_col:
                        temp = df[[sio2_col, tio2_col]].copy()
                        temp[sio2_col] = self.to_numeric_series(temp[sio2_col])
                        temp[tio2_col] = self.to_numeric_series(temp[tio2_col])
                        temp = temp.dropna().head(1200)

                        if not temp.empty:
                            ax.scatter(temp[sio2_col], temp[tio2_col], s=12, alpha=0.6, color=palette["series_3"])
                            ax.set_title("SiO2 vs TiO2")
                            ax.set_xlabel("SiO2")
                            ax.set_ylabel("TiO2")
                            rendered = True

                    elif chart_type == "Top litologías" and rock_col and sio2_col:
                        temp = df[[rock_col, sio2_col]].copy()
                        temp[sio2_col] = self.to_numeric_series(temp[sio2_col])
                        temp = temp.dropna(subset=[rock_col, sio2_col])

                        if not temp.empty:
                            grouped = temp.groupby(rock_col)[sio2_col].mean().sort_values(ascending=False).head(6)
                            labels = self.shorten_labels(grouped.index.tolist(), 12)
                            ax.bar(labels, grouped.values, color=palette["series_2"])
                            ax.set_title("Top litologías")
                            ax.tick_params(axis="x", rotation=16)
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Geology: faltan columnas válidas")

                elif module_name == "Metallurgy":
                    date_col = self.find_column(df, ["date", "fecha"])
                    silica_col = self.find_column(df, ["% Silica Concentrate", "silica", "silica concentrate"])
                    iron_col = self.find_column(df, ["% Iron Concentrate", "iron", "iron concentrate"])

                    if chart_type == "Tendencia sílice" and date_col and silica_col:
                        temp = df[[date_col, silica_col]].copy()
                        temp[silica_col] = self.to_numeric_series(temp[silica_col])
                        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
                        temp = temp.dropna(subset=[date_col, silica_col])

                        if not temp.empty:
                            agg = temp.groupby(temp[date_col].dt.date)[silica_col].mean().reset_index()
                            ax.plot(agg[date_col], agg[silica_col], color=palette["series_3"], linewidth=2)
                            ax.set_title("Tendencia sílice")
                            ax.tick_params(axis="x", rotation=16)
                            rendered = True

                    elif chart_type == "Hierro vs sílice" and iron_col and silica_col:
                        temp = df[[iron_col, silica_col]].copy()
                        temp[iron_col] = self.to_numeric_series(temp[iron_col])
                        temp[silica_col] = self.to_numeric_series(temp[silica_col])
                        temp = temp.dropna().head(1200)

                        if not temp.empty:
                            ax.scatter(temp[iron_col], temp[silica_col], s=12, alpha=0.6, color=palette["series_1"])
                            ax.set_title("Hierro vs sílice")
                            ax.set_xlabel("% Fe")
                            ax.set_ylabel("% SiO2")
                            rendered = True

                    elif chart_type == "Distribución sílice" and silica_col:
                        data = self.to_numeric_series(df[silica_col]).dropna()
                        if not data.empty:
                            ax.hist(data, bins=20, color=palette["series_2"])
                            ax.set_title("Distribución sílice")
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Metallurgy: faltan columnas válidas")

                elif module_name == "Maintenance":
                    device_col = self.find_column(df, ["device", "equipo"])
                    failure_col = self.find_column(df, ["failure", "falla"])
                    metric_cols = [c for c in df.columns if str(c).lower().startswith("metric")]
                    metric1_col = self.find_column(df, ["metric1"]) if "metric1" in [str(c).lower() for c in df.columns] else (metric_cols[0] if metric_cols else None)

                    if chart_type == "Equipos con fallas" and device_col and failure_col:
                        temp = df[[device_col, failure_col]].copy()
                        temp[failure_col] = self.to_numeric_series(temp[failure_col])
                        temp = temp.dropna(subset=[device_col, failure_col])

                        if not temp.empty:
                            grouped = temp.groupby(device_col)[failure_col].sum().sort_values(ascending=False).head(6)
                            labels = self.shorten_labels(grouped.index.tolist(), 12)
                            ax.bar(labels, grouped.values, color=palette["series_5"])
                            ax.set_title("Equipos con fallas")
                            ax.tick_params(axis="x", rotation=16)
                            rendered = True

                    elif chart_type == "Falla vs no falla" and failure_col and metric1_col:
                        temp = df[[failure_col, metric1_col]].copy()
                        temp[failure_col] = self.to_numeric_series(temp[failure_col])
                        temp[metric1_col] = self.to_numeric_series(temp[metric1_col])
                        temp = temp.dropna()

                        if not temp.empty:
                            grouped = temp.groupby(failure_col)[metric1_col].mean()
                            labels = ["Sin falla" if i == 0 else "Con falla" for i in grouped.index.tolist()]
                            ax.bar(labels, grouped.values, color=[palette["series_1"], palette["series_5"]][:len(labels)])
                            ax.set_title("Métrica por estado")
                            rendered = True

                    elif chart_type == "Distribución métrica" and metric1_col:
                        data = self.to_numeric_series(df[metric1_col]).dropna()
                        if not data.empty:
                            ax.hist(data, bins=20, color=palette["series_4"])
                            ax.set_title(f"Distribución {metric1_col}")
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Maintenance: faltan columnas válidas")

            except Exception:
                self.empty_chart_message(ax, "No se pudo renderizar")

        fig.tight_layout(pad=1.1)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frames[module_name])
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.chart_canvases[module_name] = canvas