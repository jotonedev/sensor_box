#ifndef CONF_H
#define CONF_H

#include "Arduino.h"

const char *SSID = "";
const char *PASS = "";
const char *BSSID = "";

const char *BROKER = "mqtt.local";
const char *CLIENT_ID = "SensorBox01";
const int BROKER_PORT = 1883;

const char *topic_temp = "box01/temperature";
const char *topic_hum = "box01/humidity";
const char *topic_pres = "box01/pressure";
const char *topic_caqi = "box01/caqi";
const char *topic_eco2 = "box01/eco2";
const char *topic_tvoc = "box01/tvoc";
const char *topic_pm01 = "box01/pm01";
const char *topic_pm25 = "box01/pm25";
const char *topic_pm100 = "box01/pm100";
const char *topic_h2 = "box01/h2";
const char *topic_ethanol = "box01/ethanol";
const char *topic_err = "box01/error";

#endif