import customtkinter as ctk

from app.core.constants import APP_TITLE, APP_SIZE, MODULE_CONFIG
from app.core.app_state import AppState
from app.ui.styles import THEMES
from app.modules.home_view import HomeView
from app.modules.mining_view import MiningView
from app.modules.geology_view import GeologyView
from app.modules.metallurgy_view import MetallurgyView
from app.modules.maintenance_view import MaintenanceView


class Proyect2CodeaUNI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.app_state = AppState()
        self.palette = THEMES[self.app_state.current_theme]

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.configure(fg_color=self.palette["bg"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = None
        self.content = None
        self.current_view = None

        # cache de vistas
        self.views = {}

        self.build_sidebar()
        self.build_content()
        self.show_view("Inicio")

    def build_sidebar(self):
        if self.sidebar is not None:
            self.sidebar.destroy()

        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            corner_radius=0,
            fg_color=self.palette["surface"],
            border_width=1,
            border_color=self.palette["border"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text=APP_TITLE,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.palette["text"],
        ).pack(anchor="w", padx=20, pady=(24, 8))

        ctk.CTkLabel(
            self.sidebar,
            text="Analítica minera integrada",
            text_color=self.palette["muted"],
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            self.sidebar,
            text="Tema visual",
            text_color=self.palette["muted"],
        ).pack(anchor="w", padx=20, pady=(6, 6))

        theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=list(THEMES.keys()),
            command=self.change_theme,
            fg_color=self.palette["panel"],
            button_color=self.palette["primary"],
            button_hover_color=self.palette["primary_hover"],
        )
        theme_menu.set(self.app_state.current_theme)
        theme_menu.pack(fill="x", padx=14, pady=(0, 16))

        for module_name, cfg in MODULE_CONFIG.items():
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{cfg['icon']}  {module_name}",
                anchor="w",
                corner_radius=12,
                fg_color=self.palette["panel"],
                hover_color=self.palette["primary_hover"],
                text_color=self.palette["text"],
                command=lambda m=module_name: self.show_view(m),
            )
            btn.pack(fill="x", padx=14, pady=6)

    def build_content(self):
        if self.content is None:
            self.content = ctk.CTkFrame(self, fg_color="transparent")
            self.content.grid(row=0, column=1, sticky="nsew")
            self.content.grid_rowconfigure(0, weight=1)
            self.content.grid_columnconfigure(0, weight=1)

    def change_theme(self, theme_name: str):
        self.app_state.set_theme(theme_name)
        self.palette = THEMES[theme_name]
        self.configure(fg_color=self.palette["bg"])

        # destruir vistas cacheadas para recrearlas con el nuevo tema
        for view in self.views.values():
            view.destroy()

        self.views = {}
        self.current_view = None

        self.build_sidebar()
        self.show_view(self.app_state.current_module)

    def create_view(self, module_name: str):
        if module_name == "Inicio":
            return HomeView(self.content, self.app_state)
        elif module_name == "Mining":
            return MiningView(self.content, self.app_state)
        elif module_name == "Geology":
            return GeologyView(self.content, self.app_state)
        elif module_name == "Metallurgy":
            return MetallurgyView(self.content, self.app_state)
        elif module_name == "Maintenance":
            return MaintenanceView(self.content, self.app_state)
        else:
            return HomeView(self.content, self.app_state)

    def show_view(self, module_name: str):
        self.app_state.set_module(module_name)

        # La Home siempre se refresca para mostrar el estado actual
        if module_name == "Inicio" and module_name in self.views:
            self.views[module_name].destroy()
            del self.views[module_name]

        if module_name not in self.views:
            view = self.create_view(module_name)
            self.views[module_name] = view
            view.grid(row=0, column=0, sticky="nsew")

        for name, view in self.views.items():
            if name == module_name:
                view.grid()
                view.tkraise()
            else:
                view.grid_remove()

        self.current_view = self.views[module_name]