#!/usr/bin/env python3

import asyncio

import time
from neopixel import *
import argparse
import random


from collections import deque

import webcolors
import sys
import colorsys

# Ultrasonic HC-SR04
from Bluetin_Echo import Echo
# Define GPIO pin constants.
TRIGGER_PIN = 22
ECHO_PIN = 26
# Initialise Sensor with pins, speed of sound.
speed_of_sound = 315
echo = Echo(TRIGGER_PIN, ECHO_PIN, speed_of_sound)
samples = 1

EXPLODE_ENABLED = False
MAX_DIST = 190.0
JUNK_MIN_DIST = 5.0

update_period = 0.005

# LED strip configuration:

HSV_BRIGHTNESS_TEST = 0.2

LED_COUNT      = 500      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 250     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


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

    #print (red, green, blue)

    return Color(red, green, blue)


yellow_orange = Color(255, 215, 0)
purple = Color(160, 32, 240)
red = Color(200, 0, 0)
blue = Color(0,0,200)
light_gold = Color(244, 232, 104)
green = name_to_color('green') #Color(88, 4, 4),

orange = Color(255, 110, 0)
dark_orange = Color(12, 8, 0)


class TreeStrip(Adafruit_NeoPixel):

    def __init__(self, *args, **kwargs):
        super(TreeStrip, self).__init__(*args, **kwargs)
        self.base_color = dark_orange
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

        # HSV (Hue Saturation Vrightness)
        self.current_hue = 0.0
        self.target_hue = 0.0
        self.current_brightness = 0.1
        self.target_brightness = 0.1

        self.smoothing_factor = 0.04
        self.close_enough = 0.02

        self.flicker = False
        self.verbosity = 0

    def update_hues(self):

        if abs(self.target_hue - self.current_hue) > self.close_enough:
            if self.verbosity > 1:
                print('updating')
            new_hue = (self.target_hue - self.current_hue) * self.smoothing_factor + self.current_hue
            new_brightness = (self.target_brightness - self.current_brightness) * self.smoothing_factor + self.current_brightness

            if not self.flicker:
                self.set_to_single_hue(new_brightness=new_brightness, new_hue=new_hue)
            else:
                print('flicker dynamic')

            self.current_brightness = new_brightness
            self.current_hue = new_hue
        else:
            if not self.flicker:
                if self.verbosity > 2:
                    print('already there')
            else:
                print('flicker static')
                pass
            pass

    def flicker_static(self, hue, brightness):
        return

    def set_to_single_hue(self, new_hue, new_brightness):
        new_color = hsv_to_color(new_hue, 1.0, new_brightness)
        strip.all_to_color(new_color, show=True)

    def setPixelColor2(self, pixel, color):
        i = pixel #self.num_pix - pixel
        self.setPixelColor(i, color)

    def all_to_color(self, color, show=True):

        #print("Changing to {} ".format(color))
        for i in range(self.num_pix):
            self.setPixelColor(i, color)
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

import numpy as np


