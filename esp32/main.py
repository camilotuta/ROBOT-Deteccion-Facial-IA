from machine import Pin, PWM
import network
import time
from umqtt.simple import MQTTClient
import ujson

# Configuracion
WIFI_SSID = "PETRA"
WIFI_PASSWORD = "PETRA2021"

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = b"facetracking/tuta/servo"  # Debe coincidir con el publisher
CLIENT_ID = b"esp32_servo_tuta"

SERVO_CONFIG = {
    "pan_pin": 26,
    "tilt_pin": 25,  # Pin correcto del servo 180
    "pan_center": 90,  # Centro del servo 360 (detenido)
    "tilt_center": 130,  # Centro del servo 180 (desde verify_servos.py)
}


class ServoController:
    def __init__(self):
        # Inicializar PWM a 50Hz
        print("Inicializando servos...")
        self.pan = PWM(Pin(SERVO_CONFIG["pan_pin"]), freq=50)
        self.tilt = PWM(Pin(SERVO_CONFIG["tilt_pin"]), freq=50)

        self.current_pan = SERVO_CONFIG["pan_center"]
        self.current_tilt = SERVO_CONFIG["tilt_center"]

        # Centrar servos
        self.pan.duty(self.angle_to_duty(self.current_pan))
        self.tilt.duty(self.angle_to_duty(self.current_tilt))
        time.sleep(0.1)

        # Configuración para servo 360 con pulsos
        self.pan_move_duration = 0.3  # 0.3 segundos por movimiento
        self.pan_left_angle = 95  # Ángulo para girar izquierda (> 90)
        self.pan_right_angle = 80  # Ángulo para girar derecha (< 90) - CORREGIDO
        self.pan_stop_angle = 90  # Ángulo para detener

        print("Servos listos!")

    def angle_to_duty(self, angle):
        min_duty = 26
        max_duty = 128
        duty = int(min_duty + (angle / 180.0) * (max_duty - min_duty))
        return duty

    def move_pan(self, direction, duration=None):
        """Mueve el servo 360 por el tiempo especificado en la dirección indicada
        direction: 'left', 'right', o 'stop'
        duration: tiempo en segundos (si es None, usa self.pan_move_duration)
        """
        if duration is None:
            duration = self.pan_move_duration

        if direction == "left":
            # Girar izquierda por el tiempo especificado
            self.pan.duty(self.angle_to_duty(self.pan_left_angle))
            time.sleep(duration)
            self.pan.duty(self.angle_to_duty(self.pan_stop_angle))
        elif direction == "right":
            # Girar derecha por el tiempo especificado
            self.pan.duty(self.angle_to_duty(self.pan_right_angle))
            time.sleep(duration)
            self.pan.duty(self.angle_to_duty(self.pan_stop_angle))
        elif direction == "stop":
            # Detener
            self.pan.duty(self.angle_to_duty(self.pan_stop_angle))

    def set_tilt(self, angle):
        """Mueve el servo 180 a un ángulo específico"""
        angle = max(60, min(160, angle))
        self.current_tilt = angle
        self.tilt.duty(self.angle_to_duty(angle))

    def move_to(self, pan_direction, tilt_angle, pan_duration=None):
        """Mueve ambos servos
        pan_direction: 'left', 'right', 'stop'
        tilt_angle: ángulo para servo 180
        pan_duration: tiempo en segundos para el movimiento del servo 360
        """
        # Solo mover tilt si hay un cambio significativo (más de 1 grado)
        if abs(tilt_angle - self.current_tilt) > 1:
            self.set_tilt(tilt_angle)

        # Mover pan (esto bloquea por el tiempo de duration si hay movimiento)
        self.move_pan(pan_direction, pan_duration)

    def center(self):
        self.move_pan("stop")
        self.set_tilt(SERVO_CONFIG["tilt_center"])


def connect_wifi():
    print("Conectando a WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        print("")
        print("WiFi conectado!")
        print("IP:", wlan.ifconfig()[0])
        return True
    else:
        print("")
        print("No se pudo conectar a WiFi")
        return False


# Variable global para el servo
servo = None
message_count = 0


def mqtt_callback(topic, msg):
    global servo, message_count
    try:
        data = ujson.loads(msg)
        pan_direction = data.get("pan_direction", "stop")  # 'left', 'right', 'stop'
        tilt = data.get("tilt", 130)  # Default al centro correcto
        duration = data.get("duration", None)  # Duración opcional para el pan
        update_tilt = data.get("update_tilt", True)  # Si debe actualizar el tilt
        tracking = data.get("tracking", False)

        # PRIMERO mover el pan (esto puede bloquear con time.sleep)
        servo.move_pan(pan_direction, duration)

        # DESPUÉS actualizar tilt si es necesario (no bloquea)
        if update_tilt:
            servo.set_tilt(tilt)

        message_count += 1
        status = "TRACKING" if tracking else "IDLE"

        # Imprimir cada 10 mensajes para no saturar
        if message_count % 10 == 0:
            dur_str = f"{duration}s" if duration else "default"
            tilt_str = "update" if update_tilt else "skip"
            print(
                "#" + str(message_count),
                status,
                "| Pan:",
                pan_direction,
                "(" + dur_str + ")",
                "Tilt:",
                round(tilt, 1),
                "(" + tilt_str + ")",
            )

    except Exception as e:
        print("Error procesando mensaje:", str(e))
        print("Mensaje:", msg)


print("=" * 50)
print("ESP32 Face Tracking - MQTT TIEMPO REAL")
print("=" * 50)

if not connect_wifi():
    print("Sistema detenido - No hay conexion WiFi")
    while True:
        time.sleep(1)

servo = ServoController()
print("Servos inicializados")
servo.center()
time.sleep(1)

print("Conectando a MQTT broker:", MQTT_BROKER)

try:
    client = MQTTClient(CLIENT_ID, MQTT_BROKER)
    client.set_callback(mqtt_callback)
    client.connect()
    client.subscribe(MQTT_TOPIC)
    print("Suscrito a:", MQTT_TOPIC)
    print("=" * 50)
    print("Sistema ACTIVO - Recibiendo en tiempo real...")
    print("")

    while True:
        client.check_msg()  # No bloqueante
        time.sleep(0.01)  # 10ms delay

except KeyboardInterrupt:
    print("")
    print("Deteniendo...")
    servo.center()
    client.disconnect()
    print("Desconectado")
except Exception as e:
    print("Error:", str(e))
    servo.center()
    try:
        client.disconnect()
    except:
        pass
