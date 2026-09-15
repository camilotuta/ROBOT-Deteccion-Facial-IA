# cSpell: disable
# pylint: disable=all
# ruff: noqa
import os

CAMERA_CONFIG = {"index": 0, "width": 640, "height": 480, "fps": 30}

ESP32_CONFIG = {
    "port": "COM7",
    "baudrate": 115200,
    "timeout": 1,
}

SERVO_CONFIG = {
    "pan_center": 90,
    "tilt_center": 90,
    "pan_range": (0, 180),
    "tilt_range": (30, 150),
    "max_speed": 8,  # Aumentado para movimiento más rápido
}

ROBOFLOW_CONFIG = {
    "model_id": "proyectoia-x1a1m/6",
    # Por seguridad la API key se toma de la variable de entorno ROBOFLOW_API_KEY.
    # En desarrollo puede asignarse aquí como cadena, pero NO subirla al repo.
    "api_key": os.environ.get("ROBOFLOW_API_KEY"),
    "confidence": 0.4,  # Reducido para mejor detección
    "tracking_confidence": 0.85,  # Reducido de 0.90 a 0.85
}

TRACKING_CONFIG = {
    "detection_interval": 1,  # Detectar en cada frame para mejor fluidez
    "smoothing_factor": 0.5,  # Aumentado para movimiento más suave
    "target_person": None,
    "debug_mode": True,
    "frame_skip": 1,  # Procesar cada frame (1 = sin saltos)
}

PID_CONFIG = {
    "pan": {"kp": 0.20, "ki": 0.015, "kd": 0.12},  # Aumentado para respuesta más rápida
    "tilt": {"kp": 0.20, "ki": 0.015, "kd": 0.12},
}

DEADZONE = {"x": 15, "y": 15}  # Reducido para mejor centrado

# Archivo JSON para compartir datos con ESP32
SERVO_DATA_FILE = "servo_position.json"

# Colores para cada persona (BGR)
PERSON_COLORS = {
    "tuta": (255, 0, 0),  # Azul
    "laura": (0, 255, 0),  # Verde
    "unknown": (128, 128, 128),  # Gris
}
