# SPDX-License-Identifier: MIT

from os import getenv
import board
import busio
from adafruit_pyportal import PyPortal
from digitalio import DigitalInOut
import adafruit_connection_manager
import adafruit_requests
from adafruit_esp32spi import adafruit_esp32spi
import displayio
import json
import terminalio
from adafruit_display_text import label
import adafruit_minimqtt.adafruit_minimqtt as MQTT


secrets = {
    "ssid": getenv("CIRCUITPY_WIFI_SSID"),
    "password": getenv("CIRCUITPY_WIFI_PASSWORD"),
    "broker": getenv("broker"),
    "user": getenv("ADAFRUIT_AIO_USERNAME"),
    "pass": getenv("ADAFRUIT_AIO_KEY")
}
if secrets == {"ssid": None, "password": None}:
    try:
        # Fallback on secrets.py until depreciation is over and option is removed
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in settings.toml, please add them there!")
        raise

IMAGE_URL = "https://silversaucer.com/static/img/album-art/image_300.bmp"

# pyportal = PyPortal()
# pyportal.network.connect()

# Set up WIFI w/ConnectionManager

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# Secondary (SCK1) SPI used to connect to WiFi board on Arduino Nano Connect RP2040
if "SCK1" in dir(board):
    spi = busio.SPI(board.SCK1, board.MOSI1, board.MISO1)
else:
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
requests = adafruit_requests.Session(pool, ssl_context)

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except OSError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# Get the Album title and artist name from JSON
data_source = "https://silversaucer.com/album/data"

resp = requests.get(data_source)
data = resp.json()
print(data)

image_location = data["image_url"]
artist = data["artist"]
album = data["album"]

album_info = artist + " - " + album

# album_info = "Garbage - Garbage"

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
