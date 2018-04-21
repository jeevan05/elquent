#!/usr/bin/env python3.6
# -*- coding: utf8 -*-

'''
ELQuent.link
RegEx cleaner for links

Mateusz Dąbrowski
github.com/MateuszDabrowski
linkedin.com/in/mateusz-dabrowski-marketing/
'''

import os
import re
import sys
import encodings
import pyperclip
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)


'''
=================================================================================
                            File Path Getter
=================================================================================
'''


def file(file_path):
    '''
    Returns file path to template files
    '''

    def find_data_file(filename):
        '''
        Returns correct file path for both script and frozen app
        '''
        if getattr(sys, 'frozen', False):
            datadir = os.path.dirname(sys.executable)
        else:
            datadir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(datadir, 'outcomes', filename)

    file_paths = {
        'elqtrack': find_data_file(f'WK{source_country}_CleanedURL-Code.txt'),
        'utmswap': find_data_file(f'WK{source_country}_SwappedUTM-Code.txt')
    }

    return file_paths.get(file_path)


'''
=================================================================================
                            Preparation of the program
=================================================================================
'''


def get_code():
    '''
    Returns code to be cleaned
    » code: long str
    '''
    while True:
        print(
            f'\n{Fore.WHITE}» Copy code [CTRL+C] and click [Enter]', end='')
        input(' ')
        code = pyperclip.paste()
        is_html = re.compile(r'<html[\s\S\n]*?</html>', re.UNICODE)
        if is_html.findall(code):
            break
        print(
            f'\t{Fore.RED}[ERROR] {Fore.YELLOW}Copied code is not correct HTML')

    return code


'''
=================================================================================
                            Cleaning functions
=================================================================================
'''


def clean_elq_track(country):
    '''
    Returns code without elqTrack UTMs
    » code: long str
    '''
    global source_country
    source_country = country

    code = get_code()
    elq_track = re.compile(r'(\?|&)elqTrack.*?(?=(#|"))', re.UNICODE)
    if elq_track.findall(code):
        print(
            f'{Fore.GREEN}» Cleaned {len(elq_track.findall(code))} elqTrack instances')
        code = elq_track.sub('', code)
        pyperclip.copy(code)
        with open(file('elqtrack'), 'w', encoding='utf-8') as f:
            f.write(code)
        print(
            f'\n{Fore.GREEN}» You can now paste code to Eloqua [CTRL+V].',
            f'\n{Fore.WHITE}  (It is also saved as WK{source_country}_CleanedURL-Code.txt in Outcomes folder)')
    else:
        print(f'\t{Fore.RED}[ERROR] {Fore.YELLOW}elqTrack not found')

    # Asks user if he would like to repeat
    print(f'\n{Fore.WHITE}» Do you want to clean another code? (Y/N)', end='')
    choice = input(' ')
    if choice.lower() == 'y':
        print(
            f'\n{Fore.GREEN}-----------------------------------------------------------------------------')
        clean_elq_track(country)

    return


'''
=================================================================================
                            Swapping functions
=================================================================================
'''


def swap_utm_track(country, code=''):
    '''
    Returns code with swapped tracking scripts in links
    » code: long str
    '''
    global source_country
    source_country = country

    # Gets Email code
    if not code:
        code = get_code()

    # Cleans ELQ tracking
    elq_track = re.compile(r'(\?|&)elqTrack.*?(?=(#|"))', re.UNICODE)
    if elq_track.findall(code):
        code = elq_track.sub('', code)

    # Gets new UTM tracking
    utm_track = re.compile(r'((\?|&)(kampania|utm).*?)(?=(#|"))', re.UNICODE)
    while True:
        print(
            f'{Fore.WHITE}» Copy new UTM tracking script [CTRL+C] and click [Enter]', end='')
        input(' ')
        new_utm = pyperclip.paste()
        if utm_track.findall(new_utm + '"'):
            break
        print(
            f'\t{Fore.RED}[ERROR] {Fore.YELLOW}Copied code is not correct UTM tracking script')

    # Asks if phone field should be changed to lead mechanism
    swapping = ''
    while swapping.lower() != 'y' and swapping.lower() != 'n':
        print(f'\n{Fore.WHITE}Change UTM tracking script from:',
              f'\n{Fore.WHITE}"{Fore.YELLOW}{(utm_track.findall(code))[0][0]}{Fore.WHITE}"',
              f'\n{Fore.WHITE}to:',
              f'\n{Fore.WHITE}"{Fore.YELLOW}{new_utm}{Fore.WHITE}"',
              f'\n{Fore.WHITE}? (Y/N)', end='')
        swapping = input(' ')

    if swapping.lower() == 'y':
        print(
            f'{Fore.GREEN}» Swapped {len(utm_track.findall(code))} UTM tracking scripts')
        code = utm_track.sub(new_utm, code)
        pyperclip.copy(code)
        with open(file('utmswap'), 'w', encoding='utf-8') as f:
            f.write(code)
        print(
            f'\n{Fore.GREEN}» You can now paste code to Eloqua [CTRL+V].',
            f'\n{Fore.WHITE}  (It is also saved as WK{source_country}_SwappedUTM-Code.txt in Outcomes folder)')

    # Asks user if he would like to repeat
    print(f'\n{Fore.WHITE}» Do you want to swap another UTM tracking?\n(Y/N or S for another UTM change in the same code)', end='')
    choice = input(' ')
    if choice.lower() == 'y':
        print(
            f'\n{Fore.GREEN}-----------------------------------------------------------------------------')
        swap_utm_track(country)
    elif choice.lower() == 's':
        print(
            f'\n{Fore.GREEN}-----------------------------------------------------------------------------', end='\n')
        swap_utm_track(country, code)

    return