# -*- coding: utf-8 -*-
"""把抓取的 HTML 正文清洗 + 组件语义化 -> _work/clean.json"""
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"

# 站内路径 -> 绿皮书内部锚点
SLUG_TO_ID = {}


def slug_id(slug: str) -> str:
    return "doc-" + slug.replace("/", "-")


CALLOUT_TYPE_HINTS = [
    ("warning", ["amber", "orange", "yellow", "text-amber", "text-orange"]),
    ("danger", ["red", "rose", "text-red"]),
    ("tip", ["green", "emerald", "text-green", "text-emerald"]),
    ("info", ["blue", "sky", "indigo", "text-blue"]),
]


CALLTYPE_MAP = {
    "note": "info",
    "tip": "tip",
    "info": "info",
    "warning": "warning",
    "caution": "warning",
    "danger": "danger",
    "important": "danger",
}


def guess_callout_type(el) -> str:
    # 1) 优先读 data-callout-type（站点原生标注，最可靠）
    node = el
    for _ in range(6):
        if node is None or getattr(node, "attrs", None) is None:
            break
        t = node.get("data-callout-type")
        if t:
            return CALLTYPE_MAP.get(str(t).lower(), "info")
        node = node.parent
    # 2) 退化：按颜色类名猜
    blob = " ".join(el.get("class") or [])
    parent = el.parent
    if parent is not None:
        blob += " " + " ".join(parent.get("class") or [])
    for name, hints in CALLOUT_TYPE_HINTS:
        if any(h in blob for h in hints):
            return name
    return "info"


def clean_tree(soup: BeautifulSoup):
    """通用垃圾清理"""
    for t in soup.find_all(["script", "style", "button", "noscript"]):
        t.decompose()
    # 复制按钮等纯界面残留
    for d in soup.find_all("div"):
        if d.get_text(strip=True) in ("Copy", "复制", "Copied") and not d.find("pre"):
            d.decompose()
    # 标题锚点链接
    for a in soup.select("a.heading-anchor"):
        a.decompose()
    # 纯装饰 svg 图标
    for svg in soup.find_all("svg"):
        parent = svg.parent
        if parent is not None and (parent.get("data-component-part") in ("card-icon",)
                                   or "lucide-arrow-up-right" in " ".join(svg.get("class") or [])):
            svg.decompose()
    for svg in soup.find_all("svg"):
        if "lucide" in " ".join(svg.get("class") or []) and svg.find_parent(["p", "h2", "h3"]):
            continue
    # 空 div
    for d in soup.find_all("div"):
        if not d.get_text(strip=True) and not d.find("img") and not d.get("data-component-part"):
            d.decompose()


def normalize_spans(soup: BeautifulSoup):
    """span[data-as=p] -> p 等"""
    for sp in soup.find_all("span", attrs={"data-as": True}):
        tag = sp["data-as"]
        if tag in ("p", "h1", "h2", "h3", "h4", "h5", "li", "blockquote", "div"):
            new = soup.new_tag(tag)
            new.attrs = {k: v for k, v in sp.attrs.items() if k != "data-as"}
            for c in list(sp.contents):
                new.append(c)
            sp.replace_with(new)


def convert_callouts(soup: BeautifulSoup):
    for el in soup.select('[data-component-part="callout-content"]'):
        root = el.parent
        while root and root.parent and "callout" not in " ".join(root.get("class") or []):
            root = root.parent
            if root.name == "div" and "callout" in " ".join(root.get("class") or []):
                break
        box = soup.new_tag("div")
        ctype = guess_callout_type(el)
        box["class"] = f"gb-callout gb-callout--{ctype}"
        for c in list(el.contents):
            box.append(c)
        target = root if (root and "callout" in " ".join(root.get("class") or [])) else el.parent
        target.replace_with(box)


def convert_code_blocks(soup: BeautifulSoup):
    for root in soup.select('[data-component-part="code-block-root"]'):
        pre = root.find("pre")
        if not pre:
            root.decompose()
            continue
        lang = pre.get("language") or pre.get("data-language") or ""
        new = soup.new_tag("pre")
        new["class"] = "gb-code"
        if lang:
            new["data-lang"] = lang
        code = soup.new_tag("code")
        # 只保留行文本，丢掉 shiki 的行内配色（绿皮书统一配色）
        for line in pre.select("span.line"):
            code.append(line.get_text())
            code.append("\n")
        if not code.get_text().strip():
            code.string = pre.get_text()
        new.append(code)
        root.replace_with(new)


