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

update_period = 0.1

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
        
        # pixel = strip.num_pix - strip.get_pixel_from_normalized_float(ndist)
        # print(pixel)
        # strip.target_pixel = pixel
        # print("target pixel is now {}".format(strip.target_pixel))
        #strip.update()
        
        # if dist < 20.0:
        #     print("yooo")
        #     #base_color = hsv_to_color(0.9, 0.2, 0.3) #Color(15, 7, 0) #sonar_color_dict[2]
        # #elif dist < 30:
        # #    base_color = sonar_color_dict[1]
        # elif dist < 168.0:
        if True:
            print(f'normalized distance: {ndist}')
            hue = ndist #dist / MAX_DIST

            red_fac = 8.0
            red_reverse_hue = (1.0 / red_fac) - (hue / red_fac)
            night_bright = HSV_BRIGHTNESS_TEST * (1.0 - ndist)

            print(f"reverse hue: {red_reverse_hue}")


            strip.target_hue = red_reverse_hue
            strip.target_brightness = night_bright

            #
            # # only update if there's a change
            # if abs((red_reverse_hue - current_hue) / red_reverse_hue) > close_enough:
            #     if smoothing_enabled:
            #         print("\n\nSmoothing\n")
            #         new_hue = (red_reverse_hue - current_hue) * smoothing_factor + current_hue
            #         print(f'Current: {current_hue}')
            #
            #         print(f'Smoothed: {new_hue}')
            #         current_hue = new_hue
            #     else:
            #         new_hue = red_reverse_hue
            #
            #     #print(hue)
            #     #print(red_reverse_hue)
            #     #print('')
            #     #hue = 0. if hue <= 0 else (1.0 if hue > 1 else hue)
            #     new_color = hsv_to_color(new_hue, 1.0, night_bright)
            #     #color2 = hsv_to_color(hue / 2.0, 1.0, night_bright)
            #     strip.all_to_color(new_color, show=True)

            ## turn off 2nd strip for now
            #strip2.all_to_color(color2, show=True)

            #strip.setPixelColor(3, new_color)
            maxp = 300
            # for i in range(0, maxp, 1):
            #     new_hue = hue * (maxp - i) / float(maxp)
            #     cc = hsv_to_color(new_hue, 1.0, 0.6)
            #     strip.setPixelColor(i, cc)
            # strip.show()

            # for j in range(6):
            #     for i in range(50*j, 50*(j+1), 1):
            #         #print(i)
            #         strip.setPixelColorRGB(i, 0, j*5, 55)
            # strip.show()

            #
            # if EXPLODE_ENABLED and not strip.exploding:
            #     strip.exploding = True
            #     event_loop.create_task(strip.explode())
        # else:
        #     pass
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

    # Create LED strip object with appropriate configuration.
    strip = TreeStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL,
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
