#!/usr/bin/env python3
"""Validate the small public RSS artifact before and after Pages publishing."""
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

SELF_URL = 'https://rss.gpnet.cc.cd/ai-zaozhidao.xml'

def validate(path):
    root = ET.parse(path).getroot()
    assert root.tag == 'rss' and root.get('version') == '2.0'
    channel = root.find('channel')
    assert channel is not None and channel.findtext('title')
    atom = channel.find('{http://www.w3.org/2005/Atom}link')
    assert atom is not None and atom.get('href') == SELF_URL and atom.get('rel') == 'self'
    items = channel.findall('item')
    assert 1 <= len(items) <= 15, f'unexpected item count: {len(items)}'
    guids = []
    for item in items:
        assert item.findtext('title')
        guid = item.findtext('guid'); assert guid
        guids.append(guid)
        assert parsedate_to_datetime(item.findtext('pubDate')).tzinfo is not None
        enclosure = item.find('enclosure'); assert enclosure is not None
        assert enclosure.get('url', '').startswith('https://')
        assert enclosure.get('type', '').startswith('audio/')
        assert int(enclosure.get('length', '0')) > 0, 'missing enclosure size'
    assert len(guids) == len(set(guids)), 'duplicate GUIDs'
    print(f'RSS OK: {len(items)} items; self URL and enclosure metadata valid')
    return len(items)

if __name__ == '__main__':
    validate(sys.argv[1])
