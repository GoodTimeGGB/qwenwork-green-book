# -*- coding: utf-8 -*-
"""抓取微信公众号文章，作为《千问办公绿皮书》的补充内容。

用法：
    python crawl_wx.py                     # 抓取 wx_sources.txt 里的全部链接
    python crawl_wx.py <url> [<url> ...]   # 抓取指定链接

产出：
    wx_raw/<n>.html      原始页面
    wx_assets/<hash>.png 下载并压缩后的图片
    wx_articles.json     结构化数据（供 build.py 消费）

设计要点：
1. 微信正文在 `#js_content` 里，图片地址在 `data-src`（src 为空，懒加载）。
2. mmbiz.qpic.cn 有 Referer 防盗链，必须带 Referer 下载。
3. 动图（GIF）体积常常几 MB，统一抽帧拼成静态网格图再内联，避免单文件膨胀。
4. 135editor 排版会产生大量嵌套空 section，需要逐层清理。
"""
import datetime
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "wx_raw"
ASSET_DIR = ROOT / "wx_assets"
SOURCES = ROOT / "wx_sources.txt"
OUT_JSON = ROOT / "wx_articles.json"

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 MicroMessenger/8.0.49")
REFERER = "https://mp.weixin.qq.com/"

# 内联体积预算：超过就抽帧/压缩
# 多篇文章合入书本时体积会线性叠加，可用环境变量调紧：
#   WX_MAX_KB   单图字节上限（KB，默认 260）
#   WX_MAX_W    图片最大宽度（像素，默认 820）
MAX_INLINE_BYTES = int(float(os.environ.get("WX_MAX_KB", "260")) * 1024)
MAX_WIDTH = int(os.environ.get("WX_MAX_W", "820"))
GIF_MAX_FRAMES = 6


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def fetch_bytes(url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": REFERER,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ------------------------------------------------------------------ 元信息
def extract_meta(html: str, url: str) -> dict:
    def var(name):
        """读页面里的 `var xxx = "..."` / meta 标签。注意别用 raw string 写引号，会留下反斜杠。"""
        m = re.search('var\\s+' + name + '\\s*=\\s*["\']([^"\']*)', html)
        if m:
            return m.group(1).strip()
        m = re.search('["\']' + name + '["\']\\s*:\\s*["\']([^"\']*)', html)
        return m.group(1).strip() if m else ""

    def meta_prop(prop):
        m = re.search(r'<meta property="%s" content="([^"]*)"' % prop, html)
        return m.group(1).strip() if m else ""

    ct = (var("create_time") or var("ct")).replace("*", "").split(".")[0].strip()
    ts = int(ct) if ct.isdigit() else int(time.time())
    title = var("msg_title") or meta_prop("og:title")
    desc = var("msg_desc") or meta_prop("og:description")
    cover = var("msg_cdn_url") or meta_prop("og:image")
    author = meta_prop("og:article:author") or var("author") or "千问办公"
    # 搜狗等中转链接带时效签名，优先用页面里的规范链接（__biz+mid+idx+sn）
    canon = (var("msg_link") or "").replace("&amp;", "&").strip()
    if canon.startswith("http"):
        url = canon
    return {
        "title": title or "（无标题）",
        "desc": desc,
        "cover": cover,
        "author": author or "千问办公",
        "published": datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
        "published_ts": ts,
        "url": url,
    }


def extract_content_div(html: str) -> str:
    """截取 #js_content 的正文片段（从该标签的 '>' 之后开始，避免残留裸属性文本）。

    贴图类消息（图片消息）没有 #js_content，退回 js_image_content 等容器。
    """
    i = html.find('id="js_content"')
    if i < 0:
        for alt in ('id="js_image_content"', 'id="js_article"', 'class="rich_media_content'):
            j = html.find(alt)
            if j >= 0:
                i = j
                break
    if i < 0:
        return ""
    gt = html.find(">", i)
    if gt < 0:
        return ""
    seg = html[gt + 1:]
    end = -1
    for mark in ('id="js_pc_qr_code"', 'id="content_bottom_area"', 'id="js_related"',
                 'id="js_profile_qrcode"', 'id="js_image_content_end"'):
        j = seg.find(mark)
        if j > 0 and (end < 0 or j < end):
            end = j
    return seg[:end] if end > 0 else seg[:400_000]


# ------------------------------------------------------------------ 图片处理
def compress_image(data: bytes, src_url: str, max_bytes: int = MAX_INLINE_BYTES) -> bytes:
    """把图片压到体积预算内，返回 WebP 字节。动图先抽帧拼网格。

    用 WebP 而不是 JPEG：公众号正文以界面截图为主，WebP 在同等观感下
    体积约省 30~50%，直接决定「单文件 base64 内联」的成品大小。
    """
    im = Image.open(io.BytesIO(data))
    is_gif = getattr(im, "n_frames", 1) > 1 or im.format == "GIF"

    if is_gif:
        n = getattr(im, "n_frames", 1)
        k = min(GIF_MAX_FRAMES, n)
        idxs = sorted({min(int(n * x / k), n - 1) for x in range(k)})
        frames = []
        for i in idxs:
            im.seek(i)
            frames.append(im.convert("RGB"))
        cols = 2 if k > 1 else 1
        rows = (len(frames) + cols - 1) // cols
        tw = min(frames[0].width, 760) // cols
        ths = [max(1, int(f.height * tw / f.width)) for f in frames]
        rh = max(ths)
        canvas = Image.new("RGB", (tw * cols, rh * rows), "white")
        for idx, f in enumerate(frames):
            r, c = divmod(idx, cols)
            canvas.paste(f.resize((tw, ths[idx]), Image.LANCZOS), (c * tw, r * rh))
        im = canvas

    im = im.convert("RGB") if im.mode in ("RGBA", "LA", "P") and not is_gif else im
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")

    # 限制最大宽度，公众号图普遍 1080 宽，缩到 MAX_WIDTH 足够阅读
    if im.width > MAX_WIDTH:
        h = int(im.height * MAX_WIDTH / im.width)
        im = im.resize((MAX_WIDTH, h), Image.LANCZOS)

    quality = 86
    while quality >= 55:
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=6)
        if buf.tell() <= max_bytes or quality == 55:
            return buf.getvalue()
        quality -= 8
    return buf.getvalue()


