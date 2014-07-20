#!/usr/bin/python3

import argparse
import base64
import html.parser
import os
import re
import sys
import urllib.error
from urllib.parse import urlparse
from urllib.request import urlopen
import zlib


class UrlDuplicateError(Exception): pass
URLDUP = re.compile(r'^<!-- URL: (.*) -->$')


class TitleParser(html.parser.HTMLParser):
    def __init__(self, *args, **kwargs):
        html.parser.HTMLParser.__init__(self, *args, **kwargs)
        self.images = set()
        self.css = set()

    def handle_starttag(self, name, attribs):
        if name == 'img':
            for attr, value in attribs:
                if attr == 'src':
                    self.images.add(value)
        elif name == 'title':
            titletag_start = self.rawdata.index('<title')
            title_start = self.rawdata.index('>', titletag_start) + 1
            title_end = self.rawdata.index('</title>', title_start)
            self.title = self.rawdata[title_start:title_end]
        elif name == 'link':
            attr_dict = dict(attribs)
            if attr_dict.get('rel') == 'stylesheet':
                self.css.add(attr_dict['href'])


def charset_header(content_type):
    """ Parse charset from 'content-type' header
    :param content_type: string
    :return: string with character set
    """
    if 'charset' in content_type:
        return content_type.split(';')[1].split('=')[1]
    else:
        return None


def get_text(url, content='text/html', charset='utf-8'):
    response = urlopen(url)
    if response.status != 200:
        raise urllib.error.HTTPError('Incorrect HTTP status (%d, %s) for %s' % (
                response.status, response.reason, url))
    ctype = response.headers.get('content-type')
    if ctype is None:
        raise RuntimeError('None content type for %s' % url)
    if not ctype.startswith(content):
        raise RuntimeError('Incorrect content-type for %s: %s' % (url, ctype))

    # get charset from 'Content-type' header
    charset = charset_header(ctype) or charset

    if response.info().get('Content-Encoding') == 'gzip':
        data = zlib.decompress(response.read(), 16+zlib.MAX_WBITS)
    else:
        data = response.read()
    page = data.decode(charset.lower())
    return page


def embedded_image(url):
    '''Download content from URL and return bytes if target is image'''
    u = urlopen(url)
    if u.status != 200:
        raise urllib.error.HTTPError('Incorrect HTTP status (%d, %s) for %s' % (
                u.status, u.reason, url))
    ctype = u.headers.get('Content-Type')
    data = u.read()
    b64pict = base64.b64encode(data).decode()
    return 'data:%s;base64,%s' % (ctype, b64pict)


def embed_pictures(page, pict_urls, base_url=None):
    for url in pict_urls:
        print('New picture: %s' % url)
        try:
            page = page.replace(
                url, embedded_image(complete_url(url, base_url)))
        except urllib.error.HTTPError:
            pass
    return page


def embed_css(page, css_urls, base_url=None):
    # fetch charset from base URL or use default UTF-8
    if base_url is not None:
        hdr = urlopen(base_url).headers.get('content-type')
        base_char = charset_header(hdr) if hdr is not None else None
        base_char = base_char or 'utf-8'
    for url in css_urls:
        if not url:
            continue
        print('New CSS: %s' % url)
        css_start = page.rindex('<', 0, page.index(url))
        css_end = page.index('>', css_start) + 1
        css_tag = ('<style media="screen" type="text/css">%s</style>' % get_text(
            complete_url(url, base_url), content='text/css',charset=base_char))
        page = page[:css_start] + css_tag + page[css_end:]
    return page


def url_duplicate(url):
    for htmlfile in os.listdir():
        if not htmlfile.endswith('.html'):
            continue
        with open(htmlfile) as h:
            h_url = h.readline()
            if url in URLDUP.findall(h_url):
                raise UrlDuplicateError(
                    'URL is already saved in file "%s"' % htmlfile)


def write_file(page, title, comment=None):
    write_inc = lambda i: '_%d' % i if i > 1 else ''
    inc = 0
    while True:
        inc += 1
        fname = ' '.join(title.replace('/', '_').split()) + write_inc(inc) + '.html'
        if not os.path.exists(fname):
            break

    with open(fname, 'x', newline='\n') as a_file:
        print('Saving in file "%s"' % fname)
        if comment:
            a_file.write('<!-- URL: %s -->\n' % comment)
        a_file.write(page)


def complete_url(url, base_url):
    base_up = urlparse(base_url)
    if base_url is not None:
        up = urlparse(url)
        if not up.netloc:
            url = base_up.scheme + '://' + base_up.netloc + url
        elif not up.scheme:
            url = base_up.scheme + ':' + url
    return url


def process_url(url):
    print('Processing URL: %s' % url)
    try:
        url_duplicate(url)
    except UrlDuplicateError as e:
        print(e)
        return

    try:
        page = get_text(url)
        parser = TitleParser(strict=False)
        parser.feed(page)

        page = embed_pictures(page, parser.images, base_url=url)
        page = embed_css(page, parser.css, base_url=url)
    except urllib.error.HTTPError as e:
        print('Error with URL "%s": %s' % (url,e))
        return False

    write_file(page, parser.title, comment=url)


def main():
    parser = argparse.ArgumentParser(
        description='Nevernote - download pages locally.')
    parser.add_argument('urls', metavar='URL', type=str, nargs='+',
        help='URL of page to download')
    args = parser.parse_args()

    for arg in args.urls:
        if os.path.isfile(arg):
            print('Found file %s' % arg)
            for url in (line.strip() for line in open(arg)):
                process_url(url)
        else:
            process_url(arg)


if __name__ == '__main__':
    sys.exit(main())
