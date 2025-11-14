#!/usr/bin/env python3
#*- coding: utf-8 -*-

"""
Raspberry Pi 5 + PiicoDev BME280 -> AWS IoT Core (MQTT, mTLS)
Reads temp (°C), pressure (hPa), humidity (%RH) via PiicoDev_BME280().values()
Publishes JSON to a topic using device certificates in /home/icp/aws
"""

import json
import os
import sys
import time
import socket
from datetime import datetime, timezone

from PiicoDev_BME280 import PiicoDev_BME280
from awscrt import io, mqtt, exceptions
from awsiot import mqtt_connection_builder

# ===================== USER CONFIG =====================
# Your AWS IoT ATS endpoint (Sydney / ap-southeast-2 for your account)
ENDPOINT   = "a1ajomln5m8rkh-ats.iot.ap-southeast-2.amazonaws.com"

# Logical device identity and topics
CLIENT_ID  = "minimart-wa-bentley-sensor-1"
THING_NAME = "minimart-wa-bentley-sensor-1"            # update to your actual Thing name if you like
TOPIC_DATA = "minimart/wa/bentley/sensor/1"         # data topic
TOPIC_STAT = "minimart/wa/bentley/sensor/1/status"  # status/LWT topic

# Certificate paths (stored in /home/icp/aws)
AWS_DIR    = "/home/icp/aws"
CERT_FILE  = os.path.join(AWS_DIR, "minimart-wa-bentley-sensor-1.cert.pem")
KEY_FILE   = os.path.join(AWS_DIR, "minimart-wa-bentley-sensor-1.private.key")
CA_FILE    = os.path.join(AWS_DIR, "AmazonRootCA1.pem")  # use Amazon Root CA 1

# Publish cadence
PUBLISH_PERIOD_SEC = 15
KEEP_ALIVE_SECS    = 60
# =======================================================


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def check_files(*paths):
    ok = True
    for p in paths:
        if not os.path.isfile(p):
            print(f"[ERROR] Missing file: {p}", file=sys.stderr)
            ok = False
    if not ok:
        sys.exit(1)


def on_connection_interrupted(connection, error, **kwargs):
    print(f"[WARN] Connection interrupted: {error}", file=sys.stderr)


def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"[INFO] Connection resumed. return_code={return_code} session_present={session_present}")


def build_connection():
    # Verbose logs to stderr (comment out if too chatty)
    io.init_logging(io.LogLevel.Info, 'stderr')

    event_loop_group = io.EventLoopGroup(1)
    host_resolver    = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # LWT must be bytes
    will_payload = json.dumps({
        "thing": THING_NAME,
        "status": "offline",
        "ts": iso_now()
    }).encode("utf-8")

    return mqtt_connection_builder.mtls_from_path(
        endpoint=ENDPOINT,
        cert_filepath=CERT_FILE,
        pri_key_filepath=KEY_FILE,
        ca_filepath=CA_FILE,
        client_id=CLIENT_ID,
        clean_session=True,
        keep_alive_secs=KEEP_ALIVE_SECS,
        client_bootstrap=client_bootstrap,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        will=mqtt.Will(
            topic=TOPIC_STAT,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            payload=will_payload,
            retain=False
        )
    )


def main():
    # 1) Sanity checks
    print(f"[INFO] System time: {iso_now()}")
    check_files(CERT_FILE, KEY_FILE, CA_FILE)
    try:
        socket.gethostbyname(ENDPOINT)
    except Exception as e:
        print(f"[ERROR] DNS lookup failed for endpoint: {e}", file=sys.stderr)
        sys.exit(1)

    # 2) Init sensor (same API as your main.py)
    sensor = PiicoDev_BME280()
    print("[INFO] Sensor initialized")

    # 3) Build and connect MQTT
    mqtt_connection = build_connection()
    print("[INFO] Connecting to AWS IoT...")
    mqtt_connection.connect().result()
    print("[INFO] Connected to AWS IoT")

    # 4) Publish ONLINE status
    mqtt_connection.publish(
        topic=TOPIC_STAT,
        payload=json.dumps({"thing": THING_NAME, "status": "online", "ts": iso_now()}).encode("utf-8"),
        qos=mqtt.QoS.AT_LEAST_ONCE
    )

    # 5) Read -> Publish loop
    backoff = 1
    try:
        while True:
            try:
                # Read sensor values: (tempC, presPa, humRH)
                tempC, presPa, humRH = sensor.values()
                pres_hPa = presPa / 100.0

                payload = {
                    "thing": THING_NAME,
                    "temperature_C": round(tempC, 2),
                    "pressure_hPa": round(pres_hPa, 2),
                    "humidity_RH": round(humRH, 2),
                    "timestamp_ms": int(time.time() * 1000)
                    #"ts_iso": iso_now()
                }

                msg = json.dumps(payload).encode("utf-8")
                print(f"[PUB] {payload}")
                mqtt_connection.publish(
                    topic=TOPIC_DATA,
                    payload=msg,
                    qos=mqtt.QoS.AT_LEAST_ONCE
                )

                backoff = 1
                time.sleep(PUBLISH_PERIOD_SEC)

            except exceptions.AwsCrtError as e:
                # Network/auth hiccup — try to reconnect with backoff
                print(f"[ERROR] MQTT error: {e}", file=sys.stderr)
                try:
                    print("[INFO] Reconnecting...")
                    mqtt_connection.reconnect().result()
                    print("[INFO] Reconnected")
                except Exception as re:
                    print(f"[WARN] Reconnect failed: {re}", file=sys.stderr)
                    time.sleep(min(backoff, 60))
                    backoff *= 2

            except Exception as e:
                print(f"[ERROR] Unexpected loop error: {e}", file=sys.stderr)
                time.sleep(PUBLISH_PERIOD_SEC)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")

    finally:
        # 6) Publish OFFLINE and disconnect
        try:
            mqtt_connection.publish(
                topic=TOPIC_STAT,
                payload=json.dumps({"thing": THING_NAME, "status": "offline", "ts": iso_now()}).encode("utf-8"),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
        except Exception:
            pass
        try:
            mqtt_connection.disconnect().result()
            print("[INFO] Disconnected from AWS IoT")
        except Exception:
            pass


if __name__ == "__main__":
    main()