def convert_images(soup: BeautifulSoup):
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            img.decompose()
            continue
        alt = img.get("alt") or ""
        # 文件名式 alt 不做图注
        cap_text = "" if re.search(r"\.(png|jpe?g|webp|gif|svg)\s*$", alt, re.I) else alt
        fig = soup.new_tag("figure")
        fig["class"] = "gb-fig"
        new = soup.new_tag("img")
        new["src"] = src
        new["alt"] = alt
        new["loading"] = "lazy"
        fig.append(new)
        if cap_text and cap_text not in ("产品界面", "image", "图片"):
            cap = soup.new_tag("figcaption")
            cap.string = cap_text
            fig.append(cap)
        img.replace_with(fig)


def convert_steps(soup: BeautifulSoup):
    for root in soup.select('[data-component-part="steps"]'):
        ol = soup.new_tag("ol")
        ol["class"] = "gb-steps"
        for item in root.select('[data-component-part="step-item"]'):
            li = soup.new_tag("li")
            title_el = item.select_one('[data-component-part="step-title"]')
            if title_el:
                st = soup.new_tag("strong")
                st["class"] = "gb-step-title"
                st.string = title_el.get_text(strip=True)
                li.append(st)
            content_el = item.select_one('[data-component-part="step-content"]')
            if content_el:
                for c in list(content_el.contents):
                    li.append(c)
            ol.append(li)
        root.replace_with(ol)


def convert_cards(soup: BeautifulSoup):
    for a in soup.select("a.card"):
        href = a.get("href") or ""
        inner = a.select_one('[data-component-part="card-content-container"]')
        if not inner:
            continue
        title_el = inner.select_one('[data-component-part="card-title"]')
        content_el = inner.select_one('[data-component-part="card-content"]')
        div = soup.new_tag("div")
        div["class"] = "gb-card"
        if title_el:
            t = soup.new_tag("div")
            t["class"] = "gb-card__title"
            t.string = title_el.get_text(strip=True)
            div.append(t)
        if content_el:
            c = soup.new_tag("div")
            c["class"] = "gb-card__body"
            for ch in list(content_el.contents):
                c.append(ch)
            div.append(c)
        if href.startswith("/"):
            sid = slug_id(href.strip("/"))
            if sid in SLUG_TO_ID:
                link = soup.new_tag("a")
                link["class"] = "gb-card__link"
                link["href"] = "#" + sid
                link.string = "查看章节 →"
                div.append(link)
        a.replace_with(div)


def group_cards(soup: BeautifulSoup):
    """把连续的 gb-card 合并进 .card-grid"""
    for card in list(soup.select(".gb-card")):
        if card.parent is not None and "card-grid" in " ".join(
                card.parent.get("class") or []):
            continue
        run = [card]
        nxt = card.next_sibling
        while nxt is not None:
            if getattr(nxt, "name", None) is None:
                if not str(nxt).strip():
                    nxt = nxt.next_sibling
                    continue
                break
            if "gb-card" in " ".join(nxt.get("class") or []):
                run.append(nxt)
                nxt = nxt.next_sibling
            else:
                break
        if len(run) < 2:
            continue
        grid = soup.new_tag("div")
        grid["class"] = "card-grid"
        card.insert_before(grid)
        for c in run:
            grid.append(c)


def convert_accordions(soup: BeautifulSoup):
    for d in soup.select("details.accordion"):
        title_el = d.select_one('[data-component-part="accordion-title"]')
        content_el = d.select_one('[data-component-part="accordion-content"]')
        nd = soup.new_tag("details")
        nd["class"] = "gb-acc"
        nd["open"] = "open"
        s = soup.new_tag("summary")
        s.string = title_el.get_text(strip=True) if title_el else "展开"
        nd.append(s)
        if content_el:
            for c in list(content_el.contents):
                nd.append(c)
        d.replace_with(nd)


def convert_tabs(soup: BeautifulSoup):
    for cont in soup.select("div.tab-container"):
        tabs = cont.select('[data-component-part="tab-button"]')
        panels = cont.select('[role="tabpanel"]') or cont.select('[data-component-part="tab-panel"]')
        wrap = soup.new_tag("div")
        wrap["class"] = "gb-tabs"
        labels = [t.get_text(strip=True) for t in tabs]
        for i, panel in enumerate(panels):
            box = soup.new_tag("div")
            box["class"] = "gb-tabs__panel"
            lab = soup.new_tag("div")
            lab["class"] = "gb-tabs__label"
            lab.string = labels[i] if i < len(labels) else f"选项 {i+1}"
            box.append(lab)
            for c in list(panel.contents):
                box.append(c)
            wrap.append(box)
        if not panels:  # 退化：直接保留文本
            cont.unwrap()
            continue
        cont.replace_with(wrap)


