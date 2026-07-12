/*
  ROOT NODE / GATEWAY
  Fungsi:
  - Menerima paket dari leaf/source node
  - Menghitung latency berdasarkan waktu mesh
  - Mencetak data CSV ke Serial Monitor
*/

#include "painlessMesh.h"
#include <ArduinoJson.h>

#define MESH_PREFIX   "ESP_MESH_QOS_GRID"
#define MESH_PASSWORD "meshpassword123"
#define MESH_PORT     5555

// Ubah sesuai skenario grid pengujian 2x2, 3x3
// jarak 1,3,5,10

#define TOPOLOGY_NAME "2x2"
#define DISTANCE_M    "1"

Scheduler userScheduler;
painlessMesh mesh;

unsigned long receivedCount = 0;

void receivedCallback(uint32_t from, String &msg) {
  DynamicJsonDocument doc(2048);

  DeserializationError error = deserializeJson(doc, msg);
  if (error) {
    Serial.print("# JSON_PARSE_ERROR,from=");
    Serial.print(from);
    Serial.print(",msg=");
    Serial.println(msg);
    return;
  }

  const char* type = doc["type"] | "";
  if (strcmp(type, "DATA") != 0) {
    return;
  }

  const char* sourceLabel = doc["node"] | "UNKNOWN";
  uint16_t seq = doc["seq"] | 0;
  uint16_t payloadBytes = doc["payloadBytes"] | 0;

  // Waktu kirim dari node pengirim berdasarkan mesh time
  uint32_t sentUs = doc["sentUs"] | 0;

  // Waktu diterima di root berdasarkan mesh time
  uint32_t recvUs = mesh.getNodeTime();

  // Selisih waktu dalam milidetik
  float latencyMs = (int32_t)(recvUs - sentUs) / 1000.0;

  receivedCount++;

  // Format CSV:
  // topology,distance_m,payload_bytes,from_node,source_label,seq,sent_us,recv_us,latency_ms,msg_length
  Serial.print(TOPOLOGY_NAME);
  Serial.print(",");
  Serial.print(DISTANCE_M);
  Serial.print(",");
  Serial.print(payloadBytes);
  Serial.print(",");
  Serial.print(from);
  Serial.print(",");
  Serial.print(sourceLabel);
  Serial.print(",");
  Serial.print(seq);
  Serial.print(",");
  Serial.print(sentUs);
  Serial.print(",");
  Serial.print(recvUs);
  Serial.print(",");
  Serial.print(latencyMs, 3);
  Serial.print(",");
  Serial.println(msg.length());
}

void newConnectionCallback(uint32_t nodeId) {
  Serial.print("# NEW_CONNECTION,nodeId=");
  Serial.println(nodeId);
}

void changedConnectionCallback() {
  Serial.print("# CONNECTION_CHANGED,totalKnownNodes=");
  Serial.println(mesh.getNodeList().size());
}

void nodeTimeAdjustedCallback(int32_t offset) {
  Serial.print("# TIME_ADJUSTED,offset=");
  Serial.println(offset);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("# ROOT NODE STARTED");
  Serial.println("# CSV_HEADER");
  Serial.println("topology,distance_m,payload_bytes,from_node,source_label,seq,sent_us,recv_us,latency_ms,msg_length");

  mesh.setDebugMsgTypes(ERROR | STARTUP | CONNECTION);

  mesh.init(MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT);

  // Root/gateway utama
  mesh.setRoot(true);
  mesh.setContainsRoot(true);

  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
}

void loop() {
  mesh.update();
}