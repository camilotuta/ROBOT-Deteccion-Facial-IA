# Documentación del proyecto: Detección y seguimiento facial

> Resumen breve

Sistema de seguimiento facial en tiempo real que usa un modelo (Roboflow) para detectar personas/rostros, envía comandos de movimiento por MQTT y puede comandar un ESP32 por puerto serie para mover servos (pan/tilt). El repositorio contiene componentes para captura de cámara, inferencia, control PID y comunicación (MQTT / Serial / JSON file).

**Ubicación del documento**: `Deteccion Facial/DETECCION_FACIAL_DOC.md`


## Estructura general (resumen por módulo)
- **`main.py`**: Punto de entrada. Inicializa cámara, tracker, ESP32, MQTT y el archivo de posición; ciclo principal que procesa frames, envía comandos y muestra la interfaz.
- **`config.py`**: Parámetros de configuración: cámara, ESP32, servos, PID, y `ROBOFLOW_CONFIG` (modelo y API key). Aquí se toma `ROBOFLOW_API_KEY` desde la variable de entorno.
- **`camera_handler.py`**: Manejo de la cámara con OpenCV (iniciar, leer, detener).
- **`face_tracker.py`**: Lógica de inferencia y tracking: carga el modelo (llama a `get_model`), detecta, selecciona objetivo según `target_person`, calcula dirección/ángulos (sistema de pulsos) y dibuja anotaciones.
- **`inference.py`**: (importado por `face_tracker.py`) — función `get_model(...)` que instancia el cliente/objeto de inferencia (en este repo no se encontró un `inference.py` local; el patrón de uso está en `face_tracker.py`: `get_model(model_id, api_key)` y luego `model.infer(frame)`).
- **`pid_controller.py`**: Controlador PID simple para correcciones suaves (clase `PIDController`).
- **`esp32_controller.py`**: Comunicación serie con ESP32 usando `pyserial`, envía comandos CSV: `"pan,tilt\n"` y contiene métodos `connect`, `send_command`, `center_servos`, `close`.
- **`servo_file_manager.py`**: Guarda/lee `servo_position.json` con datos actuales (pan, tilt, tracking, target, error, timestamp).
- **`mqtt_sender.py`**: Envío de datos en tiempo real vía MQTT usando `paho-mqtt`. Implementa dos formatos: `send_position` (legacy) y `send_servo_command` (nuevo, con sistema de pulsos y duración).
- **`detection_logger.py`**: Logger que escribe en `detections_log.txt` resumen de detecciones y cambios de objetivo.


## Conexión con Roboflow (dónde y cómo)
Las referencias clave están en:
- `config.py` -> `ROBOFLOW_CONFIG`
- `face_tracker.py` -> carga del modelo y uso en `detect_faces`

Fragmentos relevantes (resumen, no todo el código):

- Configuración (poner la API key en variable de entorno):

```python
# config.py (parte relevante)
ROBOFLOW_CONFIG = {
    "model_id": "proyectoia-x1a1m/6",
    "api_key": os.environ.get("ROBOFLOW_API_KEY"),
    "confidence": 0.4,
    "tracking_confidence": 0.85,
}
```

- Inicialización y uso en `FaceTracker` (en `face_tracker.py`):

```python
# face_tracker.py (inicio)
self.model = get_model(
    model_id=ROBOFLOW_CONFIG["model_id"],
    api_key=ROBOFLOW_CONFIG["api_key"]
)

# uso (en detect_faces):
small_frame = cv2.resize(frame, None, fx=0.5, fy=0.5)
results = self.model.infer(small_frame)[0]
detections = sv.Detections.from_inference(results)
# escalar back si es necesario y filtrar por confianza:
mask = detections.confidence >= ROBOFLOW_CONFIG["confidence"]
detections = detections[mask]
```

Notas importantes sobre la conexión con Roboflow:
- La API key no debe subirse al repositorio. Se obtiene desde la variable de entorno `ROBOFLOW_API_KEY` o se puede inyectar localmente en `config.py` solo para pruebas.
- `get_model` devuelve un objeto con método `infer(frame)`; el código asume que `infer` devuelve una estructura compatible con `supervision.Detections.from_inference`.
- Se reduce el tamaño del frame (scale 0.5) para acelerar inferencia y luego se reescalan las cajas.

Si quieres que extraiga/añada el contenido exacto de `inference.py` (si está en otra carpeta o faltante), puedo buscarlo/añadir un helper de ejemplo para Roboflow.


## Implementación del modelo y flujo de inferencia (resumen técnico)
- Captura frame con `CameraHandler.read()`.
- En `FaceTracker.process_frame()` se llama `detect_faces()` según `TRACKING_CONFIG["detection_interval"]`.
- `detect_faces()`:
  - redimensiona frame para inferencia (ej. 0.5x), llama `model.infer()`,
  - convierte resultados a `Detections`, escala coordenadas de vuelta,
  - filtra detecciones por confianza (`ROBOFLOW_CONFIG["confidence"]`).
- `select_target_face()` aplica filtro por `class_name` (p.ej. "tuta" o "laura") y por confianza mínima `tracking_confidence_threshold`.
- Si se encuentra objetivo, `calculate_servo_angles()` devuelve una dirección de pan (`left`, `right`, `stop`) y un ajuste de tilt.


