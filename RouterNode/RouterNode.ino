/*
  ROUTER NODE / RELAY NODE
  Fungsi:
  - Bergabung ke jaringan mesh
  - Tidak mengirim data pengujian
  - Menjadi node perantara / relay secara otomatis
*/

#include "painlessMesh.h"

#define MESH_PREFIX   "ESP_MESH_QOS_GRID"
#define MESH_PASSWORD "meshpassword123"
#define MESH_PORT     5555

// Ubah sesuai posisi router
// Router kanan atas: "ROUTER_01"
// Router kiri bawah: "ROUTER_10"
#define NODE_LABEL "ROUTER_07"

Scheduler userScheduler;
painlessMesh mesh;

void receivedCallback(uint32_t from, String &msg) {
  // Router tidak perlu mencatat data utama.
  // Ini hanya untuk debugging.
  Serial.print("# ROUTER_RX,");
  Serial.print(NODE_LABEL);
  Serial.print(",from=");
  Serial.print(from);
  Serial.print(",len=");
  Serial.println(msg.length());
}

void newConnectionCallback(uint32_t nodeId) {
  Serial.print("# NEW_CONNECTION,");
  Serial.print(NODE_LABEL);
  Serial.print(",nodeId=");
  Serial.println(nodeId);
}

void changedConnectionCallback() {
  Serial.print("# CONNECTION_CHANGED,");
  Serial.print(NODE_LABEL);
  Serial.print(",knownNodes=");
  Serial.println(mesh.getNodeList().size());
}

void nodeTimeAdjustedCallback(int32_t offset) {
  Serial.print("# TIME_ADJUSTED,");
  Serial.print(NODE_LABEL);
  Serial.print(",offset=");
  Serial.println(offset);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.print("# ROUTER NODE STARTED,");
  Serial.println(NODE_LABEL);

  mesh.setDebugMsgTypes(ERROR | STARTUP | CONNECTION);

  mesh.init(MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT);

  // Router tahu bahwa jaringan memiliki root
  mesh.setContainsRoot(true);

  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
}

void loop() {
  mesh.update();
}