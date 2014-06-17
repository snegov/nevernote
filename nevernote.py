#!/usr/bin/python3

import argparse
import http.client
import html.parser
import sys
from urllib.parse import urlparse
import zlib


class TitleParser(html.parser.HTMLParser):
    def handle_data(self, data):
        if self.lasttag == 'title':
            self.title = data


def download_content(url):
    '''download page and decode it to utf-8'''
    up = urlparse(url)
    if not up.scheme:
        up = urlparse('//' + url)

    headers = {
        "Host": up.netloc,
        "Content-Type": "text/html; charset=utf-8",
        "Connection": "keep-alive",
    }

    if not up.scheme or up.scheme == 'http':
        conn = http.client.HTTPConnection(up.netloc)
    elif up.scheme == 'https':
        conn = http.client.HTTPSConnection(up.netloc)
    else:
        raise NotImplementedError("protocol %s is not implemented" % up.scheme)

    conn.request("GET", up.path, None, headers)
    response = conn.getresponse()

    # follow redirects
    if ((response.status == http.client.MOVED_PERMANENTLY)
            or (response.status == http.client.FOUND)):
        new_url = response.getheader('Location')
        print('Redirect to ' + new_url)
        return download_content(new_url)
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


def write_file(page):
    parser = TitleParser(strict=False)
    parser.feed(page)

    fname = parser.title + '.html'
    with open(fname, 'w') as a_file:
        a_file.write(page)


def main():
    parser = argparse.ArgumentParser(
        description='Nevernote - download pages locally.')
    parser.add_argument('urls', metavar='URL', type=str, nargs='+',
        help='URL of page to download')

    args = parser.parse_args()

    for url in args.urls:
        page = get_page(url)
        write_file(page)


if __name__ == '__main__':
    sys.exit(main())