def localize_images(soup: BeautifulSoup, cache: dict, log: list):
    """把正文里的 data-src 图片下载并替换为本地相对路径。"""
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if not src.startswith("http"):
            img.decompose()
            continue
        key = src.split("?")[0]
        if key in cache:
            img["src"] = cache[key]
        else:
            try:
                raw = fetch_bytes(src)
                small = compress_image(raw, src)
                name = hashlib.md5(key.encode()).hexdigest()[:12] + ".webp"
                (ASSET_DIR / name).write_bytes(small)
                cache[key] = "wx_assets/" + name
                img["src"] = cache[key]
                log.append("  img ok %6.1fKB -> %6.1fKB  %s"
                           % (len(raw) / 1024, len(small) / 1024, name))
            except Exception as e:  # 图片失败不能拖垮整篇
                log.append("  img FAIL %s (%s)" % (src[:60], e))
                img.decompose()
                continue
        img["loading"] = "lazy"
        img.attrs.pop("data-src", None)
        img.attrs.pop("data-aistatus", None)
        img.attrs.pop("data-imgfileid", None)
        img.attrs.pop("data-ratio", None)
        img.attrs.pop("data-w", None)
        img.attrs.pop("data-type", None)
        img["class"] = "wx-img"


# ------------------------------------------------------------------ 正文清洗
DROP_TEXT = {"预览时标签不可点", "阅读原文", "微信扫一扫", "关注该公众号",
             "轻点两下取消赞", "赞", "在看", "分享", "收藏"}


KEEP_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "img", "strong", "em", "b", "i",
             "br", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td", "a"}
SENT_END = "。！？；!?…"


def clean_content(div_html: str, cache: dict, log: list) -> list:
    """把 135editor 产出的嵌套 section 压平成 (类型, 内容) 块列表。"""
    soup = BeautifulSoup(div_html, "lxml")
    root = soup.select_one("#js_content") or soup.select_one("body") or soup

    for t in root.find_all(["script", "style", "svg", "noscript", "mp-style-type", "iframe"]):
        t.decompose()

    localize_images(root, cache, log)

    # 清掉所有非保留标签（135editor 的 section/span/div 壳），只保留结构与行内语义
    for t in list(root.find_all(True)):
        if t.name not in KEEP_TAGS:
            t.unwrap()
        else:
            keep = {}
            if t.name == "img" and t.get("src"):
                keep = {"src": t["src"], "class": "wx-img", "loading": "lazy"}
            elif t.name == "a" and t.get("href"):
                keep = {"href": t["href"]}
            t.attrs = keep

    # 空块清掉
    for t in list(root.find_all(KEEP_TAGS - {"img", "br"})):
        if t.parent is not None and not t.get_text(strip=True) and not t.find("img"):
            t.decompose()

    # 按文档顺序收集块级节点
    blocks = []
    for node in root.find_all(["p", "h1", "h2", "h3", "h4", "h5", "img", "ul", "ol", "table"]):
        if node.find_parent(["p", "li", "td"]):
            continue  # 嵌套在段落里的，交给父块统一处理
        if node.name == "img":
            blocks.append(("img", node.get("src", "")))
            continue
        if node.name in ("ul", "ol", "table"):
            blocks.append(("raw", str(node)))
            continue
        # 段落：先取出内部图片，图片独立成块跟在段落后面
        txt = node.get_text(" ", strip=True)
        imgs = [im.get("src", "") for im in node.find_all("img")]
        if not txt and not imgs:
            continue
        if txt in DROP_TEXT:
            continue
        if imgs:
            for s in imgs:
                blocks.append(("img", s))
            if not txt:
                continue
        blocks.append(("p", txt))

    return merge_fragments(blocks)


