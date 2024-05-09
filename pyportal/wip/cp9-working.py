# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_pyportal import PyPortal
import adafruit_imageload
import displayio

import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_requests as requests
import terminalio
from adafruit_display_text import label
import json

### WiFi ### - works prior to ConnectionManager

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

pyportal = PyPortal()
pyportal.network.connect()

# Get the Album title and artist name from JSON
data_source = "https://silversaucer.com/album/data"

resp = requests.get(data_source)
data = resp.json()
print(data)

# There's a few different places we look for data in the photo of the day
image_location = data["image_url"]
artist = data["artist"]
album = data["album"]

album_info = artist + " - " + album

# Load image on disk and display it on first boot
display = board.DISPLAY
display.rotation = 90

winamp = displayio.OnDiskBitmap(open("winamp256.bmp", "rb"))

# Create a TileGrid to hold the bitmap
tile_grid_1 = displayio.TileGrid(winamp, pixel_shader=winamp.pixel_shader, x=0)

# Create a Group to hold the TileGrid
group = displayio.Group()

# Add the TileGrid to the Group
group.append(tile_grid_1)

album_art = displayio.OnDiskBitmap("albumart.bmp")

tile_grid_2 = displayio.TileGrid(album_art, pixel_shader=album_art.pixel_shader, y=120)
group.append(tile_grid_2)

font = terminalio.FONT
color = 0x00E200

text_area = label.Label(font, text=album_info, color=color)

text_area.x = 130
text_area.y = 42
group.append(text_area)

# Add the Group to the Display
display.root_group = group

# ------------- MQTT Topic Setup ------------- #
mqtt_topic = "albumart"

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
    if message == "New album picked!":
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

            resp = requests.get(data_source)
            data = resp.json()
            print(data)

            # There's a few different places we look for data in the photo of the day
            image_location = data["image_url"]
            artist = data["artist"]
            album = data["album"]

            album_str = artist + " - " + album

            album_info = album_str[:30]

            winamp = displayio.OnDiskBitmap(open("winamp256.bmp", "rb"))

            # Create a TileGrid to hold the bitmap
            tile_grid_1 = displayio.TileGrid(winamp, pixel_shader=winamp.pixel_shader)

            # Create a Group to hold the TileGrid
            group = displayio.Group()

            # Add the TileGrid to the Group
            group.append(tile_grid_1)

            album_art = displayio.OnDiskBitmap("albumart.bmp")

            tile_grid_2 = displayio.TileGrid(album_art, pixel_shader=album_art.pixel_shader, y=120)
            group.append(tile_grid_2)

            font = terminalio.FONT
            color = 0x00E200

            text_area = label.Label(font, text=album_info, color=color)

            text_area.x = 130
            text_area.y = 42
            group.append(text_area)

            # Add the Group to the Display
            display.root_group = group

            time.sleep(10)

        else:
            print("Bad get request")


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
