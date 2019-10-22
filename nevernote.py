#!/usr/bin/python3

import argparse
import base64
import html.parser
import os
import re
import sys
from urllib.parse import urlparse

import requests

URLDUP = re.compile(r'^<!-- URL: (.*) -->$')


class TitleParser(html.parser.HTMLParser):
    def __init__(self, *args, **kwargs):
        html.parser.HTMLParser.__init__(self, *args, **kwargs)
        self.images = set()
        self.css = set()
        self.scripts = set()

    def handle_starttag(self, name, attribs):
        if name == 'img':
            for attr, value in attribs:
                if attr == 'src':
                    self.images.add(value)
        elif name == 'script':
            for attr, value in attribs:
                if attr == 'src':
                    self.scripts.add(value)
        elif name == 'title':
            titletag_start = self.rawdata.index('<title')
            title_start = self.rawdata.index('>', titletag_start) + 1
            title_end = self.rawdata.index('</title>', title_start)
            self.title = self.rawdata[title_start:title_end]
        elif name == 'link':
            attr_dict = dict(attribs)
            if attr_dict.get('rel') == 'stylesheet':
                self.css.add(attr_dict['href'])


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


def embed_pictures(page, pict_urls, base_url=None):
    """Write all pictures in HTML file"""
    for url in pict_urls:
        print('New picture: %s' % url)
        try:
            page = page.replace(
                url, get_embedded_binary(complete_url(url, base_url)))
        except requests.exceptions.HTTPError:
            pass
    return page


def embed_css(page, css_urls, base_url=None):
    """Write all CSS's in HTML file"""
    for url in css_urls:
        if not url:
            continue
        print('New CSS: %s' % url)
        css_start = page.rindex('<', 0, page.index(url))
        css_end = page.index('>', css_start) + 1
        css_tag = ('<style media="screen" type="text/css">%s</style>' % get_text(
            complete_url(url, base_url)))
        page = page[:css_start] + css_tag + page[css_end:]
    return page


def embed_scripts(page, script_urls, base_url=None):
    """Write all scripts in HTML file"""
    for url in script_urls:
        print('New script: %s' % url)
        try:
            page = page.replace(
                url, get_embedded_binary(complete_url(url, base_url)))
        except requests.exceptions.HTTPError:
            pass
    return page


def url_duplicate(url):
    """Check if url was already downloaded"""
    for htmlfile in os.listdir(path='.'):
        if not htmlfile.endswith('.html'):
            continue
        with open(htmlfile) as h:
            h_url = h.readline()
            if url in URLDUP.findall(h_url):
                raise UrlDuplicateError(
                    'URL is already saved in file "%s"' % htmlfile)


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


def process_url(url):
    """Save single URL to a file"""
    print('Processing URL: %s' % url)
    try:
        url_duplicate(url)
    except UrlDuplicateError as e:
        print(e)
        return

    try:
        page = get_text(url)
        parser = TitleParser()
        parser.feed(page)

        page = embed_pictures(page, parser.images, base_url=url)
        page = embed_css(page, parser.css, base_url=url)
        page = embed_scripts(page, parser.scripts, base_url=url)
    except requests.exceptions.HTTPError as e:
        print(e)
        return False

    write_file(page, parser.title, comment=url)


def main():
    parser = argparse.ArgumentParser(
        prog="nevernote.py",
        description="Nevernote - tool for downloading pages locally."
    )
    parser.add_argument("-i", "--infile",
                        help="File with URLs to download")
    parser.add_argument('urls', metavar='URL', type=str, nargs='*',
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
            process_url(url.strip())
        fd.close()

    # Process URLs from CLI
    for arg in args.urls:
        process_url(arg)


class UrlDuplicateError(Exception):
    pass


if __name__ == '__main__':
    sys.exit(main())
