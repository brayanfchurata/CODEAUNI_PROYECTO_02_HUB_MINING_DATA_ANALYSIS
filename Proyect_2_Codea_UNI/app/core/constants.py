from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = BASE_DIR / "assets" / "icons"

APP_TITLE = "MineData Hub"
APP_SIZE = "1440x900"
APP_ICON = str(ASSETS_DIR / "app.ico")

MODULE_CONFIG = {
    "Inicio": {
        "icon_text": "⌂",
        "icon_path": str(ASSETS_DIR / "home.ico"),
        "description": "Vista general de la plataforma",
    },
    "Mining": {
        "icon_text": "⛏",
        "icon_path": str(ASSETS_DIR / "mining.ico"),
        "description": "Perforación, voladura y productividad",
        "required_columns": ["operator", "shift", "bench"],
    },
    "Geology": {
        "icon_text": "◉",
        "icon_path": str(ASSETS_DIR / "geology.ico"),
        "description": "Geoquímica de rocas y óxidos",
        "required_columns": ["rock_name", "SiO2n"],
    },
    "Metallurgy": {
        "icon_text": "⚗",
        "icon_path": str(ASSETS_DIR / "metallurgy.ico"),
        "description": "Flotación y control de sílice",
        "required_columns": ["date", "% Silica Concentrate", "% Iron Concentrate"],
    },
    "Maintenance": {
        "icon_text": "⚙",
        "icon_path": str(ASSETS_DIR / "maintenance.ico"),
        "description": "Monitoreo de equipos y fallas",
        "required_columns": ["date", "device", "failure"],
    },
}