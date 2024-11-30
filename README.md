# MQTT Gateway
This project provides an HTTP-to-MQTT gateway. It allows you to send HTTP requests (GET/POST) to publish messages to an MQTT broker. The gateway supports basic authentication, custom configurations via a .env file, and health monitoring through a /ping endpoint.

## Features
Publish messages to an MQTT broker via HTTP.
Supports GET, POST, PUT, and DELETE methods.
Basic authentication for secure communication.
Configurable via a .env file.
/ping endpoint for server health checks.
Detailed logging to mqtt_gateway.log.
### Prerequisites
Python 3.8 or higher
pip for managing Python packages
MQTT broker (e.g., Mosquitto)

# Setup
## Step 1: Clone the Repository
```yaml
git clone https://github.com/rozicdejan/py-httppost-to-mqtt
cd py-httppost-to-mqtt
```
## Step 2: Install Dependencies
```yaml
pip install -r requirements.txt
```
## Step 3: Create a .env File
Create a .env file in the project directory and populate it with the following variables:
```yaml
# MQTT Configuration
MQTT_SERVER=your_mqtt_broker_address
MQTT_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password

# HTTP Server Configuration
HTTP_PORT=8088
HTTP_HOST=0.0.0.0
HTTP_USER=your_http_user
HTTP_PASSWORD=your_http_password

# Advanced Settings
MQTT_KEEPALIVE=120
MAX_PAYLOAD_SIZE=1048576  # 1 MB
ALLOW_INSECURE=false
Replace the placeholder values with your actual configuration.
```
## Usage
Run the Gateway
Execute the main script:

```yaml
python main.py
```

HTTP Endpoints
POST: Publish messages to an MQTT topic.

Example:
```yaml
curl -X POST -u user:password -d "Hello, MQTT!" http://localhost:8088/mqtt/test
```

Publishes the payload (Hello, MQTT!) to the MQTT topic mqtt/test.
GET: Perform health checks or test message publishing.

Health Check:
``` yaml
curl -X GET http://localhost:8088/ping
```
Response:
``` yaml
{ "status": "alive", "message": "Server is running" }
```
DELETE: Publish a zero-byte retained message to a topic.

Example:
bash
``` yaml
curl -X DELETE -u user:password http://localhost:8088/mqtt/test
```

## Logging
Logs are stored in the mqtt_gateway.log file. You can view real-time logs in the console or review the log file for detailed information about requests and MQTT interactions.

### Troubleshooting
MQTT Connection Issues:

Ensure your MQTT broker is running and reachable.
Check the MQTT_SERVER and MQTT_PORT values in your .env file.
Authentication Errors:

Verify HTTP_USER and HTTP_PASSWORD in the .env file.
Ensure your curl requests include the correct credentials.
Payload Too Large:

Increase the MAX_PAYLOAD_SIZE in the .env file if needed.
