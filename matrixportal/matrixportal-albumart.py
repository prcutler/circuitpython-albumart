import time

import board
import displayio
from adafruit_matrixportal.matrix import Matrix
import framebufferio
import adafruit_requests
import adafruit_imageload
import gc
import wifi
import ssl
import os
import socketpool
import io
import adafruit_minimqtt.adafruit_minimqtt as MQTT


wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
ssl_context = ssl.create_default_context()

displayio.release_displays()
matrix = Matrix(width=64, height=64, bit_depth=6)
display = matrix.display

url = "https://silversaucer.com/static/img/album-art/image64p.bmp"
free_memory = gc.mem_free()
print("Free memory: ", free_memory)

print("Fetching image from %s" % url)
response = requests.get(url)
# print("GET complete, Type: ", type(response.content))

if response.status_code == 200:
    print("Starting image download...")
    with open("albumart.bmp", "wb") as f:
        for chunk in response.iter_content(chunk_size=32):
            f.write(chunk)
        print("Album art saved")
    response.close()

    # open('bg256.bmp', 'wb').write(response.content)

    group = displayio.Group(scale=1)
    b, p = adafruit_imageload.load("albumart.bmp")
    tile_grid = displayio.TileGrid(b, pixel_shader=p)
    # tile_grid.x = 0

    group.append(tile_grid)
    display.root_group = group

    response.close()

# ------------- MQTT Topic Setup ------------- #
mqtt_topic = "prcutler/feeds/albumart"

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

        url = "https://silversaucer.com/static/img/album-art/image64p.bmp"

        response = requests.get(url)
        if response.status_code == 200:
            print("Starting image download...")
            with open("albumart.bmp", "wb") as f:
                for chunk in response.iter_content(chunk_size=32):
                    f.write(chunk)
                print("Album art saved")
            response.close()

            group = displayio.Group(scale=1)
            b, p = adafruit_imageload.load("albumart.bmp")
            tile_grid = displayio.TileGrid(b, pixel_shader=p)
            # tile_grid.x = 0

            group.append(tile_grid)
            display.root_group = group

            response.close()

            time.sleep(10)

        else:
            print("Bad get request")


# Initialize MQTT interface with the esp interface
# pylint: disable=protected-access
# MQTT.set_socket(socket, pyportal.network._wifi.esp)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=8883,
    username=os.getenv('aio_username'),
    password=os.getenv('aio_key'),
    ssl_context=ssl_context,
    socket_pool=pool,
    is_ssl=True,
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

ssl_context = ssl.create_default_context()

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