## Movimiento del robot (cómo se calcula y cómo se envía)
- Sistema híbrido: pulsos en pan y ángulo de tilt gradual.
- Lógica básica (en `face_tracker.py`):
  - Calcular error = target_center - frame_center.
  - Si |error_x| pequeño -> `pan_direction = "stop"`; si negativo -> `left`; si positivo -> `right`.
  - Para tilt se aplica un pequeño `tilt_step` y suavizado.
- Control PID:
  - Existe `PIDController` con `update(error)` que calcula P + I + D; actualmente `FaceTracker` utiliza un enfoque simple (en este código el cálculo de tilt usa suavizado explícito y el PID se inicializa pero su uso puede ser expandido para correcciones más precisas).
- Envío a actuadores:
  - **MQTT (principal en esta versión)**: `mqtt.send_servo_command(...)` envía un payload JSON con `pan_direction`, `tilt`, `duration`, `update_tilt`, `tracking`, `confidence`, `target`.
    - Ejemplo de payload publicado en `main.py`:

```json
{
  "pan_direction": "left",
  "tilt": 125.0,
  "duration": 0.15,
  "update_tilt": false,
  "tracking": true,
  "confidence": 0.72,
  "target": "tuta"
}
```

  - **ESP32 (opcional / legacy)**: envía por serie CSV `"{pan:.1f},{tilt:.1f}\n"`. El ESP32 debe interpretar esos valores y mover los servos.

- Archivo de posición `servo_position.json` se actualiza en cada iteración como backup/estado compartido.


## Puntos clave del código (fragmentos cortos y explicación)
- Cargar modelo (roboflow): ya mostrado arriba (ver `face_tracker.__init__`).

- Filtrado por confianza y escalado:
```python
# detect_faces
small = cv2.resize(frame, None, fx=0.5, fy=0.5)
results = model.infer(small)[0]
detections = sv.Detections.from_inference(results)
if len(detections) > 0:
    detections.xyxy = detections.xyxy / 0.5  # llevar de vuelta a tamaño original
mask = detections.confidence >= ROBOFLOW_CONFIG['confidence']
detections = detections[mask]
```

- Formato de envío por Serial (ESP32):
```python
# esp32_controller.py
command = f"{pan_angle:.1f},{tilt_angle:.1f}\n"
self.serial.write(command.encode())
```

- Sistema de pulsos MQTT (cómo decide duración):
```python
# main.py
if pan_dir == 'left': duration = 0.15
elif pan_dir == 'right': duration = 0.08
else: duration = 0.0
mqtt.send_servo_command(pan_direction=pan_dir, tilt=tilt_angle, duration=duration,...)
```


## Herramientas / dependencias usadas
- Python 3.x
- OpenCV (`cv2`) — captura y dibujos en pantalla
- numpy
- paho-mqtt (`paho.mqtt.client`) — comunicación MQTT
- pyserial (`serial`) — comunicación con ESP32
- supervision (`sv`) — estructura/ayudas para detecciones (se usa `Detections` y anotadores)
- Roboflow (API) — modelo de detección (a través de `get_model` / `model.infer`)


## Cómo configurar y ejecutar (rápido)
1. Instalar dependencias (ejemplo):

```powershell
pip install opencv-python numpy paho-mqtt pyserial supervision
# + cualquier librería necesaria para Roboflow client (si aplica)
```

2. Definir la API key de Roboflow en la variable de entorno:

```powershell
$env:ROBOFLOW_API_KEY = 'tu_api_key_aqui'
```

3. Ejecutar:

```powershell
python main.py
```

Notas:
- Ajusta `config.py` para cambiar `CAMERA_CONFIG`, `ROBOFLOW_CONFIG["model_id"]` o puertos de `ESP32_CONFIG`.
- Si no tienes ESP32 conectado, el sistema seguirá funcionando usando MQTT y el archivo JSON.


## Archivos importantes para revisar rápidamente
- `face_tracker.py` — inferencia, selección de objetivo y cálculo de movimiento.
- `config.py` — parámetros y dónde poner la API key.
- `mqtt_sender.py` — formato JSON publicado y cómo se envían comandos.
- `esp32_controller.py` — formato CSV serie que debe interpretar el firmware del ESP32.
- `servo_position.json` — archivo de estado generado por `ServoFileManager`.


## Sugerencias y próximos pasos (opcionales)
- Añadir o localizar `inference.py` para documentar exactamente la inicialización del cliente Roboflow. Si falta, puedo crear un helper ejemplo `inference.py` que muestre cómo usar la API de Roboflow.
- Si quieres que el PID controle activamente pan/tilt en lugar del sistema de pulsos, puedo integrar `PIDController.update(...)` en `FaceTracker.calculate_servo_angles()`.
- Añadir tests simples o un README con comandos de instalación y ejecución detallada.


---
Documento generado automáticamente: `Deteccion Facial/DETECCION_FACIAL_DOC.md`

Si quieres, lo adapto al formato README principal o lo traduzco a inglés. También puedo insertar más fragmentos de código concretos (p. ej. el contenido exacto de `inference.py`) si me indicas dónde está o si quieres que lo cree de ejemplo.