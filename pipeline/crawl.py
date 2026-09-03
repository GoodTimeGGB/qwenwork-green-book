# -*- coding: utf-8 -*-
"""抓取千问办公知识库全部页面正文 -> _work/pages.json"""
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RAW.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# ---------- 1. 解析 llms.txt 得到分组 + 顺序 ----------
def parse_llms(path):
    txt = path.read_text(encoding="utf-8")
    groups, cur = [], None
    for line in txt.splitlines():
        if line.startswith("## "):
            cur = {"group": line[3:].strip(), "items": []}
            groups.append(cur)
        elif line.startswith("- [") and cur is not None:
            m = re.match(r"- \[(.+?)\]\((.+?)\)(?::\s*(.*))?", line)
            if m:
                cur["items"].append({
                    "title": m.group(1).strip(),
                    "url": m.group(2).strip(),
                    "desc": (m.group(3) or "").strip(),
                })
    return groups


def fetch(url, cache=None, retry=3):
    if cache and cache.exists() and cache.stat().st_size > 200:
        return cache.read_text(encoding="utf-8", errors="ignore")
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                s = r.read().decode("utf-8", errors="ignore")
            if cache:
                cache.write_text(s, encoding="utf-8")
            return s
        except Exception as e:
            print(f"   retry {i+1} {url}: {e}")
            time.sleep(2)
    return ""


# ---------- 2. 抽取正文 ----------
def extract_adoc(html):
    """docs.qwenwork.cn: .adoc-mdx-content / qwenwork.cn: .markdown-body"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1#page-title") or soup.select_one("h1")
    title = h1.get_text(strip=True) if h1 else ""
    eyebrow = soup.select_one("div.eyebrow")
    node = soup.select_one(".adoc-mdx-content") or soup.select_one(".markdown-body")
    body = str(node) if node else ""
    meta = ""
    if eyebrow:
        meta = eyebrow.get_text(strip=True)
    return title, clean_body(body), meta


def clean_body(h):
    # 去掉脚本/样式/按钮
    h = re.sub(r'<script\b.*?</script>', '', h, flags=re.S)
    h = re.sub(r'<style\b.*?</style>', '', h, flags=re.S)
    h = re.sub(r'<button\b.*?</button>', '', h, flags=re.S)
    # 去掉锚点链接图标
    h = re.sub(r'<a class="anchor[^"]*"[^>]*>.*?</a>', '', h, flags=re.S)
    # 标题里的 id 保留（做目录锚点）
    return h.strip()


def extract_release_notes(html):
    """更新日志页：按版本块解析，返回 (title, html)"""
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    title = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else "客户端更新日志"
    html = re.sub(r'<script\b.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<style\b.*?</style>', '', html, flags=re.S)
    # 每个版本条目：date + name + description + content
    parts = re.split(r'(?=<div class="[^"]*update-divider|<div[^>]*data-component-part="update-label")', html)
    out = []
    date_pat = re.compile(
        r'data-component-part="update-label">(.*?)</div>.*?'
        r'data-component-part="update-description">(.*?)</div>.*?'
        r'data-component-part="update-content">(.*?)</div>\s*</div>',
        re.S)
    found = False
    for date, name, content in date_pat.findall(html):
        found = True
        date = re.sub(r'<[^>]+>', '', date).strip()
        name = re.sub(r'<[^>]+>', '', name).strip()
        out.append({
            "date": date, "version": name, "html": content.strip(),
        })
    if not found:
        return title, ""
    return title, out


def main():
    llms = RAW / "llms_docs.txt"
    if not llms.exists():
        fetch("https://docs.qwenwork.cn/llms.txt", llms)
    groups = parse_llms(llms)

    pages = []
    n = 0
    for g in groups:
        for it in g["items"]:
            n += 1
            url = it["url"].replace(".md", "")
            slug = url.replace("https://docs.qwenwork.cn/", "").strip("/")
            cache = RAW / ("p_" + slug.replace("/", "__") + ".html")
            print(f"[{n:02d}] {g['group']} :: {it['title']}  {url}")
            html = fetch(url, cache)
            if not html:
                print("    !! FAILED")
                continue
            if slug.startswith("release-notes/"):
                title, content = extract_release_notes(html)
                kind = "release-notes"
                meta = ""
            else:
                title, content, meta = extract_adoc(html)
                kind = "doc"
            body_len = len(content) if isinstance(content, str) else sum(len(x["html"]) for x in content)
            print(f"    title={title!r} len={body_len}")
            pages.append({
                "group": g["group"], "nav_title": it["title"], "desc": it.get("desc", ""),
                "url": url, "slug": slug, "title": title or it["title"],
                "kind": kind, "content": content,
            })

    # 补充：qwenwork.cn 上独有页面（docs.qwenwork.cn 无 md）
    extra = [
        ("官方公告", "GLM-5.3 上线", "https://qwenwork.cn/docs/activity/glm-5.3-launch"),
        ("官方公告", "DeepSeek V4 Pro 会员不限量", "https://qwenwork.cn/docs/activity/deepseek-v4-pro-member-unlimited"),
    ]
    for grp, t, url in extra:
        slug = url.replace("https://qwenwork.cn/", "").strip("/")
        cache = RAW / ("p_x_" + slug.replace("/", "__") + ".html")
        print(f"[extra] {t} {url}")
        html = fetch(url, cache)
        if not html:
            print("    !! FAILED")
            continue
        title, content, meta = extract_adoc(html)
        print(f"    title={title!r} len={len(content)}")
        if len(content) > 200:
            pages.append({
                "group": grp, "nav_title": t, "desc": "", "url": url, "slug": slug,
                "title": title or t, "eyebrow": meta, "kind": "doc", "content": content,
            })

    (ROOT / "pages.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nTOTAL pages:", len(pages))
    print("empty:", [p["slug"] for p in pages if not p["content"]])


if __name__ == "__main__":
    main()
