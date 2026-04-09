import customtkinter as ctk

from app.ui.shared_widgets import make_title, make_subtitle, make_card
from app.core.constants import MODULE_CONFIG
from app.ui.styles import PALETTE


class HomeView(ctk.CTkFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        self.app_state = app_state
        self.build_ui()

    def get_palette(self):
        try:
            return self.master.master.palette
        except Exception:
            return PALETTE

    def module_status_data(self):
        rows = []
        datasets_loaded = 0
        total_records = 0
        alerts = 0

        for module_name in ["Mining", "Geology", "Metallurgy", "Maintenance"]:
            df = self.app_state.get_dataset(module_name)

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
        }

    def build_ui(self):
        palette = self.get_palette()
        status_info = self.module_status_data()

        # Header
        title = make_title(self, "MineData Hub")
        title.pack(anchor="w", padx=20, pady=(20, 6))

        subtitle = make_subtitle(
            self,
            "Plataforma integrada de analítica minera con módulos de Mining, Geology, Metallurgy y Maintenance.",
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 12))

        loaded = status_info["datasets_loaded"]
        total_records = status_info["total_records"]

        if loaded == 0:
            headline = "Sistema listo para comenzar. Aún no hay datasets cargados."
        else:
            headline = f"Sistema activo: {loaded}/4 módulos con data cargada, {total_records:,} registros acumulados."

        headline_card = make_card(self)
        headline_card.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            headline_card,
            text="Estado general del sistema",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            headline_card,
            text=headline,
            text_color=palette["muted"],
            wraplength=1200,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Cards de módulos
        modules_grid = ctk.CTkFrame(self, fg_color="transparent")
        modules_grid.pack(fill="x", padx=14, pady=(0, 12))
        modules_grid.grid_columnconfigure((0, 1), weight=1)

        modules = [m for m in MODULE_CONFIG.keys() if m != "Inicio"]
        for i, module_name in enumerate(modules):
            row = i // 2
            col = i % 2
            cfg = MODULE_CONFIG[module_name]

            card = make_card(modules_grid)
            card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

            ctk.CTkLabel(
                card,
                text=f"{cfg['icon']} {module_name}",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=16, pady=(16, 8))

            ctk.CTkLabel(
                card,
                text=cfg["description"],
                wraplength=420,
                justify="left",
                text_color=palette["muted"],
            ).pack(anchor="w", padx=16, pady=(0, 16))

        # Zona inferior
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=14, pady=(6, 14))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=4)
        bottom.grid_rowconfigure(0, weight=1)

        # Panel izquierdo
        left_panel = make_card(bottom)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(
            left_panel,
            text="Project / Contact",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 10))

        contact_lines = [
            ("Autor", "Brayan Churata"),
            ("Programa", "CODEa UNI"),
            ("Versión", "1.0"),
            ("Correo", "brayan.churata@dataminesoftware.com"),
            ("Estado", "Operativo"),
        ]

        for label, value in contact_lines:
            row = ctk.CTkFrame(left_panel, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=5)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=78,
                anchor="w",
                text_color=palette["muted"],
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                anchor="w",
                wraplength=190,
                justify="left",
                text_color=palette["text"],
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(left_panel, fg_color="transparent", height=10).pack()

        ctk.CTkLabel(
            left_panel,
            text="MineData Hub integra módulos especializados para exploración, operación, planta y mantenimiento.",
            wraplength=220,
            justify="left",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(8, 14))

        # Panel derecho
        right_panel = make_card(bottom)
        right_panel.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            right_panel,
            text="System Overview",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            right_panel,
            text="Resumen ejecutivo del sistema y estado actual de los módulos.",
            text_color=palette["muted"],
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # KPIs
        kpi_wrap = ctk.CTkFrame(right_panel, fg_color="transparent")
        kpi_wrap.pack(fill="x", padx=12, pady=(0, 14))
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
                corner_radius=14,
                border_width=1,
                border_color=palette["border"],
            )
            card.grid(row=0, column=i, sticky="nsew", padx=6, pady=4)

            ctk.CTkLabel(
                card,
                text=label,
                text_color=palette["muted"],
            ).pack(anchor="w", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                card,
                text=value,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=palette["text"],
            ).pack(anchor="w", padx=12, pady=(0, 10))

        # Estado por módulo
        status_card = ctk.CTkFrame(
            right_panel,
            fg_color=palette["panel"],
            corner_radius=16,
            border_width=1,
            border_color=palette["border"],
        )
        status_card.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        ctk.CTkLabel(
            status_card,
            text="Module Status",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=palette["text"],
        ).pack(anchor="w", padx=14, pady=(14, 10))

        header = ctk.CTkFrame(status_card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(0, 6))

        headers = ["Módulo", "Estado", "Registros", "Última acción"]
        widths = [150, 120, 120, 200]

        for text, width in zip(headers, widths):
            ctk.CTkLabel(
                header,
                text=text,
                width=width,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
                text_color=palette["muted"],
            ).pack(side="left", padx=(0, 8))

        for module, status, records, action in status_info["rows"]:
            row = ctk.CTkFrame(status_card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=4)

            values = [module, status, records, action]
            for value, width in zip(values, widths):
                ctk.CTkLabel(
                    row,
                    text=value,
                    width=width,
                    anchor="w",
                    text_color=palette["text"],
                ).pack(side="left", padx=(0, 8))

        footer = ctk.CTkFrame(right_panel, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 14))

        if loaded == 0:
            footer_text = "Comienza seleccionando un módulo desde la barra lateral e importando un dataset."
        else:
            footer_text = "Ya hay información cargada. Puedes volver a cualquier módulo para continuar el análisis."

        ctk.CTkLabel(
            footer,
            text=footer_text,
            text_color=palette["muted"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w")