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
            "Maintenance": ctk.StringVar(value="Equipos críticos"),
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

    def card_border_color(self, level="default"):
        palette = self.get_palette()
        mapping = {
            "soft": palette.get("border_soft", palette["border"]),
            "default": palette["border"],
            "strong": "#C2CEDC",
            "analytics": "#B9C7D8",
        }
        return mapping.get(level, palette["border"])

    def card_background(self, kind="default"):
        palette = self.get_palette()
        mapping = {
            "default": palette.get("card_alt", palette["card"]),
            "panel": palette.get("panel", palette["card"]),
            "analytics": "#F7FAFC",
            "analytics_inner": "#FBFCFD",
        }
        return mapping.get(kind, palette.get("card_alt", palette["card"]))

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
                font=ctk.CTkFont(size=11),
                text_color="#7B8CA2",
                anchor="e",
                justify="right",
            ).grid(row=0, column=1, sticky="e", padx=(14, 0))

    def build_ui(self):
        palette = self.get_palette()
        status_info = self.module_status_data()

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

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkFrame(body, fg_color="transparent", width=295)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_col.grid_propagate(False)

        modules_card = ctk.CTkFrame(
            left_col,
            fg_color=self.card_background("default"),
            corner_radius=12,
            border_width=1,
            border_color=self.card_border_color("soft"),
        )
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
            "Metallurgy": "Flotación, sílice y estabilidad",
            "Maintenance": "Criticidad, riesgo y señales de falla",
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

        insights_card = ctk.CTkFrame(
            left_col,
            fg_color=self.card_background("default"),
            corner_radius=12,
            border_width=1,
            border_color=self.card_border_color("soft"),
        )
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

        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.grid_rowconfigure(1, weight=1)

        overview_card = ctk.CTkFrame(
            right_col,
            fg_color=self.card_background("default"),
            corner_radius=12,
            border_width=1,
            border_color=self.card_border_color("default"),
        )
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

        charts_card = ctk.CTkFrame(
            right_col,
            fg_color=self.card_background("analytics"),
            corner_radius=12,
            border_width=1,
            border_color=self.card_border_color("analytics"),
        )
        charts_card.pack(fill="both", expand=True)

        self.add_inline_header(
            charts_card,
            "Visual Summary",
            "Cada módulo muestra una visual de referencia. Puedes cambiar el tipo de gráfica desde el selector.",
        )

        charts_grid = ctk.CTkFrame(charts_card, fg_color="transparent")
        charts_grid.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        charts_grid.grid_columnconfigure((0, 1), weight=1)
        charts_grid.grid_rowconfigure((0, 1), weight=1)

        modules_chart_order = ["Mining", "Geology", "Metallurgy", "Maintenance"]
        for i, module_name in enumerate(modules_chart_order):
            row = i // 2
            col = i % 2
            accent = self.module_accent(module_name)

            chart_card = ctk.CTkFrame(
                charts_grid,
                fg_color=self.card_background("analytics_inner"),
                corner_radius=11,
                border_width=1,
                border_color=self.card_border_color("default"),
            )
            chart_card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            chart_card.grid_rowconfigure(1, weight=1)
            chart_card.grid_columnconfigure(0, weight=1)

            topbar = ctk.CTkFrame(chart_card, fg_color="transparent", height=36)
            topbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
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
            ).pack(side="left", pady=5)

            selector = ctk.CTkOptionMenu(
                topbar,
                values=self.get_chart_options(module_name),
                variable=self.chart_options[module_name],
                command=lambda _, m=module_name: self.render_module_chart(m),
                width=155,
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
                fg_color="#FCFDFE",
                corner_radius=9,
                border_width=1,
                border_color="#D6E0EA",
            )
            frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
            self.chart_frames[module_name] = frame

        for module_name in modules_chart_order:
            self.render_module_chart(module_name)

    def get_chart_options(self, module_name):
        return {
            "Mining": ["Top operadores", "Turnos", "Distribución M3"],
            "Geology": ["Boxplot SiO2", "SiO2 vs TiO2", "Top litologías"],
            "Metallurgy": [
                "Tendencia sílice",
                "Hierro vs sílice",
                "Variables asociadas",
                "Estabilidad proceso",
            ],
            "Maintenance": [
                "Equipos críticos",
                "Tendencia de falla",
                "Métricas discriminantes",
                "Comparación métrica foco",
            ],
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

    def get_failure_series(self, df):
        if df is None or "failure" not in df.columns:
            return pd.Series(dtype="int64")

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

    def maintenance_metric_columns(self, df):
        if df is None:
            return []
        return [c for c in df.columns if str(c).lower().startswith("metric")]

    def maintenance_metric_effects(self, df):
        if df is None or df.empty or "failure" not in df.columns:
            return pd.DataFrame()

        metric_cols = self.maintenance_metric_columns(df)
        if not metric_cols:
            return pd.DataFrame()

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
                    "effect_size": effect,
                    "abs_effect_size": abs(effect),
                    "mean_fail": mean_fail,
                    "mean_ok": mean_ok,
                }
            )

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows).sort_values("abs_effect_size", ascending=False)

    def maintenance_device_summary(self, df):
        if df is None or df.empty or "device" not in df.columns or "failure" not in df.columns:
            return pd.DataFrame()

        temp = df.copy()
        temp["failure_num"] = self.get_failure_series(df)

        grouped = temp.groupby("device").agg(
            records=("failure_num", "count"),
            failures=("failure_num", "sum"),
            failure_rate=("failure_num", "mean"),
        ).reset_index()

        grouped["criticality_score"] = (
            grouped["failures"] * 0.65
            + grouped["failure_rate"] * 100 * 0.35
        )

        return grouped.sort_values(["criticality_score", "failures", "failure_rate"], ascending=False)

    def apply_chart_margins(self, fig, ax, chart_type):
        ax.margins(x=0.04)

        if chart_type in {
            "Top operadores", "Turnos", "Top litologías", "Equipos con fallas",
            "Variables asociadas", "Equipos críticos", "Métricas discriminantes"
        }:
            for label in ax.get_xticklabels():
                label.set_rotation(18 if chart_type not in {"Variables asociadas", "Métricas discriminantes"} else 30)
                label.set_ha("right")
            fig.subplots_adjust(
                left=0.08, right=0.985, top=0.88,
                bottom=0.30 if chart_type in {"Variables asociadas", "Métricas discriminantes"} else 0.28
            )

        elif chart_type in {"Boxplot SiO2", "Comparación métrica foco"}:
            for label in ax.get_xticklabels():
                label.set_rotation(10)
                label.set_ha("right")
            fig.subplots_adjust(left=0.08, right=0.985, top=0.88, bottom=0.24)

        elif chart_type in {"Tendencia sílice", "Tendencia de falla"}:
            for label in ax.get_xticklabels():
                label.set_rotation(18)
                label.set_ha("right")
            fig.subplots_adjust(left=0.085, right=0.985, top=0.88, bottom=0.24)

        elif chart_type in {"SiO2 vs TiO2", "Hierro vs sílice"}:
            fig.subplots_adjust(left=0.10, right=0.985, top=0.88, bottom=0.16)

        elif chart_type in {"Estabilidad proceso"}:
            fig.subplots_adjust(left=0.10, right=0.985, top=0.88, bottom=0.18)

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
                            temp["day"] = temp[date_col].dt.date
                            agg = temp.groupby("day", as_index=False)[silica_col].mean()
                            agg["rolling_5"] = agg[silica_col].rolling(window=5, min_periods=2).mean()

                            ax.plot(
                                agg["day"],
                                agg[silica_col],
                                color=palette["series_3"],
                                linewidth=1.9,
                                alpha=0.75,
                                label="Promedio diario",
                            )
                            ax.plot(
                                agg["day"],
                                agg["rolling_5"],
                                color=palette["series_2"],
                                linewidth=2.2,
                                alpha=0.95,
                                label="Media móvil 5",
                            )

                            mean_value = agg[silica_col].mean()
                            if pd.notna(mean_value):
                                ax.axhline(
                                    mean_value,
                                    color=palette["series_5"],
                                    linestyle="--",
                                    linewidth=1.3,
                                    alpha=0.85,
                                )

                            ax.set_title("Tendencia sílice")
                            ax.set_xlabel("Fecha")
                            ax.set_ylabel("% SiO2")
                            ax.legend(fontsize=8)
                            rendered = True

                    elif chart_type == "Hierro vs sílice" and iron_col and silica_col:
                        temp = df[[iron_col, silica_col]].copy()
                        temp[iron_col] = self.to_numeric_series(temp[iron_col])
                        temp[silica_col] = self.to_numeric_series(temp[silica_col])
                        temp = temp.dropna().head(1800)

                        if not temp.empty:
                            corr_value = temp[[iron_col, silica_col]].corr(numeric_only=True).iloc[0, 1]
                            ax.scatter(temp[iron_col], temp[silica_col], s=14, alpha=0.6, color=palette["series_1"])
                            ax.set_title(f"Hierro vs sílice | Corr: {corr_value:.3f}")
                            ax.set_xlabel("% Fe")
                            ax.set_ylabel("% SiO2")
                            rendered = True

                    elif chart_type == "Variables asociadas" and silica_col:
                        numeric_df = df.copy()
                        numeric_candidates = []
                        for col in numeric_df.columns:
                            try:
                                series = pd.to_numeric(numeric_df[col], errors="coerce")
                                if series.notna().sum() >= 20 and series.nunique(dropna=True) > 1:
                                    numeric_candidates.append(col)
                            except Exception:
                                continue

                        if silica_col in numeric_candidates and len(numeric_candidates) >= 2:
                            corr = numeric_df[numeric_candidates].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)[silica_col].dropna()
                            corr = corr.drop(labels=[silica_col], errors="ignore")
                            corr = corr.sort_values(key=lambda s: s.abs(), ascending=False).head(6)

                            if not corr.empty:
                                colors = [palette["series_3"] if v >= 0 else palette["series_5"] for v in corr.values]
                                ax.bar(corr.index.astype(str), corr.values, color=colors, edgecolor=palette["accent"], alpha=0.88)
                                ax.axhline(0, color=palette["chart_axis"], linewidth=1.0, alpha=0.9)
                                ax.set_title("Variables asociadas a sílice")
                                ax.set_ylabel("Correlación")
                                rendered = True

                    elif chart_type == "Estabilidad proceso" and silica_col:
                        data = self.to_numeric_series(df[silica_col]).dropna()

                        if len(data) >= 12:
                            rolling_std = data.rolling(window=5, min_periods=3).std().dropna()
                            if not rolling_std.empty:
                                ax.plot(
                                    rolling_std.index,
                                    rolling_std.values,
                                    color=palette["series_3"],
                                    linewidth=2.0,
                                    alpha=0.92,
                                )

                                mean_std = rolling_std.mean()
                                if pd.notna(mean_std):
                                    ax.axhline(
                                        mean_std,
                                        color=palette["series_2"],
                                        linestyle="--",
                                        linewidth=1.3,
                                        alpha=0.9,
                                    )

                                ax.set_title("Estabilidad del proceso")
                                ax.set_xlabel("Ventanas sucesivas")
                                ax.set_ylabel("Std móvil sílice")
                                rendered = True

                    if not rendered:
                        self.empty_chart_message(ax, "Metallurgy: faltan columnas válidas.", module_name)

                elif module_name == "Maintenance":
                    if chart_type == "Equipos críticos":
                        summary = self.maintenance_device_summary(df)
                        if not summary.empty:
                            top = summary.head(6)
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
                            rendered = True

                    elif chart_type == "Tendencia de falla":
                        date_col = self.find_column(df, ["date", "fecha"])
                        if date_col and "failure" in df.columns:
                            temp = df[[date_col]].copy()
                            temp["failure_num"] = self.get_failure_series(df)
                            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce", dayfirst=True)
                            temp = temp.dropna(subset=[date_col])

                            if not temp.empty:
                                temp["day"] = temp[date_col].dt.date
                                grouped = temp.groupby("day").agg(
                                    records=("failure_num", "count"),
                                    failures=("failure_num", "sum"),
                                ).reset_index()
                                grouped["failure_rate"] = grouped["failures"] / grouped["records"]
                                grouped["rolling_rate"] = grouped["failure_rate"].rolling(window=7, min_periods=2).mean()

                                ax.plot(
                                    grouped["day"],
                                    grouped["failure_rate"] * 100,
                                    color=palette["series_1"],
                                    linewidth=1.4,
                                    alpha=0.70,
                                    label="Tasa diaria",
                                )
                                ax.plot(
                                    grouped["day"],
                                    grouped["rolling_rate"] * 100,
                                    color=palette["series_2"],
                                    linewidth=2.2,
                                    alpha=0.95,
                                    label="Media móvil 7",
                                )
                                ax.set_title("Tendencia de falla")
                                ax.set_xlabel("Fecha")
                                ax.set_ylabel("Tasa (%)")
                                ax.legend(fontsize=8)
                                rendered = True

                    elif chart_type == "Métricas discriminantes":
                        effects = self.maintenance_metric_effects(df)
                        if not effects.empty:
                            top = effects.head(6)
                            colors = [palette["series_3"] if v >= 0 else palette["series_5"] for v in top["effect_size"]]
                            ax.bar(
                                top["metric"].astype(str),
                                top["effect_size"],
                                color=colors,
                                edgecolor=palette["accent"],
                                alpha=0.88,
                            )
                            ax.axhline(0, color=palette["chart_axis"], linewidth=1.0, alpha=0.9)
                            ax.set_title("Métricas discriminantes")
                            ax.set_ylabel("Efecto estandarizado")
                            rendered = True

                    elif chart_type == "Comparación métrica foco":
                        effects = self.maintenance_metric_effects(df)
                        metric_col = str(effects.iloc[0]["metric"]) if not effects.empty else None

                        if metric_col and metric_col in df.columns and "failure" in df.columns:
                            temp = pd.DataFrame({
                                "metric": pd.to_numeric(df[metric_col], errors="coerce"),
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

                                    ax.set_title(f"Comparación {metric_col}")
                                    ax.set_ylabel(metric_col)
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