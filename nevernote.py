#!/usr/bin/python3

import argparse
import base64
import http.client
import html.parser
import os.path
import sys
from urllib.parse import urlparse
import zlib


class InfiniteRedirects(Exception): pass


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


def download_content(url, depth=0):
    '''download page and decode it to utf-8'''
    if depth > 10:
        raise InfiniteRedirects('too much redirects: %s' % url)

    up = urlparse(url)
    if not up.netloc:
        up = urlparse('//' + url)

    headers = {
        "Host": up.netloc,
        "Connection": "keep-alive",
    }

    if not up.scheme or up.scheme == 'http':
        conn = http.client.HTTPConnection(up.netloc)
    elif up.scheme == 'https':
        conn = http.client.HTTPSConnection(up.netloc)
    else:
        raise NotImplementedError("protocol %s is not implemented" % up.scheme)

    conn.request("GET", '?'.join((up.path, up.query)), None, headers)
    response = conn.getresponse()

    # follow redirects
    if ((response.status == http.client.MOVED_PERMANENTLY)
            or (response.status == http.client.FOUND)):
        new_url = response.getheader('Location')
        print('Redirecting to ' + new_url)
        return download_content(new_url, depth+1)
    return response


def get_page(url):
    response = download_content(url)

    # get page charset from response header
    c_type = response.getheader('Content-Type')
    if not c_type.startswith('text'):
        raise ValueError('incorrect Content-Type for HTML page: %s' % c_type)

    c_encoding = response.getheader('Content-Encoding')
    if c_encoding:
        if c_encoding == 'gzip':
            page_binary = zlib.decompress(response.read(), 16+zlib.MAX_WBITS)
        else:
            raise NotImplementedError(
                'content encoding %s is not implemented' % c_encoding)
    else:
        page_binary = response.read()

    charset = 'iso-8859-1'
    ct_spl = c_type.split('; ')
    if len(ct_spl) > 1:
        charset = ct_spl[1].split('=')[1]
    page = page_binary.decode(charset)

    return page


def embedded_image(url):
    '''Download content from URL and return bytes if target is image'''
    response = download_content(url)
    ctype = response.getheader('Content-Type')
    if not ctype or not ctype.startswith('image'):
        raise ValueError('incorrect Content-Type for image: %s' % ctype)
    b64pict = base64.b64encode(response.read()).decode()
    return 'data:%s;base64,%s' % (ctype, b64pict)


def embed_pictures(page, pict_urls, base_url=None):
    for url in pict_urls:
        print('New picture: %s' % url)
        try:
            page = page.replace(
                url, embedded_image(complete_url(url, base_url)))
        except (ValueError, InfiniteRedirects, ConnectionRefusedError):
            pass
    return page


def embed_css(page, css_urls, base_url=None):
    for url in css_urls:
        if not url:
            continue
        print('New CSS: %s' % url)
        try:
            css_start = page.rindex('<', 0, page.index(url))
            css_end = page.index('>', css_start) + 1
            css = ('<style media="screen" type="text/css">%s</style>'
                   % get_page(complete_url(url, base_url)))
            page = page[:css_start] + css + page[css_end:]
        except (InfiniteRedirects, ConnectionRefusedError):
            pass
    return page


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
        a_file.write(page)
        if comment:
            a_file.write('<!-- URL: %s -->' % comment)


def complete_url(url, base_url):
    if base_url is not None:
        up = urlparse(url)
        if not up.netloc:
            url = '//' + urlparse(base_url).netloc + url
    return url


def main():
    parser = argparse.ArgumentParser(
        description='Nevernote - download pages locally.')
    parser.add_argument('urls', metavar='URL', type=str, nargs='+',
        help='URL of page to download')
    args = parser.parse_args()

    for url in args.urls:
        page = get_page(url)
        parser = TitleParser(strict=False)
        parser.feed(page)

        page = embed_pictures(page, parser.images, base_url=url)
        page = embed_css(page, parser.css, base_url=url)
        write_file(page, parser.title, comment=url)


if __name__ == '__main__':
    sys.exit(main())
