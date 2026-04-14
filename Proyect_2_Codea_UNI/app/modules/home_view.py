import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.shared_widgets import make_title, make_subtitle
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

    def module_accent(self, module_name):
        palette = self.get_palette()
        return {
            "Mining": palette.get("module_mining", palette["primary"]),
            "Geology": palette.get("module_geology", palette["series_4"]),
            "Metallurgy": palette.get("module_metallurgy", palette["success"]),
            "Maintenance": palette.get("module_maintenance", palette["warning"]),
        }.get(module_name, palette["primary"])
        
    def module_title_color(self, module_name):
        return {
            "Mining": "#26486B",
            "Geology": "#304A73",
            "Metallurgy": "#3F6A54",
            "Maintenance": "#6E5846",
        }.get(module_name, self.get_palette()["text"])


    def module_border_color(self, module_name):
        return {
            "Mining": "#B7C9DD",
            "Geology": "#BCC9DE",
            "Metallurgy": "#BFD5C7",
            "Maintenance": "#D7C6B7",
        }.get(module_name, self.get_palette()["border"])

    def make_card(self, parent, fg_key="card_alt", corner_radius=12, border_key="border_soft"):
        palette = self.get_palette()
        return ctk.CTkFrame(
            parent,
            fg_color=palette.get(fg_key, palette["card_alt"]),
            corner_radius=corner_radius,
            border_width=1,
            border_color=palette.get(border_key, palette["border"]),
        )

    def add_section_title(self, parent, title, subtitle=None, pad_top=10):
        palette = self.get_palette()

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=12, pady=(pad_top, 6))

        ctk.CTkLabel(
            wrap,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                wrap,
                text=subtitle,
                font=ctk.CTkFont(size=13),
                text_color=palette["muted"],
                wraplength=1200,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

    def add_inline_header(self, parent, title, subtitle=None, pad_top=10):
        palette = self.get_palette()

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=12, pady=(pad_top, 6))
        wrap.grid_columnconfigure(0, weight=0)
        wrap.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            wrap,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).grid(row=0, column=0, sticky="w")

        if subtitle:
            ctk.CTkLabel(
                wrap,
                text=subtitle,
                font=ctk.CTkFont(size=12),
                text_color=palette["muted"],
                anchor="e",
                justify="right",
            ).grid(row=0, column=1, sticky="e", padx=(14, 0))

    def build_ui(self):
        palette = self.get_palette()
        status_info = self.module_status_data()

        # TOP BAND
        top_band = ctk.CTkFrame(self, fg_color="transparent")
        top_band.pack(fill="x", padx=12, pady=(10, 8))
        top_band.grid_columnconfigure(0, weight=3)
        top_band.grid_columnconfigure(1, weight=2)

        title_box = ctk.CTkFrame(top_band, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        make_title(title_box, "MineData Hub", palette=palette, size=21).pack(anchor="w", pady=(0, 2))
        make_subtitle(
            title_box,
            "Plataforma integrada de analítica minera con módulos de Minería, Geología, Metalurgia y Mantenimiento.",
            palette=palette,
            size=12,
        ).pack(anchor="w")

        loaded = status_info["datasets_loaded"]
        total_records = status_info["total_records"]

        if loaded == 0:
            headline = "Sistema listo para comenzar. Aún no hay datasets cargados."
        else:
            headline = f"Sistema activo: {loaded}/4 módulos con data cargada, {total_records:,} registros acumulados."

        headline_card = ctk.CTkFrame(
            top_band,
            fg_color=palette.get("headline_card", palette["card_alt"]),
            corner_radius=12,
            border_width=1,
            border_color=palette.get("border_soft", palette["border"]),
            height=84,
        )
        headline_card.grid(row=0, column=1, sticky="nsew")
        headline_card.grid_propagate(False)

        ctk.CTkFrame(
            headline_card,
            fg_color=palette.get("section_accent", palette["accent"]),
            height=3,
            corner_radius=8,
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            headline_card,
            text="Estado general del sistema",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=12, pady=(0, 2))

        ctk.CTkLabel(
            headline_card,
            text=headline,
            font=ctk.CTkFont(size=12),
            text_color=palette["muted"],
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # BODY
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # LEFT RAIL
        left_col = ctk.CTkFrame(body, fg_color="transparent", width=295)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_col.grid_propagate(False)

        modules_card = self.make_card(left_col, fg_key="card_alt")
        modules_card.pack(fill="x", pady=(0, 8))

        self.add_section_title(
            modules_card,
            "Modules",
            "Acceso rápido al estado de cada módulo.",
        )

        modules_block = ctk.CTkFrame(modules_card, fg_color="transparent")
        modules_block.pack(fill="x", padx=10, pady=(0, 10))

        module_descriptions = {
            "Mining": "Perforación, voladura y productividad",
            "Geology": "Geoquímica de rocas y óxidos",
            "Metallurgy": "Flotación y control de sílice",
            "Maintenance": "Monitoreo de equipos y fallas",
        }

        status_lookup = {
            module: {"status": status, "records": records}
            for module, status, records, _ in status_info["rows"]
        }

        for module_name in ["Mining", "Geology", "Metallurgy", "Maintenance"]:
            accent = self.module_accent(module_name)
            title_color = self.module_title_color(module_name)
            border_color = self.module_border_color(module_name)

            module_info = status_lookup.get(module_name, {"status": "Sin cargar", "records": "0"})
            status_text = module_info["status"]
            records_text = module_info["records"]

            status_color = palette["muted"]

            item = ctk.CTkFrame(
                modules_block,
                fg_color=palette.get("panel", palette["card"]),
                corner_radius=10,
                border_width=1,
                border_color=border_color,
                height=88,
            )
            item.pack(fill="x", pady=4)
            item.pack_propagate(False)

            ctk.CTkFrame(
                item,
                fg_color=accent,
                width=4,
                corner_radius=8
            ).pack(side="left", fill="y", padx=(0, 8))

            content = ctk.CTkFrame(item, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=7)

            top_row = ctk.CTkFrame(content, fg_color="transparent")
            top_row.pack(fill="x")

            ctk.CTkLabel(
                top_row,
                text=module_name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=title_color,
            ).pack(side="left", anchor="w")

            ctk.CTkLabel(
                top_row,
                text=status_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=status_color,
            ).pack(side="right", anchor="e")

            ctk.CTkLabel(
                content,
                text=module_descriptions[module_name],
                font=ctk.CTkFont(size=11),
                text_color=palette["muted"],
                wraplength=220,
                justify="left",
            ).pack(anchor="w", pady=(3, 4))

            bottom_row = ctk.CTkFrame(content, fg_color="transparent")
            bottom_row.pack(fill="x")

            ctk.CTkLabel(
                bottom_row,
                text=f"Registros: {records_text}",
                font=ctk.CTkFont(size=11),
                text_color=palette["text"],
            ).pack(side="left", anchor="w")

        insights_card = self.make_card(left_col, fg_key="card_alt")
        insights_card.pack(fill="x", pady=(0, 8))

        self.add_section_title(insights_card, "Quick Insights")

        insights_wrap = ctk.CTkFrame(insights_card, fg_color="transparent")
        insights_wrap.pack(fill="x", padx=10, pady=(0, 10))
        insights_wrap.grid_columnconfigure((0, 1), weight=1)

        insights = [
            ("Módulos", str(status_info["datasets_loaded"])),
            ("Mayor volumen", status_info["largest_module"]),
            ("Registros", f"{status_info['largest_records']:,}"),
            ("Alertas", str(status_info["alerts"])),
        ]

        for i, (label, value) in enumerate(insights):
            r = i // 2
            c = i % 2

            cell = ctk.CTkFrame(
                insights_wrap,
                fg_color=palette.get("panel", palette["card"]),
                corner_radius=9,
                border_width=1,
                border_color=palette.get("border_soft", palette["border"]),
                height=76,
            )
            cell.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            cell.grid_propagate(False)

            ctk.CTkLabel(
                cell,
                text=label,
                text_color=palette["muted"],
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=8, pady=(8, 2))

            ctk.CTkLabel(
                cell,
                text=value,
                text_color=palette["text"],
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=8, pady=(0, 8))

        # RIGHT ANALYTICS
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(1, weight=1)

        overview_card = self.make_card(right_col, fg_key="card_alt")
        overview_card.pack(fill="x", pady=(0, 8))

        self.add_inline_header(
            overview_card,
            "System Overview",
            "Resumen ejecutivo del sistema y referencias visuales por módulo.",
        )

        kpi_wrap = ctk.CTkFrame(overview_card, fg_color="transparent")
        kpi_wrap.pack(fill="x", padx=8, pady=(0, 8))
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
                corner_radius=11,
                border_width=1,
                border_color=palette.get("border_soft", palette["border"]),
                height=78,
            )
            outer.grid(row=0, column=i, sticky="nsew", padx=4, pady=2)
            outer.grid_propagate(False)

            ctk.CTkFrame(outer, fg_color=accent, height=3, corner_radius=8).pack(fill="x", pady=(0, 6))

            ctk.CTkLabel(
                outer,
                text=label,
                text_color=palette["muted"],
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=10, pady=(0, 1))

            ctk.CTkLabel(
                outer,
                text=value,
                font=ctk.CTkFont(size=17, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=10, pady=(0, 6))

        charts_card = self.make_card(right_col, fg_key="card_alt")
        charts_card.pack(fill="both", expand=True)

        self.add_inline_header(
            charts_card,
            "Visual Summary",
            "Cada módulo muestra una visual de referencia. Puedes cambiar el tipo de gráfica desde el selector.",
        )

        charts_grid = ctk.CTkFrame(charts_card, fg_color="transparent")
        charts_grid.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        charts_grid.grid_columnconfigure((0, 1), weight=1)
        charts_grid.grid_rowconfigure((0, 1), weight=1)

        modules_chart_order = ["Mining", "Geology", "Metallurgy", "Maintenance"]
        for i, module_name in enumerate(modules_chart_order):
            row = i // 2
            col = i % 2
            accent = self.module_accent(module_name)

            chart_card = ctk.CTkFrame(
                charts_grid,
                fg_color=palette["panel"],
                corner_radius=10,
                border_width=1,
                border_color=palette.get("border_soft", palette["border"]),
            )
            chart_card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            chart_card.grid_rowconfigure(1, weight=1)
            chart_card.grid_columnconfigure(0, weight=1)

            topbar = ctk.CTkFrame(chart_card, fg_color="transparent", height=34)
            topbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 1))
            topbar.grid_propagate(False)
            topbar.grid_columnconfigure(0, weight=1)

            title_box = ctk.CTkFrame(topbar, fg_color="transparent")
            title_box.grid(row=0, column=0, sticky="w")

            marker = ctk.CTkFrame(
                title_box,
                fg_color=accent,
                width=8,
                height=8,
                corner_radius=8,
            )
            marker.pack(side="left", padx=(0, 6), pady=11)

            ctk.CTkLabel(
                title_box,
                text=module_name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.module_title_color(module_name)
                #text_color=palette["text"],
            ).pack(side="left", pady=5)

            selector = ctk.CTkOptionMenu(
                topbar,
                values=self.get_chart_options(module_name),
                variable=self.chart_options[module_name],
                command=lambda _, m=module_name: self.render_module_chart(m),
                width=140,
                height=28,
                fg_color=palette["primary"],
                button_color=palette["primary"],
                button_hover_color=palette["primary_hover"],
                dropdown_fg_color=palette["panel"],
                dropdown_text_color=palette["text"],
                text_color=palette["panel"] if palette["primary"] != palette["panel"] else palette["text"],
                font=ctk.CTkFont(size=10),
            )
            selector.grid(row=0, column=1, sticky="e", padx=(8, 0), pady=1)

            frame = ctk.CTkFrame(
                chart_card,
                fg_color=palette.get("panel_2", palette["panel"]),
                corner_radius=9,
                border_width=1,
                border_color=palette.get("border_soft", palette["border"]),
            )
            frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
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
            out.append(s if len(s) <= max_len else s[: max_len - 3] + "...")
        return out

    def apply_chart_margins(self, fig, ax, chart_type):
        ax.margins(x=0.04)

        if chart_type in {"Top operadores", "Turnos", "Top litologías", "Equipos con fallas"}:
            for label in ax.get_xticklabels():
                label.set_rotation(18)
                label.set_ha("right")
            fig.subplots_adjust(left=0.08, right=0.985, top=0.88, bottom=0.28)

        elif chart_type in {"Boxplot SiO2"}:
            for label in ax.get_xticklabels():
                label.set_rotation(10)
                label.set_ha("right")
            fig.subplots_adjust(left=0.08, right=0.985, top=0.88, bottom=0.24)

        elif chart_type in {"Tendencia sílice"}:
            for label in ax.get_xticklabels():
                label.set_rotation(18)
                label.set_ha("right")
            fig.subplots_adjust(left=0.085, right=0.985, top=0.88, bottom=0.24)

        elif chart_type in {"SiO2 vs TiO2", "Hierro vs sílice"}:
            fig.subplots_adjust(left=0.10, right=0.985, top=0.88, bottom=0.16)

        else:
            fig.subplots_adjust(left=0.08, right=0.985, top=0.88, bottom=0.18)

    def empty_chart_message(self, ax, message, module_name=None):
        palette = self.get_palette()
        accent = self.module_accent(module_name) if module_name else palette["primary"]
        title_color = self.module_title_color(module_name) if module_name else palette["text"]

        ax.text(
            0.5,
            0.57,
            "Sin datos disponibles",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=title_color,
            transform=ax.transAxes,
        )
        ax.text(
            0.5,
            0.48,
            message,
            ha="center",
            va="center",
            fontsize=10,
            color=palette.get("muted", palette["text"]),
            transform=ax.transAxes,
        )

        ax.plot(
            [0.40, 0.60],
            [0.67, 0.67],
            transform=ax.transAxes,
            color=accent,
            linewidth=2.0,
            alpha=0.95,
        )

        ax.set_xticks([])
        ax.set_yticks([])

        for spine in ax.spines.values():
            spine.set_color(palette.get("empty_state_border", palette["border"]))

    def clear_chart(self, module_name):
        frame = self.chart_frames[module_name]
        for child in frame.winfo_children():
            child.destroy()

    def style_axes(self, fig, ax, module_name=None):
        palette = self.get_palette()
        fig.patch.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.set_facecolor(palette.get("chart_bg", palette["panel"]))
        ax.grid(
            True,
            color=palette.get("chart_grid", palette["border"]),
            alpha=0.22,
            linestyle="--",
            linewidth=0.50,
        )

        for spine in ax.spines.values():
            spine.set_color(palette["chart_axis"])

        ax.tick_params(axis="x", colors=palette["chart_text"], labelsize=8.5, pad=2)
        ax.tick_params(axis="y", colors=palette["chart_text"], labelsize=8.5, pad=2)
        ax.title.set_color(self.module_title_color(module_name) if module_name else palette["chart_text"])
        ax.title.set_fontsize(10.5)
        ax.xaxis.label.set_color(palette["chart_text"])
        ax.yaxis.label.set_color(palette["chart_text"])

    def render_module_chart(self, module_name):
        self.clear_chart(module_name)
        palette = self.get_palette()
        df = self.get_dataset(module_name)
        chart_type = self.chart_options[module_name].get()

        fig = Figure(figsize=(8.6, 5.2), dpi=100)
        ax = fig.add_subplot(111)
        self.style_axes(fig, ax, module_name)
       #self.style_axes(fig, ax)

        if df is None or df.empty:
            self.empty_chart_message(ax, "Carga un dataset para habilitar esta vista.", module_name)
            fig.subplots_adjust(left=0.06, right=0.985, top=0.93, bottom=0.10)
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
                            labels = self.shorten_labels(grouped.index.tolist(), 13)
                            ax.bar(labels, grouped.values, color=palette["series_1"])
                            ax.set_title("Top operadores")
                            rendered = True

                    elif chart_type == "Turnos" and shift_col and m3_col:
                        temp = df[[shift_col, m3_col]].copy()
                        temp[m3_col] = self.to_numeric_series(temp[m3_col])
                        temp = temp.dropna(subset=[shift_col, m3_col])

                        if not temp.empty:
                            grouped = temp.groupby(shift_col)[m3_col].mean().sort_values(ascending=False)
                            labels = self.shorten_labels(grouped.index.tolist(), 13)
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
                        self.empty_chart_message(ax, "Mining: faltan columnas válidas.", module_name)

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
                            rendered = True

                    elif chart_type == "SiO2 vs TiO2" and sio2_col and tio2_col:
                        temp = df[[sio2_col, tio2_col]].copy()
                        temp[sio2_col] = self.to_numeric_series(temp[sio2_col])
                        temp[tio2_col] = self.to_numeric_series(temp[tio2_col])
                        temp = temp.dropna().head(1400)

                        if not temp.empty:
                            ax.scatter(temp[sio2_col], temp[tio2_col], s=14, alpha=0.6, color=palette["series_3"])
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
                            labels = self.shorten_labels(grouped.index.tolist(), 13)
                            ax.bar(labels, grouped.values, color=palette["series_2"])
                            ax.set_title("Top litologías")
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Geology: faltan columnas válidas.", module_name)

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
                            ax.plot(agg.iloc[:, 0], agg.iloc[:, 1], color=palette["series_3"], linewidth=2.1)
                            ax.set_title("Tendencia sílice")
                            rendered = True

                    elif chart_type == "Hierro vs sílice" and iron_col and silica_col:
                        temp = df[[iron_col, silica_col]].copy()
                        temp[iron_col] = self.to_numeric_series(temp[iron_col])
                        temp[silica_col] = self.to_numeric_series(temp[silica_col])
                        temp = temp.dropna().head(1400)

                        if not temp.empty:
                            ax.scatter(temp[iron_col], temp[silica_col], s=14, alpha=0.6, color=palette["series_1"])
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
                        self.empty_chart_message(ax, "Metallurgy: faltan columnas válidas.", module_name)

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
                            labels = self.shorten_labels(grouped.index.tolist(), 13)
                            ax.bar(labels, grouped.values, color=palette["series_5"])
                            ax.set_title("Equipos con fallas")
                            rendered = True

                    elif chart_type == "Falla vs no falla" and failure_col and metric1_col:
                        temp = df[[failure_col, metric1_col]].copy()
                        temp[failure_col] = self.to_numeric_series(temp[failure_col])
                        temp[metric1_col] = self.to_numeric_series(temp[metric1_col])
                        temp = temp.dropna()

                        if not temp.empty:
                            grouped = temp.groupby(failure_col)[metric1_col].mean()
                            labels = ["Sin falla" if i == 0 else "Con falla" for i in grouped.index.tolist()]
                            colors = [palette["series_1"], palette["series_5"]][:len(labels)]
                            ax.bar(labels, grouped.values, color=colors)
                            ax.set_title("Métrica por estado")
                            rendered = True

                    elif chart_type == "Distribución métrica" and metric1_col:
                        data = self.to_numeric_series(df[metric1_col]).dropna()
                        if not data.empty:
                            ax.hist(data, bins=20, color=palette["series_4"])
                            ax.set_title(f"Distribución {metric1_col}")
                            rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Maintenance: faltan columnas válidas.", module_name)

            except Exception:
                self.empty_chart_message(ax, "No se pudo renderizar.", module_name)

            self.apply_chart_margins(fig, ax, chart_type)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frames[module_name])
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)
        self.chart_canvases[module_name] = canvas