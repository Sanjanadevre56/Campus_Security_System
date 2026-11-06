/*
  AI-Based Campus Security System - ESP32 Buzzer Hardware Controller
  
  Firmware Contract & HTTP API:
  -------------------------------------------------------------------
  Protocol: HTTP over Local Wi-Fi (Port 80)
  Endpoint: POST /trigger-buzzer
  Payload : {"event": "UNKNOWN_DETECTION", "alert_id": 102, "duration_ms": 3000}
  Response: HTTP 200 OK {"status": "success", "buzzer": "activated"}
  
  Hardware Connections:
  -------------------------------------------------------------------
  - ESP32 GPIO 12 -> Piezo Buzzer Positive (+) Lead
  - ESP32 GND     -> Piezo Buzzer Negative (-) Lead
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// Wi-Fi Access Point Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Hardware Pin Configuration
const int BUZZER_PIN = 12;

// Initialize HTTP Web Server on Port 80
WebServer server(80);

void handleRoot() {
  server.send(200, "application/json", "{\"status\": \"online\", \"device\": \"ESP32 Campus Security Buzzer Controller\"}");
}

void handleTriggerBuzzer() {
  if (server.method() != HTTP_POST) {
    server.send(405, "application/json", "{\"status\": \"error\", \"message\": \"Method Not Allowed. Use POST.\"}");
    return;
  }

  String requestBody = server.arg("plain");
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, requestBody);

  int duration_ms = 3000; // Default 3 second buzzer activation
  if (!error && doc.containsKey("duration_ms")) {
    duration_ms = doc["duration_ms"];
  }

  // Activate physical piezo buzzer
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duration_ms);
  digitalWrite(BUZZER_PIN, LOW);

  // Return HTTP 200 OK response payload
  server.send(200, "application/json", "{\"status\": \"success\", \"buzzer\": \"activated\", \"duration_ms\": " + String(duration_ms) + "}");
}

void handleNotFound() {
  server.send(404, "application/json", "{\"status\": \"error\", \"message\": \"Endpoint Not Found\"}");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("\n--- ESP32 Campus Security Controller ---");
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[✓] Wi-Fi Connected!");
  Serial.print("[*] Local IP Address: ");
  Serial.println(WiFi.localIP());

  // Bind Web Server HTTP Routes
  server.on("/", handleRoot);
  server.on("/trigger-buzzer", handleTriggerBuzzer);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("[✓] HTTP Web Server Started on Port 80.");
}

void loop() {
  server.handleClient();
}
