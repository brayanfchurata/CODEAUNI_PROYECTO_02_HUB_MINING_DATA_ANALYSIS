APP_TITLE = "MineData Hub"
APP_SIZE = "1440x900"

MODULE_CONFIG = {
    "Inicio": {
        "icon": "🏠",
        "description": "Vista general de la plataforma",
    },
    "Mining": {
        "icon": "⛏️",
        "description": "Perforacion, voladura y productividad",
        "required_columns": ["operator", "shift", "bench"],
    },
    "Geology": {
        "icon": "🪨",
        "description": "Geoquimica de rocas y oxidos",
        "required_columns": ["rock_name", "SiO2n"],
    },
    "Metallurgy": {
        "icon": "⚗️",
        "description": "Flotacion y control de silica",
        "required_columns": ["date", "% Silica Concentrate", "% Iron Concentrate"],
    },
    "Maintenance": {
        "icon": "🛠️",
        "description": "Monitoreo de equipos y fallas",
        "required_columns": ["date", "device", "failure"],
    },
}