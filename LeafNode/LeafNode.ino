/*
  LEAF NODE / SENDER
  Fungsi:
  - Mengirim 500 paket ke mesh
  - Payload bisa diubah 32, 128, atau 512 byte
  - Paket dikirim broadcast, root akan mencatat data
*/

#include "painlessMesh.h"

#define MESH_PREFIX   "ESP_MESH_QOS_GRID"
#define MESH_PASSWORD "meshpassword123"
#define MESH_PORT     5555

// Identitas node sesuai grid
#define NODE_LABEL "LEAF_11"

// Ubah ini sesuai skenario:
// 1024, 128, atau 512
#define PAYLOAD_SIZE 512

// Jumlah paket sesuai skripsi
#define TOTAL_PACKETS 500

// Interval pengiriman.
// Untuk awal pakai 1000 ms agar stabil.
// Nanti bisa diturunkan, misalnya 500 ms atau 200 ms, asal konsisten di semua skenario.
#define SEND_INTERVAL_MS 1000

// Waktu tunggu awal agar mesh terbentuk dan waktu antar-node tersinkron
#define START_DELAY_MS 15000

Scheduler userScheduler;
painlessMesh mesh;

uint16_t seq = 0;
unsigned long lastSendMs = 0;
bool finished = false;

String makePayload(uint16_t sizeBytes) {
  String payload;
  payload.reserve(sizeBytes);

  for (uint16_t i = 0; i < sizeBytes; i++) {
    payload += char('A' + (i % 26));
  }

  return payload;
}

void sendPacket() {
  if (finished) return;

  if (seq >= TOTAL_PACKETS) {
    finished = true;
    Serial.println("# TEST_FINISHED");
    return;
  }

  // Jangan mulai kirim kalau belum ada node lain yang terhubung
  if (mesh.getNodeList().size() == 0) {
    Serial.println("# WAITING_FOR_ROOT");
    return;
  }

  String payload = makePayload(PAYLOAD_SIZE);

  uint32_t sentUs = mesh.getNodeTime();

  String msg;
  msg.reserve(PAYLOAD_SIZE + 180);

  msg += "{";
  msg += "\"type\":\"DATA\",";
  msg += "\"node\":\"";
  msg += NODE_LABEL;
  msg += "\",";
  msg += "\"seq\":";
  msg += seq;
  msg += ",";
  msg += "\"payloadBytes\":";
  msg += PAYLOAD_SIZE;
  msg += ",";
  msg += "\"sentUs\":";
  msg += sentUs;
  msg += ",";
  msg += "\"payload\":\"";
  msg += payload;
  msg += "\"";
  msg += "}";

  bool ok = mesh.sendBroadcast(msg);

  Serial.print("# SENT,seq=");
  Serial.print(seq);
  Serial.print(",payload=");
  Serial.print(PAYLOAD_SIZE);
  Serial.print(",sentUs=");
  Serial.print(sentUs);
  Serial.print(",status=");
  Serial.println(ok ? "OK" : "FAILED");

  seq++;
}

void receivedCallback(uint32_t from, String &msg) {
  Serial.print("# RX_FROM_");
  Serial.print(from);
  Serial.print(",");
  Serial.println(msg);
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

  Serial.println("# LEAF NODE STARTED");

  mesh.setDebugMsgTypes(ERROR | STARTUP | CONNECTION);

  mesh.init(MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT);

  // Leaf tahu bahwa jaringan punya root
  mesh.setContainsRoot(true);

  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
}

void loop() {
  mesh.update();

  if (millis() < START_DELAY_MS) {
    return;
  }

  if (!finished && millis() - lastSendMs >= SEND_INTERVAL_MS) {
    lastSendMs = millis();
    sendPacket();
  }
}