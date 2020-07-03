#!/usr/bin/python3
# loop over the video frames

# check for motion
# if the light is off:

#   if there is motion, run the person detector

#       if there is a person
#           turn on the lights.
#           the brightness should be a function of the time of day, including sunset/sunrise time
#           sleep for a certain amount of time. this should also be a function of the time of day

# if the light is on:
#   if there is motion, run the person detector:
#       if there is a person, keep the lights on and sleep
#       otherwise, turn the lights off and don't sleep
#

from hue.hue_wrapper import HueWrapper
from optics.human_detector import HumanDetector
from model.hue_strategy import HueStrategy
from model.hue_state_change import HueStateChangeEvent
from picamera.array import PiRGBArray
from util.storm import getSunrise, getSunset
from picamera import PiCamera

import cv2
import datetime
import pytz
import sys
import time


last_seen_human_time = time.time()

def get_camera():
    """
    Connects to the camera

    :return: a handle to the camera and its capture feed
    """
    resolution = (1296, 976)
    #resolution = (1296, 736)
    camera = PiCamera()
    camera.resolution = resolution
    camera.framerate = 3
    camera.contrast = 70
    camera.brightness = 80
    camera.iso = 800
    raw_capture = PiRGBArray(camera, size=resolution)
    raw_capture.truncate(0)
    raw_capture.seek(0)
    # warmup the sensor array
    time.sleep(3)
    return (camera, raw_capture)


def scan(camera, capture, hue, strategy):
    """
    Scans the video stream for motion and humans.

    :param camera:
    :param capture:
    :param hue:
    :param strategy:
    :return:
    """
    human_detector = HumanDetector()
    human_threshold = 0.8

    global last_seen_human_time
    print("scanning video stream...")
    stream = camera.capture_continuous(capture, format="bgr", use_video_port=True)

    # discard the first few frames
    for i in range(16):
        next(stream)
        capture.truncate(0)

    capture.truncate(0)


    group_on = None

    # check if the current frame contains a human
    # if it does, turn lights on, set last_seen_human
    # if not, turn lights off
    for frame in stream:
        frame = frame.array
        brightness = strategy.brightness()
        (human_rects, human_weights) = human_detector.detect(frame)
        #print("human weights: {}".format(human_weights))

        # filter on a small threshold to avoid false positives
        filtered_weights = filter(lambda w: w > human_threshold, human_weights)
        # TODO we should also check that the rects are overlapping
        if len(list(filtered_weights)) > 0:
            print \
                ("found humans above threshold {}, might turn on {} lights, brightness={}".format(human_threshold, strategy.hue_group, brightness))
            last_seen_human_time = time.time()
            if group_on is None or group_on is False:
                print("turning on lights")
                hue.turn_group_on(strategy.hue_group)
                hue.set_light_group_brightness(strategy.hue_group, brightness)
                human_threshold = 0.5
                group_on = True
                break
        # just print that we are likely avoiding a false positive
        elif len(human_rects) > 0:
            #last_seen_human_time = time.time()
            print("found humans below threshold {} (likely false positive)".format(human_threshold))
        elif len(human_rects) == 0 and (time.time() - last_seen_human_time) > (strategy.sleep_when_on() + 60): # strategy.sleep_when_on(last_off_time):
            if group_on is None or group_on is True:
                print("turning off lights")
                hue.set_light_group_brightness(strategy.hue_group, brightness)
                hue.turn_group_off(strategy.hue_group)
                human_threshold = 0.8
                group_on = False

        # we need to truncate the buffer before the next iteration
        capture.truncate(0)
        capture.seek(0)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            sys.exit(1)

    return HueStateChangeEvent(strategy.sleep_when_on)


def get_brightness():
    """
    :return: the brightness we should set the lights to based on time of day.
    """
    hour = datetime.datetime.now(pytz.timezone('US/Pacific')).hour

    sunrise = getSunrise()
    sunset = getSunset()


    # late night
    if hour <= 3:
        return 20
    # late night
    elif hour <= 5:
        return 20
    # early morning
    elif hour <= sunrise[0]:
        return 100
    # during work
    elif hour <= 18:
        return 50
    elif hour <= sunset[0]:
        return 100
    else:
        return 80


def get_sleep_time():
    """
    TODO this should lookup sunrise and sunset time
    TODO this should return a tuple and be combined with get_brightness()
    :return: the amount of time (in seconds) that we should sleep for after turning the lights on.
    """
    #hour = datetime.datetime.now(pytz.timezone('US/Pacific')).hour
    #epoch_seconds = time.time()
    #sleep_time = None
    # late night
    # if hour <= 3:
    #     sleep_time = 600
    # # sleep time
    # elif hour <= 7:
    #     sleep_time = 120
    # else:
    #     sleep_time = 600

    # if (epoch_seconds - last_off_time) < 10:
    #     print("extending time, someone is probably cooking")
    #     return sleep_time * 3
    # else:
    #     return sleep_time
    return 60


def main():
    """
    Main script loop.

    Creates a hue wrapper and monitors the video stream.
    :return:
    """
    hue = HueWrapper("philips-hue.lan")

    (camera, capture, result) = None, None, None

    while True:
        # create a camera
        (camera, capture) = get_camera()
        # create a strategy
        strategy = HueStrategy("Kitchen", lambda: get_brightness(), lambda: get_sleep_time())
        # scan the video stream
        result = scan(camera, capture, hue, strategy)
        camera.close()
        capture.close()
        print("sleeping for {}s".format(result.sleep_time()))
        time.sleep(result.sleep_time())

if __name__ == "__main__":
    main()
