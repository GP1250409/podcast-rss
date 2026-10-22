#!/usr/bin/env python3
"""抓小宇宙播客页 -> 生成标准播客 RSS（含媒体文件大小）。
用法: SELF_URL=https://example.com/x.xml python3 gen_rss.py <podcast_id> <out.xml>

小宇宙网页每次 SSR 只返回最新 15 期，够播客 App 日常订阅用。
"""
import json, re, sys, html, os, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1")
SELF_URL = os.environ.get("SELF_URL", "")


def fetch(url):
    return subprocess.run(["curl", "-fsSL", "--retry", "3", "--connect-timeout", "10",
                           "--max-time", "60", "-A", UA, url],
                          capture_output=True, check=True).stdout.decode("utf-8", "replace")


def head_size(url):
    common = ["curl", "-fsSL", "--retry", "2", "--connect-timeout", "10",
              "--max-time", "30", "-A", UA]
    head = subprocess.run(common + ["-I", url], capture_output=True)
    out = head.stdout.decode("utf-8", "replace")
    matches = re.findall(r"(?im)^content-length:\s*(\d+)", out)
    if head.returncode == 0 and matches and int(matches[-1]) > 0:
        return int(matches[-1])
    # Some CDN edges omit Content-Length for HEAD. A one-byte GET exposes
    # the full media size in Content-Range without downloading the episode.
    ranged = subprocess.run(common + ["--range", "0-0", "--max-filesize", "1024",
                                     "-D", "-", "-o", os.devnull, url], capture_output=True)
    out = ranged.stdout.decode("utf-8", "replace")
    total = re.findall(r"(?im)^content-range:\s*bytes\s+\d+-\d+/(\d+)", out)
    if ranged.returncode == 0 and total:
        return int(total[-1])
    lengths = re.findall(r"(?im)^content-length:\s*(\d+)", out)
    if ranged.returncode in (0, 63) and lengths and int(lengths[-1]) > 0:
        return int(lengths[-1])
    statuses = re.findall(r"(?im)^HTTP/\S+\s+\d+", out)
    raise RuntimeError(f"Cannot determine enclosure size: HEAD exit={head.returncode}; "
                       f"Range exit={ranged.returncode}; HTTP={statuses}")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", str(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def main():
    pid, out_path = sys.argv[1], sys.argv[2]
    raw = fetch(f"https://www.xiaoyuzhoufm.com/podcast/{pid}")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', raw, re.S)
    if not m:
        sys.exit("找不到 __NEXT_DATA__，页面结构可能变了")
    p = json.loads(m.group(1))["props"]["pageProps"]["podcast"]

    link = f"https://www.xiaoyuzhoufm.com/podcast/{pid}"
    img = p["image"]["picUrl"]
    now = format_datetime(datetime.now(timezone.utc))
    eps = p.get("episodes", [])
    total = len(eps)

    items = []
    for idx, e in enumerate(eps):
        url = e["enclosure"]["url"]
        size = head_size(url)
        dt = datetime.fromisoformat(e["pubDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
        desc = strip_html(e.get("shownotes") or e.get("description"))
        items.append(f"""    <item>
      <title>{esc(e['title'])}</title>
      <enclosure url="{esc(url)}" length="{size}" type="audio/mp4" />
      <guid isPermaLink="false">{esc(e['eid'])}</guid>
      <pubDate>{format_datetime(dt)}</pubDate>
      <itunes:duration>{int(e.get('duration') or 0)}</itunes:duration>
      <itunes:episode>{total - idx}</itunes:episode>
      <description>{esc(desc)}</description>
      <link>{esc('https://www.xiaoyuzhoufm.com/episode/' + e['eid'])}</link>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{esc(p['title'])}</title>
    <link>{esc(link)}</link>
    <atom:link href="{esc(SELF_URL)}" rel="self" type="application/rss+xml" />
    <description>{esc(strip_html(p.get('description') or p.get('brief')))}</description>
    <language>zh-cn</language>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{esc(p.get('author'))}</itunes:author>
    <itunes:summary>{esc(strip_html(p.get('description') or p.get('brief')))}</itunes:summary>
    <itunes:image href="{esc(img)}" />
    <image><url>{esc(img)}</url><title>{esc(p['title'])}</title><link>{esc(link)}</link></image>
    <itunes:explicit>false</itunes:explicit>
    <itunes:owner><itunes:name>{esc(p.get('author'))}</itunes:name></itunes:owner>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(out_path, "w", encoding="utf-8") as output:
        output.write(rss)
    print(f"{len(items)} 期 -> {out_path}")


if __name__ == "__main__":
    main()
