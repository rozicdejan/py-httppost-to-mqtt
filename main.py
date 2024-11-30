import os
import base64
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import paho.mqtt.client as mqtt
import threading
import time
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mqtt_gateway.log', encoding='utf-8')
    ]
)

# Configuration class
class Config:
    def __init__(self):
        self.MQTT_SERVER = os.getenv('MQTT_SERVER', 'localhost')
        self.MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
        self.MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
        self.MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
        self.HTTP_PORT = int(os.getenv('HTTP_PORT', 8088))
        self.HTTP_HOST = os.getenv('HTTP_HOST', '0.0.0.0')
        self.HTTP_USER = os.getenv('HTTP_USER', 'user')
        self.HTTP_PASSWORD = os.getenv('HTTP_PASSWORD', 'password')
        self.MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', 120))
        self.MAX_PAYLOAD_SIZE = int(os.getenv('MAX_PAYLOAD_SIZE', 1024 * 1024))  # 1MB default
        self.ALLOW_INSECURE = os.getenv('ALLOW_INSECURE', 'false').lower() == 'true'

config = Config()

# Counters for metrics
http_to_mqtt_count = 0
mqtt_reconnect_count = 0

class MQTTGatewayHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        """Add CORS headers for web applications."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _validate_authentication(self):
        """Validate Basic Authentication."""
        if config.ALLOW_INSECURE:
            return True

        auth = self.headers.get('Authorization')
        if not auth or not auth.startswith('Basic '):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="MQTT Gateway"')
            self._send_cors_headers()
            self.end_headers()
            return False

        try:
            credentials = base64.b64decode(auth.split(' ')[1]).decode('utf-8')
            username, password = credentials.split(':', 1)
            return username == config.HTTP_USER and password == config.HTTP_PASSWORD
        except Exception:
            return False

    def _extract_topic_from_path(self):
        """Normalize URL path to an MQTT topic."""
        topic = self.path.lstrip('/')
        topic = '/'.join([segment for segment in topic.split('/') if segment])  # Normalize slashes
        return topic

    def do_GET(self):
        """Handle GET requests."""
        global http_to_mqtt_count

        if self.path == "/ping":
            self._handle_ping()
            return

        if not self._validate_authentication():
            return

        topic = self._extract_topic_from_path()
        payload = ""

        if not topic:
            self.send_error(400, "Invalid topic format")
            return

        try:
            if self._handle_mqtt_publish(topic, payload):
                http_to_mqtt_count += 1
                self.send_response(200)
                self._send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({"status": "success", "topic": topic})
                self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            logging.error(f"GET request error: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def do_POST(self):
        """Handle POST requests."""
        global http_to_mqtt_count

        if not self._validate_authentication():
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            topic = self._extract_topic_from_path()

            if not topic:
                self.send_error(400, "Invalid topic format")
                return

            if len(body.encode('utf-8')) > config.MAX_PAYLOAD_SIZE:
                self.send_error(413, "Payload too large")
                return

            if self._handle_mqtt_publish(topic, body):
                http_to_mqtt_count += 1
                self.send_response(200)
                self._send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({"status": "success", "topic": topic, "payload": body})
                self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            logging.error(f"POST request error: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def _handle_ping(self):
        """Respond to /ping requests."""
        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "alive", "message": "Server is running"})
        self.wfile.write(response.encode('utf-8'))
        logging.info("Heartbeat received on /ping")

    def _handle_mqtt_publish(self, topic, payload, retain=False):
        """Publish to MQTT with reconnection logic."""
        global mqtt_reconnect_count

        if not mqtt_client.is_connected():
            try:
                logging.warning("[MQTT] Disconnected. Attempting to reconnect...")
                mqtt_client.reconnect()
                mqtt_reconnect_count += 1
                logging.info("[MQTT] Reconnected successfully.")
            except Exception as e:
                logging.error(f"[MQTT] Reconnect failed: {e}")
                self.send_error(503, "MQTT connection could not be established.")
                return False

        try:
            mqtt_client.publish(topic, payload, retain=retain)
            return True
        except Exception as e:
            logging.error(f"[MQTT] Publish error: {e}")
            return False

def create_mqtt_client():
    """Set up MQTT client."""
    client = mqtt.Client()
    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    def on_connect(client, userdata, flags, rc):
        logging.info(f"MQTT Connected with result code {rc}")

    def on_disconnect(client, userdata, rc):
        logging.warning(f"MQTT Disconnected with code {rc}")
        if rc != 0:
            logging.info("Unexpected disconnection. Attempting reconnect...")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(config.MQTT_SERVER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
        client.loop_start()
    except Exception as e:
        logging.error(f"MQTT Connection Failed: {e}")

    return client

def mqtt_health_check():
    """Periodically publish health metrics."""
    global mqtt_client, http_to_mqtt_count, mqtt_reconnect_count

    while True:
        try:
            health_topic = "http2mqtt/health"
            health_payload = json.dumps({
                "http_to_mqtt_count": http_to_mqtt_count,
                "mqtt_reconnect_count": mqtt_reconnect_count
            })
            mqtt_client.publish(health_topic, health_payload)
            logging.info(f"[MQTT] Published health check to {health_topic}: {health_payload}")
        except Exception as e:
            logging.error(f"[MQTT] Health check failed: {e}")

        time.sleep(config.MQTT_KEEPALIVE)

def run_server():
    """Start the HTTP server."""
    try:
        server_address = (config.HTTP_HOST, config.HTTP_PORT)
        httpd = HTTPServer(server_address, MQTTGatewayHandler)
        logging.info(f"HTTP to MQTT Gateway running on {config.HTTP_HOST}:{config.HTTP_PORT}")
        httpd.serve_forever()
    except Exception as e:
        logging.critical(f"Server startup failed: {e}")

if __name__ == '__main__':
    mqtt_client = create_mqtt_client()
    health_thread = threading.Thread(target=mqtt_health_check, daemon=True)
    health_thread.start()

    try:
        run_server()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
