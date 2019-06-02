#!/usr/bin/env python3

import asyncio

import time
from neopixel import *
import argparse
import random

update_period = 0.8

from collections import deque

import webcolors
import sys
import colorsys

# Ultrasonic HC-SR04
from Bluetin_Echo import Echo
# Define GPIO pin constants.
TRIGGER_PIN = 13
ECHO_PIN = 26
# Initialise Sensor with pins, speed of sound.
speed_of_sound = 315
echo = Echo(TRIGGER_PIN, ECHO_PIN, speed_of_sound)
samples = 3

EXPLODE_ENABLED = False
MAX_DIST = 200.0

#
# async def sonar_gen():
#     await asyncio.sleep(0.4)
#     dist =  echo.read('cm', samples)
#     print(dist)
#     yield dist


# async def monitor_sonar():
#
#     while True:
#         await asyncio.sleep(0.4)
#         dist = echo.read('cm', samples)
#         print("{:0.2f} cm distanceee".format(dist))


# LED strip configuration:
LED_COUNT      = 300      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 100     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


wait_std = 80


#
# # sine wave
# from math import *
# Fs = 8000
# f = 10
# sample=10000
# a=[0]*sample
# for n in range(sample):
#     a[n]=sin(2*pi*f*n/Fs)


#num_pix = strip.numPixels()
#pixb=[0]*strip.numPixels()
#for n in range(num_pix):
#   pixb[n] = 0 

def name_to_color(color_name):
    try:
        wc = webcolors.name_to_rgb(color_name)
        print(wc)
        return Color(wc[0], wc[1], wc[2])
    except Exception as e:
        print(e)
        return Color(0, 60, 0)

def hsv_to_color(hue, sat, val):
    #print("YEEAEASH")
    #from hsv import hsv_to_rgb
    rgb_tuple = colorsys.hsv_to_rgb(hue, sat, val)
    red = int(rgb_tuple[0] * 255)
    green = int(rgb_tuple[1] * 255)
    blue = int(rgb_tuple[2] * 255)

    print (red, green, blue)

    return Color(red, green, blue)

yellow_orange = Color(255, 215, 0)
purple = Color(160, 32, 240)
red = Color(200, 0, 0)
blue = Color(0,0,200)
light_gold = Color(244, 232, 104)
green = name_to_color('green') #Color(88, 4, 4),

orange = Color(255, 110, 0)
dark_orange = Color(12, 8, 0)

palette_1 = {
    0: name_to_color('violet'),
    1: purple,
    2: dark_orange,
    3: Color(99, 66, 66),
    4: Color(66, 66, 66),
    5: Color(0, 6, 0)
    }
#
# sonar_color_dict_orig = {
#     '20': Color(88, 4, 4),
#     '30': Color(99, 66, 66),
#     '40': Color(66, 66, 66),
#     '100': Color(0, 6, 66),
#     }

sonar_color_dict = palette_1


class TreeStrip(Adafruit_NeoPixel):

    def __init__(self, *args, **kwargs):
        super(TreeStrip, self).__init__(*args, **kwargs)
        self.base_color = dark_orange #Color(22, 0, 3)
        self.previous_base_color = dark_orange
        self.active_color = orange
        self.num_pix = self.numPixels()

        self.previous_index = 0
        self.target_pixel = 0
        self.active_pixel = 0
        self.old_pixel_stack = deque()
        self.explode_thresh = int(0.75 * self.num_pix)
        self.explode_color = Color(40, 22, 0) #name_to_color('aqua')
        self.next_explode_color = Color(0, 0, 50)
        self.exploding = False

    def setPixelColor2(self, pixel, color):
        i = pixel #self.num_pix - pixel
        self.setPixelColor(i, color)

    def all_to_color(self, color, show=True):

        print("Chaging to {} ".format(color))
        for i in range(self.num_pix):
            self.setPixelColor2(i, color)
        if show:
            self.show()

    def all_to_base(self, show=False):
        self.all_to_color(color=self.base_color, show=show)

    def maybe_change_base_color(self, color, chance=0.001):
        if random.random() < chance:
            self.base_color = color

    def get_pixel_from_normalized_float(self, nfloat):

        pix = int(nfloat * self.num_pix)
        if pix > self.num_pix:
            return self.num_pix
        elif pix < 0:
            return 0
        return pix
            
    def update_single_pixel(self, si):
       if si != self.previous_index:
           self.setPixelColor2(si, self.active_color)
           self.setPixelColor2(self.previous_index, self.base_color)
           self.previous_index = si
       else:
           strip.setPixelColor2(si, strip.active_color)
       strip.show()

    def dim_pixel(self, pixel):
        pixel_color = Color(22, 0, 0)
        pixel_color=self.base_color
        self.setPixelColor2(pixel, pixel_color)

    def dim_old_pixels(self):
        if len(self.old_pixel_stack) > 8:
            pixel = self.old_pixel_stack.pop()

        #self.setPixelColor(pixel, self.base_color)            
        #pixel_color = Color(22, 0, 0)
        for pixel in self.old_pixel_stack:
            if pixel != self.active_pixel:
                #print("changing {} pixel to dim".format(pixel))
                #self.setPixelColor(pixel, pixel_color)
                self.dim_pixel(pixel)

    async def explode(self):

        await asyncio.sleep(6)
        self.exploding = False

        # force the base back, maybe a better way?
        self.previous_base_color = Color(0, 0, 0)

    #     if self.exploding:
    #         temp_color = self.explode_color
    #         self.explode_color = self.next_explode_color
    #         self.next_explode_color = temp_color
    #         for i in range(self.explode_thresh, self.num_pix):
    #             self.setPixelColor2(i, self.explode_color)
    #         self.show()
    #
    # def explode_pixels(self, color):
    #       for i in range(self.explode_thresh, self.num_pix):
    #           self.setPixelColor2(i, color)
            
    def update(self):
        #print("in update")

        updated = False

        if not self.exploding: # and self.base_color != self.previous_base_color:
            print("Changing base")
            self.all_to_base()
            self.previous_base_color = self.base_color
            updated = True

        elif self.exploding:
            print('exploding...')
            self.all_to_color(color=self.explode_color, show=False)
            updated = True

        if updated:
            self.show()