class FireStrip(TreeStrip):

    def __init__(self, *args, **kwargs):
        super(FireStrip, self).__init__(*args, **kwargs)
        self.heat = np.zeros(self.num_pix)
        self.heat_bright = np.zeros(self.num_pix)
        self.cooling_factor = kwargs.get('cooling_factor', 10)
        self.spark_region_factor = 4
        self.sparking_threshold = kwargs.get('sparking_threshold', 100)
        self.red_fac = 7.0
        #self.hue_min = 0.0
        #self.hue_max = 0.2

    def cool_pixel(self, cur_heat):

        if cur_heat == 0:
            return 0

        new_heat = cur_heat - random.randint(2, self.cooling_factor)
        if new_heat < 0:
            return 0
        return new_heat

    def heat_pixel(self, cur_val):
        new_val = cur_val + random.randint(160, 255)
        if new_val > 255:
            new_val = 255
        return new_val

    #def drift_pixel(self):

    def update_hues(self):
        # void Fire2012WithPalette()
        #{
        # // Array of temperature readings at each simulation cell
          # static byte heat[NUM_LEDS];

        # Step 1.  Cool down every cell a little
        # heat[i] = qsub8( heat[i],  random8(0, ((COOLING * 10) / NUM_LEDS) + 2));
        for i in range(self.num_pix):
            self.heat[i] = self.cool_pixel(self.heat[i])
            self.heat_bright[i] = self.cool_pixel(self.heat_bright[i])
        #self.heat = np.apply_along_axis(self.cool_pixel, 0, self.heat)


        # Step 2.  Heat from each cell drifts 'up' and diffuses a little
        #    for( int k= NUM_LEDS - 1; k >= 2; k--) {
        #      heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2] ) / 3;
        for k in range((self.num_pix - 1), 2, -1):
            self.heat[k] = (self.heat[k - 1] + self.heat[k - 2] + self.heat[k - 2]) / 3
            self.heat_bright[k] = (self.heat_bright[k - 1] + self.heat_bright[k - 2] + self.heat_bright[k - 2]) / 3

        # Step 3.  Randomly ignite new 'sparks' of heat near the bottom
        if random.randint(0, 255) < self.sparking_threshold:
            y = random.randint(0, 30) #self.num_pix / self.spark_region_factor)
            old_heat = self.heat[y]
            self.heat[y] = self.heat_pixel(self.heat[y])
            self.heat_bright[y] = self.heat_pixel(self.heat_bright[y])
            #print(f'Spark pixel: {y},  old heat: {old_heat}, new_heat: {self.heat[y]}')

        # Step 4.  Map from heat cells to LED colors
        # map from 255 to subset of HSV.

        for i in range(self.num_pix):
            max_heat = 255.0
            #print(self.heat[i])
            red_reverse_hue = self.heat[i] / max_heat * 0.14  #((max_heat / self.red_fac) - (self.heat[i] / self.red_fac)) / (max_heat / self.red_fac)
            new_brightness = self.heat_bright[i] / max_heat * 0.2
            #print(red_reverse_hue)
            color = hsv_to_color(red_reverse_hue, 1.0, new_brightness)
            self.setPixelColor(i, color)

        self.show()


        #
        #     for( int j = 0; j < NUM_LEDS; j++) {
        #       // Scale the heat value from 0-255 down to 0-240
        #       // for best results with color palettes.
        #       byte colorindex = scale8( heat[j], 240);
        #       CRGB color = ColorFromPalette( gPal, colorindex);
        #       int pixelnumber;
        #       if( gReverseDirection ) {
        #         pixelnumber = (NUM_LEDS-1) - j;
        #       } else {
        #         pixelnumber = j;
        #       }
        #       leds[pixelnumber] = color;
        #     }
        # }

def normalize_dist(distance_in_cm, max_dist = MAX_DIST):

    if distance_in_cm > max_dist:
        return 1.0
    elif distance_in_cm <= 0.0:
        return 0.0    
    return distance_in_cm / max_dist 


async def ongoing_update(strip, event_loop):
    while True:
        await asyncio.sleep(update_period)
        strip.update_hues()


async def sonar_colors(strip, event_loop):

    sonar_wait = 0.5

    current_hue = 0.0
    current_brightness = 0.0
    smoothing_factor = 0.2
    smoothing_enabled = True
    close_enough = 0.02

    while True:
        await asyncio.sleep(sonar_wait)

        dist = await echo.read_async('cm', samples=samples)
        #print(dist)

        print("{:0.0f} cm distance".format(dist))
        if dist <= JUNK_MIN_DIST:
            # could be junk
            print('.... junk distance, skipping')
            dist = random.randint(1, MAX_DIST - 1)
            #continue
        
        ndist = normalize_dist(dist, max_dist=200.)

        # FireStrip
        strip.sparking_threshold = (1.0 - ndist) * 255.0

        # For TreeStrip
        if False:
            print(f'normalized distance: {ndist}')
            hue = ndist #dist / MAX_DIST
            red_fac = 8.0
            red_reverse_hue = (1.0 / red_fac) - (hue / red_fac)
            night_bright = HSV_BRIGHTNESS_TEST * (1.0 - ndist)
            print(f"reverse hue: {red_reverse_hue}")
            strip.target_hue = red_reverse_hue
            strip.target_brightness = night_bright


# Main program logic follows:
if __name__ == '__main__':
    # Process arguments
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    # args = parser.parse_args()

    # Create LED strip object with appropriate configuration.
    strip = FireStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL,
                      strip_type=ws.WS2811_STRIP_GRB)
    # Intialize the library (must be called once before other functions).
    strip.begin()
    strip.all_to_color(color=Color(0, 45, 4))

    if False:
        # second strip
        LED_PIN_2 = 13
        strip2 = TreeStrip(LED_COUNT, LED_PIN_2, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, 1,
                          strip_type=ws.WS2811_STRIP_GRB)

        strip2.begin()
        strip2.all_to_color(color=Color(0, 0, 8))

    loop = asyncio.get_event_loop()
    try:
        print('task creation started')
        echo.event_loop = loop
        loop.create_task(ongoing_update(strip, event_loop=loop))
        loop.create_task(sonar_colors(strip, event_loop=loop))
        loop.run_forever()
    except KeyboardInterrupt:
        print("DONE")
        raise
    finally:
        loop.close()

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
