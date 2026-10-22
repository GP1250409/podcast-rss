import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import gen_rss

spec = importlib.util.spec_from_file_location('validate_rss', Path(__file__).parents[1] / 'scripts/validate_rss.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

class GeneratorTests(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(gen_rss.esc('a&<"'), 'a&amp;&lt;&quot;')

    def test_strip_html(self):
        self.assertEqual(gen_rss.strip_html('<p>A&amp;B<br/>C</p>'), 'A&B\nC')

    def test_generate_and_validate(self):
        podcast = {'title': 'Test & podcast', 'image': {'picUrl': 'https://example.com/cover.jpg'},
                   'author': 'Test', 'description': 'Description', 'episodes': [
                    {'eid': 'test-1', 'title': 'Episode & 1', 'pubDate': '2026-10-22T00:00:00Z',
                     'enclosure': {'url': 'https://example.com/audio.m4a'}, 'duration': 60}]}
        page = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({'props': {'pageProps': {'podcast': podcast}}}) + '</script>'
        with tempfile.TemporaryDirectory() as d:
            output = str(Path(d) / 'rss.xml')
            with patch.object(gen_rss, 'fetch', return_value=page), patch.object(gen_rss, 'head_size', return_value=123), patch.object(gen_rss, 'SELF_URL', validator.SELF_URL), patch.object(sys, 'argv', ['gen_rss.py', 'test', output]), contextlib.redirect_stdout(io.StringIO()):
                gen_rss.main()
                self.assertEqual(validator.validate(output), 1)
                data = Path(output).read_text().replace(validator.SELF_URL, 'https://example.com/wrong.xml')
                Path(output).write_text(data)
                with self.assertRaises(AssertionError):
                    validator.validate(output)

if __name__ == '__main__':
    unittest.main()
