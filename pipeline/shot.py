# -*- coding: utf-8 -*-
"""截图抽查各章节渲染效果（阻断远程图片）"""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
url = (ROOT / "千问办公绿皮书.html").resolve().as_uri()

TARGETS = [
    ("#doc-desktop-hooks", "ch27"),
    ("#doc-enterprise-sso", "sso"),
    ("#doc-release-notes-desktop", "cl"),
    ("#doc-benefits-personal", "ben"),
    ("#doc-web-pages", "webpages"),
]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--disable-gpu"], timeout=25000)
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.set_default_timeout(20000)
    pg.route("**g-adoc.alcasset.com**", lambda r: r.abort())
    pg.goto(url, wait_until="commit", timeout=20000)
    pg.wait_for_timeout(1000)
    pg.add_style_tag(content="html{scroll-behavior:auto!important}")
    for sel, name in TARGETS:
        pg.eval_on_selector(sel, "el => el.scrollIntoView({block:'start'})")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(ROOT / "_work" / f"shot_{name}.png"))
        print("shot", name)
    b.close()
print("done")
