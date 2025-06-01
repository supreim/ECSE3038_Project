#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DS18B20.h>
#include "../env.h"

// pins
#define ONE_WIRE_BUS 4
#define LIGHT 22
#define FAN 23 
#define PIR 15
#define STATUS_LED 2

//sensors
OneWire oneWire(ONE_WIRE_BUS);
DS18B20 sensor(&oneWire);


void send_temp_presence(float acquired_temp, int PIR_STATE);

void setup() {
  Serial.begin(115200);

  pinMode(FAN, OUTPUT);
  pinMode(LIGHT, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(PIR, INPUT);

  digitalWrite(FAN,LOW);
  digitalWrite(LIGHT,LOW);

  digitalWrite(STATUS_LED,HIGH);
  delay(1000);
  digitalWrite(STATUS_LED,LOW);
  delay(1000);

  sensor.begin();
  sensor.setResolution(12);
  sensor.setOffset(0.25);

  Serial.println("Hello ESP32!");
  WiFi.begin(SSID,PASS);

  digitalWrite(LIGHT,HIGH);
  delay(1000);
  digitalWrite(LIGHT,LOW);
  delay(1000);

  while(WiFi.status() != WL_CONNECTED){

    delay(500);
    Serial.print(".");
  }
  Serial.print("WiFi connected. IP address is: ");
  Serial.println(WiFi.localIP());

  delay(1000); 

}

void loop() {
  if(WiFi.status()==WL_CONNECTED){

    sensor.requestTemperatures();
    while(!sensor.isConversionComplete())
      delay(10);

    float acquired_temp = sensor.getTempC();
    if(acquired_temp != DEVICE_DISCONNECTED)
      {
        Serial.print("Present Temperature: ");
        Serial.println(acquired_temp);
      }
      else 
      {
        Serial.println("Temperature read failed");
        delay(100);
        return;
      }

      int PIR_STATE = digitalRead(PIR);
      Serial.print("Presence Detected: ");
      Serial.println(PIR_STATE);

      send_temp_presence(acquired_temp,PIR_STATE);
       delay(200);
  }
  else
  {
    Serial.println("WiFi connection Lost");
    WiFi.reconnect();
    delay(1000);
  }
  delay(100);
}
void send_temp_presence(float acquired_temp, int PIR_STATE){
  HTTPClient http;
  http.begin(String(ENDPOINT)+"/sensors_data");
  http.addHeader("Content-Type", "application/json");

  JsonDocument object_1;
  object_1["temperature"] = acquired_temp;
  object_1["presence"] = PIR_STATE;

  String request_body;
  serializeJson(object_1,request_body);

  Serial.print("Sending JSON: ");
  Serial.println(request_body);
  
  int responseCode = http.POST(request_body);
  if(responseCode == HTTP_CODE_OK )
  {
    String response = http.getString();
    Serial.print("API Response: ");
    Serial.println(response);

    JsonDocument object;
    DeserializationError error = deserializeJson(object,response);
    if(error){
      Serial.println("Deserialization failed: ");
      Serial.println(error.c_str());
    }else{
      const char *fan_status = object["fan"];
      const char *light_status = object["light"];

      if(strcmp(fan_status,"on")== 0){
        digitalWrite(FAN,HIGH);
        Serial.println("Cooling the place down");
      } else {
        digitalWrite(FAN,LOW);
        Serial.println("Place is cool");
      }

      if(strcmp(light_status, "on")==0){
        digitalWrite(LIGHT, HIGH);
        Serial.println("Light is ON");
      }else {
        digitalWrite(LIGHT, LOW);
        Serial.println("Light is OFF");
      }
      
    }
  } else{
    Serial.println("HTTP POST failed. Code: ");
    Serial.println(responseCode);
  }
  http.end();
}
