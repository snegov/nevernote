#!/usr/bin/env python3

import argparse
import base64
import os
import re
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

URLDUP = re.compile(r'^<!-- URL: (.*) -->$')


def get_text(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def get_embedded_binary(url):
    """Download content from URL and return bytes if target is image"""
    response = requests.get(url)
    response.raise_for_status()
    ctype = response.headers.get('Content-Type')
    data = response.content
    b64pict = base64.b64encode(data).decode()
    return 'data:%s;base64,%s' % (ctype, b64pict)


def is_downloaded(url: str) -> bool:
    """Check if url was already downloaded"""
    for htmlfile in os.listdir(path='.'):
        if not htmlfile.endswith('.html'):
            continue

        with open(htmlfile) as h:
            h_url = h.readline()
            if url in URLDUP.findall(h_url):
                print("URL is already saved in file '%s'" % htmlfile)
                return True

    return False


def write_file(page, title, comment=None):
    """Save HTML to file on a disk"""
    write_inc = lambda i: '_%d' % i if i > 1 else ''
    inc = 0
    while True:
        inc += 1
        fname = (' '.join(title.replace('/', '_').split()) + write_inc(inc))[:128] + '.html'
        if not os.path.exists(fname):
            break

    with open(fname, 'x', newline='\n') as a_file:
        print('Saving in file "%s"' % fname)
        if comment:
            a_file.write('<!-- URL: %s -->\n' % comment)
        a_file.write(page)


def complete_url(url, base_url=None):
    """Create absolute URL from relative paths"""
    base_up = urlparse(base_url)
    if base_url is not None:
        up = urlparse(url)
        if not up.netloc:
            url = base_up.scheme + '://' + base_up.netloc + url
        elif not up.scheme:
            url = base_up.scheme + ':' + url
    return url


def process_url(url: str, dup_check: bool = False):
    """Save single URL to a file"""
    url = url.strip()
    print('Processing URL: %s' % url)

    if dup_check and is_downloaded(url):
        return

    page_content = get_text(url)
    soup = BeautifulSoup(page_content, 'html.parser')

    for img_tag in soup.find_all('img'):
        img_url = complete_url(img_tag['src'], base_url=url)
        print('New picture: %s' % img_url)
        img_b64 = get_embedded_binary(img_url)
        img_tag['src'] = img_b64

    for link_tag in soup.find_all('link'):
        link_url = complete_url(link_tag['href'], base_url=url)
        if 'stylesheet' in link_tag['rel']:
            print('New CSS: %s' % link_url)
            css_tag = soup.new_tag('style', media='screen', type='text/css')
            css_tag.string = get_text(link_url)
            link_tag.replace_with(css_tag)

    for script_tag in soup.find_all('script'):
        if script_tag.get('src') is None:
            continue
        script_url = complete_url(script_tag['src'], base_url=url)
        print('New script: %s' % script_url)
        script_b64 = get_embedded_binary(script_url)
        script_tag['src'] = script_b64

    write_file(soup.prettify(), soup.title.text, comment=url)


def main():
    parser = argparse.ArgumentParser(
        prog="nevernote.py",
        description="Nevernote - tool for downloading pages locally."
    )
    parser.add_argument("-i", "--infile",
                        help="File with URLs to download")
    parser.add_argument("-s", "--skip-dups", action="store_false",
                        default=True, dest="dup_check",
                        help="Rewrite already downloaded files")
    parser.add_argument('urls', metavar='URL', type=str, nargs='*',
                        default=sys.stdin,
                        help='URL of page to download')
    args = parser.parse_args()

    # Process URLs from the file
    if args.infile:
        try:
            fd = open(args.infile, 'r')
        except OSError as err:
            print(err)
            return 1
        for url in fd.readlines():
            process_url(url, dup_check=args.dup_check)
        fd.close()

    # Process URLs from CLI
    for arg in args.urls:
        process_url(arg, dup_check=args.dup_check)


if __name__ == '__main__':
    sys.exit(main())