def normalize_dist(distance_in_cm, max_dist = 140.0):

    if distance_in_cm > max_dist:
        return 1.0
    elif distance_in_cm <= 6.0:
        return 0.0    
    return distance_in_cm / max_dist 


async def ongoing_update(strip, event_loop):
    while True:
        await asyncio.sleep(update_period)
        strip.update()


async def sonar_colors(strip, event_loop):

    sonar_wait = 0.4
    while True:
        await asyncio.sleep(sonar_wait)

        dist = echo.read('cm', samples=1)
        #print(dist)

        print("{:0.2f} cm disttttance".format(dist))
        if dist < -6.0:
            # could be junk
            print('junk')
            continue
        
        ndist = normalize_dist(dist, max_dist=200.)
        
        # pixel = strip.num_pix - strip.get_pixel_from_normalized_float(ndist)
        # print(pixel)
        # strip.target_pixel = pixel
        # print("target pixel is now {}".format(strip.target_pixel))
        #strip.update()
        
        if dist < 20.0:
            print("yooo")
            #base_color = hsv_to_color(0.9, 0.2, 0.3) #Color(15, 7, 0) #sonar_color_dict[2]
        #elif dist < 30:
        #    base_color = sonar_color_dict[1]
        elif dist < 168.0:
            new_color = hsv_to_color(240.0 / dist, 0.3, 0.2) # Color(30, 14, 0)  #sonar_color_dict[4]

            #strip.setPixelColor(3, new_color)
            for i in range(0, 100, 1):
                strip.setPixelColorRGB(i, 3, 9, 0)
            strip.show()
            #strip.all_to_color(color=base_color, show=True)

            #
            # if EXPLODE_ENABLED and not strip.exploding:
            #     strip.exploding = True
            #     event_loop.create_task(strip.explode())
        else:
            pass
            #base_color = Color(6, 3, 0)  #sonar_color_dict[5]

        #if base_color != strip.base_color:
        #    strip.base_color = base_color
            #strip.all_to_base()
            #print (strip.base_color)
            #print(base_color)
            #strip.base_color = Color(128, 99, 238)
            #pass

# Main program logic follows:
if __name__ == '__main__':
    # Process arguments
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    # args = parser.parse_args()

    # Create NeoPixel object with appropriate configuration.
    #strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, strip_type=ws.WS2811_STRIP_GRB)
    strip = TreeStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL,
                      strip_type=ws.WS2811_STRIP_GRB)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    strip.all_to_color(color=Color(0, 45, 4))

    # print ('Press Ctrl-C to quit.')
    # if not args.clear:
    #     print('Use "-c" argument to clear LEDs on exit')


    while 1:
        dist = echo.read('cm', samples=samples)
        hue = dist / MAX_DIST
        hue = 0. if hue <= 0 else (1.0 if hue > 1 else hue)

        print(f'Hue: {hue:.2}')

        if hue <= 0.0001:
            continue

        new_color = hsv_to_color(hue, 1.0, 1.0 - hue)
        for i in range(0, strip.numPixels(), 1):
            #strip.setPixelColorRGB(i, 3, 9, 0)
            strip.setPixelColor(n=i, color=new_color)
        strip.show()
        time.sleep(0.1)

    # loop = asyncio.get_event_loop()
    # try:
    #     print('task creation started')
    #     #loop.create_task(ongoing_update(strip, event_loop=loop))
    #     loop.create_task(sonar_colors(strip, event_loop=loop))
    #     loop.run_forever()
    # except KeyboardInterrupt:
    #     print("HEEEY")
    #     raise
    # finally:
    #     loop.close()
    #
    #
    #

    #print("The task's result was: {}".format(task_obj.result()))
    #
    # try:
    #     while True:
    #         print ('Sine Vals.')
    #         color_sine(strip, Color(255, 0, 0))  # Red sine
    #
    # except KeyboardInterrupt:
    #     if args.clear:
    #         colorWipe(strip, Color(0,0,0), 10)