def convert_tables(soup: BeautifulSoup):
    for t in soup.find_all("table"):
        t["class"] = "gb-table"
        wrap = soup.new_tag("div")
        wrap["class"] = "gb-table-wrap"
        t.wrap(wrap)
        for th in t.find_all("th"):
            th["class"] = "gb-th"


def fix_links(soup: BeautifulSoup):
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if href.startswith("/") and not href.startswith("//"):
            sid = slug_id(href.strip("/").lstrip("/"))
            if sid in SLUG_TO_ID:
                a["href"] = "#" + sid
                a["class"] = "gb-internal-link"
            else:
                a["href"] = "https://docs.qwenwork.cn" + href
                a["target"] = "_blank"
        elif href.startswith("http"):
            a["target"] = "_blank"
            a["rel"] = "noopener"


def strip_attrs(soup: BeautifulSoup):
    for t in soup.find_all(True):
        if t.attrs is None:
            continue
        keep = {}
        if t.name == "a" and t.get("href"):
            keep["href"] = t["href"]
            if t.get("target"):
                keep["target"] = t["target"]
        if t.name == "img":
            keep["src"] = t.get("src", "")
            keep["alt"] = t.get("alt", "")
            keep["loading"] = "lazy"
        if t.name == "pre" and t.get("data-lang"):
            keep["data-lang"] = t["data-lang"]
        cls = t.get("class")
        if cls:
            cls_list = cls if isinstance(cls, list) else str(cls).split()
            if any(c.startswith("gb-") for c in cls_list):
                keep["class"] = cls_list
        t.attrs = keep


def process_doc(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one(".adoc-mdx-content") or soup.select_one(".markdown-body")
    if body is None:
        soup = BeautifulSoup('<div class="adoc-mdx-content">' + html + "</div>", "lxml")
        body = soup.select_one(".adoc-mdx-content")
    if not body:
        return ""
    clean_tree(body)
    normalize_spans(body)
    convert_callouts(body)
    convert_code_blocks(body)
    convert_images(body)
    convert_steps(body)
    convert_cards(body)
    group_cards(body)
    convert_accordions(body)
    convert_tabs(body)
    convert_tables(body)
    fix_links(body)
    strip_attrs(body)
    # 段落里嵌 figure/div 属于无效嵌套，解包
    for p in list(body.find_all("p")):
        if p.attrs is None or p.parent is None:
            continue
        if p.find(["figure", "table", "div"]):
            p.unwrap()
    # 收尾：删掉空壳 div（装饰层去掉后留下的）
    for _ in range(4):
        removed = False
        for d in list(soup.find_all("div")):
            if d.attrs is None or d.parent is None:
                continue
            cls = d.get("class") or []
            cls = cls if isinstance(cls, list) else str(cls).split()
            if any(c.startswith("gb-") for c in cls):
                continue
            if not d.get_text(strip=True) and not d.find(["img", "figure"]):
                d.decompose()
                removed = True
            elif not d.find(["p", "ul", "ol", "table", "pre", "figure", "h2", "h3",
                             "h4", "div", "li", "details", "img"]):
                d.unwrap()
                removed = True
        if not removed:
            break
    out = str(body)
    out = out.replace("\u200b", "")
    # 只压平「标签之间」的空白，代码块内部原样保留
    out = re.sub(r'>\s+<', '><', out)
    return out


def main():
    pages = json.loads((ROOT / "pages.json").read_text(encoding="utf-8"))
    for p in pages:
        SLUG_TO_ID[slug_id(p["slug"])] = p["slug"]
        if p["slug"].startswith("docs/"):
            SLUG_TO_ID[slug_id(p["slug"][5:])] = p["slug"]
    out = []
    for p in pages:
        if p["kind"] == "release-notes":
            ver = []
            for v in p["content"]:
                ver.append({**v, "html": process_doc(v["html"])})
            out.append({**p, "content": ver})
        else:
            out.append({**p, "content": process_doc(p["content"])})
    (ROOT / "clean.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("pages:", len(out))
    for p in out:
        n = sum(len(v["html"]) for v in p["content"]) if p["kind"] == "release-notes" else len(p["content"])
        print(f"  {p['slug']:45s} {n:7d}")


if __name__ == "__main__":
    main()