def merge_fragments(blocks: list) -> list:
    """合并被 135editor 拆碎的段落片段，并识别 01/02 章节小标题。"""
    merged = []
    for kind, val in blocks:
        if kind != "p":
            merged.append((kind, val))
            continue
        if merged and merged[-1][0] == "p" and _should_merge(merged[-1][1], val):
            merged[-1] = ("p", merged[-1][1] + val)
        else:
            merged.append((kind, val))

    out = []
    n = len(merged)
    for i, (kind, val) in enumerate(merged):
        if kind != "p":
            out.append((kind, val))
            continue
        # 章节序号小标题：01 / 02 …，句号级标点结尾的不算
        m = re.match(r"^(\d{2})\s*([^\s].{0,40})$", val)
        if m and not re.search(r"[。！？!?…]", m.group(2)):
            out.append(("h3", "%s %s" % (m.group(1), m.group(2))))
            continue
        if val in ("滑动查看完整内容", "左右滑动查看"):
            out.append(("note", val))
            continue
        # 纯装饰分隔点
        if re.fullmatch(r"[·.\-—\s]+", val):
            out.append(("divider", val))
            continue
        # 短句小标题（四级）：短、无句末标点、后面跟着完整段落
        nxt = merged[i + 1][1] if i + 1 < n and merged[i + 1][0] == "p" else ""
        if (len(val) <= 24 and not re.search(r"[。！？!?…]", val)
                and len(nxt) > len(val) * 1.6 and out):
            out.append(("h4", val))
            continue
        out.append((kind, val))
    return out


def _should_merge(prev: str, nxt: str) -> bool:
    """判断 nxt 是不是 prev 的续写片段。"""
    if not prev or not nxt:
        return False
    if prev[-1] in SENT_END:
        return False
    # 下一块以标点开头，必定是续写
    if nxt[0] in "，。、；：）」』”’!?！？":
        return True
    # 上一块明显没说完（以连接词/介词收尾）
    if re.search(r"(涵盖|包括|如下|为|是|有|的|和|与|并|让|把|将|在|对|从|—|-|、|：|:|，)$", prev):
        return True
    # 短片段（如强调句、行内高亮）跟在长句后
    if len(nxt) <= 30 and len(prev) >= 12:
        return True
    return False


def blocks_to_html(blocks) -> str:
    out = []
    # 开篇徽标（如 "QwenWork Product"）单独提出来作眉标
    if blocks and blocks[0][0] == "p" and len(blocks[0][1]) <= 24 \
            and not re.search(r"[。！？!?…]", blocks[0][1]):
        out.append('<p class="wx-eyebrow">%s</p>' % html_escape(blocks[0][1]))
        blocks = blocks[1:]
    for kind, val in blocks:
        if kind == "h3":
            m = re.match(r"^(\d{2})\s*(.+)$", val)
            if m:
                out.append('<h3 class="wx-sec"><span class="wx-sec__num">%s</span>%s</h3>'
                           % (m.group(1), html_escape(m.group(2))))
            else:
                out.append('<h3 class="wx-sec">%s</h3>' % html_escape(val))
        elif kind == "img":
            out.append('<figure class="gb-fig"><img class="wx-img" src="%s" loading="lazy" alt=""></figure>'
                       % html_escape(val, True))
        elif kind == "h4":
            out.append('<h4 class="wx-sub">%s</h4>' % html_escape(val))
        elif kind == "note":
            out.append('<p class="wx-hint">%s</p>' % html_escape(val))
        elif kind == "divider":
            out.append('<div class="wx-divider" aria-hidden="true"></div>')
        elif kind == "raw":
            out.append(val)
        else:
            out.append("<p>%s</p>" % html_escape(val))
    return "\n".join(out)


def html_escape(s: str, quote: bool = False):
    import html as _h
    return _h.escape(s, quote=quote)


