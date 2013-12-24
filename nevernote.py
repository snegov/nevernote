#!/usr/bin/python3

import argparse
import http.client
import sys

from bs4 import BeautifulSoup
from urllib.parse import urlparse

def get_page(url):
    '''download page and decode it to utf-8'''
    charset = 'utf-8'

    up = urlparse(url)

    headers = {
        "Host": up.netloc,
        "Content-Type": "text/html; charset=utf-8",
        "Connection": "keep-alive",
    }

    if up.scheme == 'http':
        conn = http.client.HTTPConnection(up.netloc)
    elif up.scheme == 'https':
        conn = http.client.HTTPSConnection(up.netloc)
    else:
        print("ERROR: invalid protocol set in '{0}'".format(url))
        return False

    conn.request("GET", up.path, None, headers)
    response = conn.getresponse()

    # follow redirects
    if (response.status == http.client.MOVED_PERMANENTLY) \
            or (response.status == http.client.FOUND):
        new_url = response.getheader('Location')
        print('Redirect to ' + new_url)
        return get_page(new_url)

    # get page charset from response header
    contenttype = response.getheader('Content-Type')
    if contenttype:
        ct_spl = contenttype.split('; ')
        if len(ct_spl) > 1:
            charset = ct_spl[1].split('=')[1]

    page_binary = response.read()
    page = page_binary.decode(charset)

    return page


def get_title(page):
    soup = BeautifulSoup(page)
    return soup.title.string


def write_file(page):
    fname = get_title(page) + '.html'
    with open(fname, 'w') as a_file:
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
