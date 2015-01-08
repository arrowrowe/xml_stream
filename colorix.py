import colorama
import sys


def fore(source, color, bright=True):
    return getattr(colorama.Fore, color.upper()) + (colorama.Style.BRIGHT if bright else '') + \
        str(source) + colorama.Fore.RESET


def back(source, color):
    return getattr(colorama.Back, color.upper()) + \
        str(source) + colorama.Back.RESET


def echo(source, end='\n'):
    sys.stdout.write(str(source) + end)


def recho(source='', end='\n'):
    echo(colorama.Cursor.UP() + colorama.clear_line() + str(source), end)


colorama.init()