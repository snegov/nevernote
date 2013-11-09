#!/usr/bin/python3

import argparse
import sys
import urllib.request


def get_page(url):
    '''download page and decode it to utf-8'''
    u = urllib.request.urlopen(url)
    page_binary = u.read(100)
    page = page_binary.decode()


def write_file(page):
    with open('tmp.html', 'w') as a_file:
        a_file.write(page)


def main():
    parser = argparse.ArgumentParser(description=
            'Nevernote - download pages locally.')
    parser.add_argument('urls', metavar='URL', type=str, nargs='+', help=
            'URL of page to download')

    args = parser.parse_args()

    for url in args.urls:
        page = get_page(url)
        write_file(page)


if __name__ == '__main__':
    sys.exit(main())