# ------------------------------------------------------------------ 主流程
def process(url: str, idx: int, cache: dict) -> dict:
    log = []
    html = fetch(url)
    (RAW_DIR / ("%02d.html" % idx)).write_text(html, encoding="utf-8")

    meta = extract_meta(html, url)
    log.append("  标题：%s（%s，%s）" % (meta["title"], meta["author"], meta["published"]))

    blocks = clean_content(extract_content_div(html), cache, log)

    # 贴图类消息兜底：正文容器拿不到内容时，把整页的 mmbiz 图片按顺序收进来
    if not blocks:
        log.append("  正文为空，按图片消息处理")
        soup = BeautifulSoup(html, "lxml")
        imgs = []
        for im in soup.find_all("img"):
            src = im.get("data-src") or im.get("src") or ""
            if "mmbiz" in src:
                imgs.append(("img", src))
        if imgs:
            fake = BeautifulSoup('<div id="js_content">' + "".join(
                '<p><img data-src="%s"></p>' % s for _, s in imgs) + "</div>", "lxml")
            blocks = clean_content(str(fake), cache, log)

    # 首段之前插入导语卡
    body = blocks_to_html(blocks)

    cover_local = ""
    if meta["cover"]:
        key = meta["cover"].split("?")[0]
        try:
            if key not in cache:
                raw = fetch_bytes(meta["cover"])
                small = compress_image(raw, meta["cover"], max(45 * 1024, min(120 * 1024, MAX_INLINE_BYTES)))
                name = hashlib.md5(key.encode()).hexdigest()[:12] + ".webp"
                (ASSET_DIR / name).write_bytes(small)
                cache[key] = "wx_assets/" + name
                log.append("  cover ok %6.1fKB -> %6.1fKB" % (len(raw) / 1024, len(small) / 1024))
            cover_local = cache[key]
        except Exception as e:
            log.append("  cover FAIL %s" % e)

    meta["cover_local"] = cover_local
    meta["content"] = body
    meta["slug"] = "wx/" + hashlib.md5(url.encode()).hexdigest()[:10]
    meta["n_img"] = body.count("<img")
    meta["n_block"] = len(blocks)
    log.append("  正文块 %d 个，图片 %d 张" % (meta["n_block"], meta["n_img"]))
    print("\n".join(log))
    return meta


def article_id(url: str) -> str:
    """从 https://mp.weixin.qq.com/s/<22位ID> 里取出文章 ID"""
    m = re.search(r"/s/([A-Za-z0-9_\-]{16,})", url or "")
    return m.group(1) if m else ""


def dedupe(articles: list) -> list:
    """同一篇文章可能以两种 URL 入库：干净的 /s/<id>，或搜狗的 src=11 签名链接。
    按「文章ID → 标题」两级去重，保留信息更全且链接更稳定的那一条。"""
    def score(a):
        s = 0
        if article_id(a.get("url", "")):
            s += 100                                     # 规范链接优先
        s += min(len(a.get("content") or "") // 500, 40)  # 正文更全
        s += min(int(a.get("n_img") or 0), 30)            # 图更多
        return s

    def pick(pool):
        out = {}
        for a in pool:
            key = article_id(a.get("url", "")) or (a.get("title") or "").strip()
            if key not in out or score(a) > score(out[key]):
                out[key] = a
        return list(out.values())

    stage1 = pick(articles)                              # 按文章 ID
    stage2 = {}
    for a in stage1:                                     # 再按标题兜底
        t = (a.get("title") or "").strip()
        if t not in stage2 or score(a) > score(stage2[t]):
            stage2[t] = a
    return list(stage2.values())


def main():
    RAW_DIR.mkdir(exist_ok=True)
    ASSET_DIR.mkdir(exist_ok=True)

    urls = sys.argv[1:]
    if not urls:
        if SOURCES.exists():
            urls = [l.strip() for l in SOURCES.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]
        else:
            print("没有待抓取链接：把 URL 写进 wx_sources.txt 或作为参数传入")
            return

    existing = []
    if OUT_JSON.exists():
        existing = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    have = {a["url"]: a for a in existing}
    cache = {a.get("cover", ""): a.get("cover_local", "") for a in existing if a.get("cover_local")}

    for i, url in enumerate(urls, start=1):
        print("[%d/%d] %s" % (i, len(urls), url))
        try:
            have[url] = process(url, i, cache)
        except Exception as e:
            print("  FAIL:", e)

    before = len(have)
    articles = dedupe(list(have.values()))
    if len(articles) < before:
        print("去重：%d -> %d 篇（同文多链接合并）" % (before, len(articles)))
    articles = sorted(articles, key=lambda a: a.get("published_ts", 0), reverse=True)
    OUT_JSON.write_text(json.dumps(articles, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n写入 %s（共 %d 篇）" % (OUT_JSON.name, len(articles)))


if __name__ == "__main__":
    main()
