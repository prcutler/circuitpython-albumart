# SPDX-License-Identifier: MIT

import time

import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_requests as requests
import board
import displayio
from adafruit_pyportal import PyPortal

# the current working directory (where this file is)
pyportal = PyPortal()

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# ------------- MQTT Topic Setup ------------- #
mqtt_topic = "albumart"

# Load image on disk and display it
display = board.DISPLAY
maingroup = displayio.Group(x=80)
display.show(maingroup)  # show main group
bitmap = displayio.OnDiskBitmap(open("albumart.bmp", "rb"))
image = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
maingroup.append(image)


### Code ###
# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Subscribing to %s" % (mqtt_topic))
    client.subscribe(mqtt_topic)


def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from MQTT Broker!")


def message(client, topic, message):
    """Method callled when a client's subscribed feed has a new
    value.
    :param str topic: The topic of the feed with a new value.
    :param str message: The new value
    """
    if message == "Ping!":
        print("New message on topic {0}: {1}".format(topic, message))
        response = None

        url = "https://silversaucer.com/static/img/album-art/image_300.bmp"

        response = requests.get(url)
        if response.status_code == 200:
            print("Starting image download...")
            with open("albumart.bmp", "wb") as f:
                for chunk in response.iter_content(chunk_size=32):
                    f.write(chunk)
                print("Album art saved")
            response.close()

            display = board.DISPLAY
            maingroup = displayio.Group(x=80)  # everything goes in maingroup
            display.show(maingroup)  # show main group
            bitmap = displayio.OnDiskBitmap(open("albumart.bmp", "rb"))
            image = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
            maingroup.append(image)  #

            time.sleep(10)

        else:
            print("Bad get request")


# Connect to WiFi
print("Connecting to WiFi...")
pyportal.network.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
# pylint: disable=protected-access
MQTT.set_socket(socket, pyportal.network._wifi.esp)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    username=secrets["user"],
    password=secrets["pass"],
    is_ssl=False,
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

# Connect the client to the MQTT broker.
mqtt_client.connect()


while True:
    # Poll the message queue
    try:
        mqtt_client.loop()

    except RuntimeError or ConnectionError:
        time.sleep(10)
        mqtt_client.connect()
        mqtt_client.loop()

    # Send a new message
    time.sleep(5)
