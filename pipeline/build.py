# -*- coding: utf-8 -*-
"""把 clean.json 组装成单文件 HTML《千问办公绿皮书》"""
import base64
import html as html_mod
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / "gb_style.css").read_text(encoding="utf-8")

# 官方公众号补充文章（由 crawl_wx.py 产出）
WX_FILE = ROOT / "wx_articles.json"
WX_ARTICLES = json.loads(WX_FILE.read_text(encoding="utf-8")) if WX_FILE.exists() else []

# 参考站 CSS 里写死的英文串，替换成千问办公（保留 follow-cta 关注卡片样式）
CSS = CSS.replace("WORKBUDDY GREEN BOOK", "QWENWORK GREEN BOOK")
CSS = CSS.replace('content: "WorkBuddy 绿皮书"', 'content: "千问办公绿皮书"')

# ---------------------------------------------------------------- 公众号品牌
GZH_QR_FILE = ROOT / "wx_assets" / "gzh_qr.jpg"
GZH_QR_B64 = (
    "data:image/jpeg;base64,"
    + base64.b64encode(GZH_QR_FILE.read_bytes()).decode("ascii")
    if GZH_QR_FILE.exists()
    else ""
)

def _wm_svg() -> str:
    """斜排平铺水印 SVG（data URI）"""
    from urllib.parse import quote
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='460' height='360'>"
        "<text x='230' y='185' font-size='30' fill='rgb(96,134,110)' fill-opacity='0.05'"
        " text-anchor='middle' transform='rotate(-22 230 185)'"
        " font-family='Georgia,serif' font-weight='700' letter-spacing='8'>宁的AI小站</text>"
        "</svg>"
    )
    return "url(\"data:image/svg+xml;charset=utf-8," + quote(svg) + "\")"

FOLLOW_CTA = """
<div class="follow-cta noprint-follow">
  <div class="follow-left">
    <div class="follow-title">关注公众号「宁的 AI 小站」</div>
    <div class="follow-desc">全栈 · AI 讲师 · 社区主理人。每日 AI 实战、AI 办公技巧与工具复盘，在这里持续更新。</div>
    <div class="follow-actions">
      <span class="follow-pill">扫描公众号回复「千问」获取本书电子版 PDF</span>
      <span class="follow-pill">扫描公众号回复「加群」加入 AI 小站交流群</span>
    </div>
  </div>
  <img class="gzh-qr" src="{qr}" alt="宁的AI小站公众号二维码">
</div>
""".format(qr=GZH_QR_B64)

EXTRA_CSS = """
  /* ========== 千问办公文档组件适配 ========== */
  .gb-table-wrap { overflow-x: auto; margin: 24px 0; }
  .gb-table-wrap table { margin: 0; min-width: 420px; }
  .gb-table-wrap td, .gb-table-wrap th { white-space: normal; }

  pre.gb-code { position: relative; }
  pre.gb-code[data-lang]::before { content: attr(data-lang); }

  /* 批注框：note=说明 / warning=注意 */
  .gb-callout { margin: 22px 0; padding: 14px 0 14px 18px; font-size: 0.92rem;
    border-top: 1px solid var(--hairline); border-bottom: 1px solid var(--hairline);
    border-left: 2px solid var(--green-800); }
  .gb-callout p, .gb-callout li { text-align: left; }
  .gb-callout > p:first-child::before {
    font-family: var(--font-sans); font-weight: 600; font-size: 0.78rem;
    letter-spacing: 0.1em; margin-right: 10px; }
  .gb-callout--info > p:first-child::before { content: "说明"; color: var(--green-700); }
  .gb-callout--tip > p:first-child::before { content: "技巧"; color: var(--green-700); }
  .gb-callout--warning > p:first-child::before { content: "注意"; color: var(--gold); }
  .gb-callout--danger > p:first-child::before { content: "重要"; color: var(--rust); }
  .gb-callout--warning { border-left-color: var(--gold); }
  .gb-callout--danger { border-left-color: var(--rust); }

  /* 步骤 */
  ol.gb-steps { list-style: none; margin: 18px 0 22px 0; padding: 0; counter-reset: step; }
  ol.gb-steps > li { position: relative; padding: 0 0 16px 40px; margin: 0;
    border-left: 1px solid var(--hairline); counter-increment: step; }
  ol.gb-steps > li:last-child { border-left-color: transparent; padding-bottom: 0; }
  ol.gb-steps > li::before {
    content: counter(step); position: absolute; left: -12px; top: 0;
    width: 24px; height: 24px; border-radius: 50%; background: var(--green-800);
    color: #f6f4ec; font-family: var(--font-sans); font-size: 0.72rem; font-weight: 700;
    display: flex; align-items: center; justify-content: center; }
  .gb-step-title { display: block; font-family: var(--font-sans); font-size: 0.9rem;
    font-weight: 700; color: var(--ink); margin-bottom: 4px; }

  /* 卡片 */
  .gb-card { padding: 16px 18px; border: 1px solid var(--hairline); margin: 14px 0;
    background: var(--paper-raised); }
  .gb-card__title { font-family: var(--font-sans); font-size: 0.92rem; font-weight: 700;
    color: var(--green-800); margin-bottom: 6px; }
  .gb-card__body { font-size: 0.86rem; color: var(--ink-soft); line-height: 1.75; }
  .gb-card__body p { font-size: 0.86rem; text-align: left; margin-bottom: 6px; }
  .gb-card__link { display: inline-block; margin-top: 8px; font-family: var(--font-sans);
    font-size: 0.74rem; letter-spacing: 0.08em; color: var(--green-700); text-decoration: none;
    border-bottom: 1px solid var(--green-200); }
  .card-grid .gb-card { margin: 0; border: none; border-right: 1px solid var(--hairline);
    border-bottom: 1px solid var(--hairline); }

  /* 折叠块 */
  details.gb-acc { margin: 16px 0; border-top: 1px solid var(--hairline);
    border-bottom: 1px solid var(--hairline); }
  details.gb-acc > summary { cursor: pointer; padding: 12px 0; font-weight: 700;
    font-size: 0.95rem; list-style: none; }
  details.gb-acc > summary::-webkit-details-marker { display: none; }
  details.gb-acc > summary::before { content: "＋　"; color: var(--green-700); font-family: var(--font-sans); }
  details.gb-acc[open] > summary::before { content: "－　"; }
  details.gb-acc > *:not(summary) { padding-left: 4px; }

  /* 选项卡（打印/阅读形态：平铺为带标签的段落块） */
  .gb-tabs { margin: 20px 0; border: 1px solid var(--hairline); }
  .gb-tabs__panel + .gb-tabs__panel { border-top: 1px solid var(--hairline); }
  .gb-tabs__label { font-family: var(--font-sans); font-size: 0.74rem; font-weight: 600;
    letter-spacing: 0.14em; color: var(--green-800); background: var(--green-100);
    padding: 7px 16px; border-bottom: 1px solid var(--hairline); }
  .gb-tabs__panel > *:not(.gb-tabs__label) { padding: 4px 16px 0; }
  .gb-tabs__panel > p:last-child { padding-bottom: 14px; }

  /* 章节内导航 */
  .chapter-toc { margin: 0 0 26px; padding: 14px 18px; background: var(--paper-raised);
    border: 1px solid var(--hairline); }
  .chapter-toc .ct-h { font-family: var(--font-sans); font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.18em; color: var(--green-800); margin-bottom: 8px; }
  .chapter-toc ol { margin: 0; padding-left: 20px; list-style: none; }
  .chapter-toc li { margin-bottom: 3px; font-size: 0.84rem; }
  .chapter-toc li.sub { padding-left: 16px; font-size: 0.8rem; color: var(--ink-soft); }
  .chapter-toc a { text-decoration: none; color: var(--ink-soft); }
  .chapter-toc a:hover { color: var(--green-700); }

  /* 原文出处 */
  .origin { margin-top: 34px; padding-top: 12px; border-top: 1px solid var(--hairline);
    font-family: var(--font-sans); font-size: 0.72rem; color: var(--ink-mute); letter-spacing: 0.04em; }
  .origin a { color: var(--ink-mute); }

  /* 更新日志：按 new/opt/fix 归类 */
  .cl-group { margin: 14px 0 4px; font-family: var(--font-sans); font-size: 0.72rem;
    font-weight: 600; letter-spacing: 0.16em; color: var(--ink-mute); }

  /* ========== 官方公众号补充文章 ========== */
  .wx-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px;
    margin: 0 0 26px; padding-bottom: 12px; border-bottom: 1px solid var(--hairline);
    font-family: var(--font-sans); font-size: 0.74rem; color: var(--ink-mute); }
  .wx-meta__src { font-weight: 600; letter-spacing: 0.06em; color: var(--green-800); }
  .wx-meta__src::before { content: "公众号 "; font-weight: 400; color: var(--ink-mute); }
  .wx-meta__date::before { content: "发布 "; color: var(--ink-mute); }
  .wx-meta__link { margin-left: auto; text-decoration: none; color: var(--ink-mute);
    border-bottom: 1px solid var(--hairline); padding-bottom: 1px; }
  .wx-meta__link:hover { color: var(--green-700); border-bottom-color: var(--green-700); }

  .wx-eyebrow { display: inline-block; font-family: var(--font-sans); font-size: 0.66rem;
    font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
    background: var(--green-800); color: #f6f4ec; padding: 4px 10px; margin: 0 0 18px; }

  .wx-cover { margin: 0 0 24px; }
  .wx-cover img { width: 100%; }

  .chapter h3.wx-sec { display: flex; align-items: baseline; gap: 12px;
    margin: 40px 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--hairline); }
  .wx-sec__num { font-family: var(--font-sans); font-size: 1.5rem; font-weight: 700;
    color: var(--green-800); line-height: 1; letter-spacing: -0.02em; }
  .chapter h4.wx-sub { margin: 28px 0 10px; font-size: 1rem; color: var(--ink); }
  .chapter h4.wx-sub::before { content: "▸ "; color: var(--green-700); }

  .wx-hint { font-family: var(--font-sans); font-size: 0.72rem; color: var(--ink-mute);
    letter-spacing: 0.08em; text-align: center; margin: 10px 0 20px; }
  .wx-divider { width: 56px; height: 1px; background: var(--hairline); margin: 34px auto; }

  figure.gb-fig img.wx-img { width: 100%; }

  /* ========== 公众号品牌：水印 + 关注卡片 ========== */
  #main { position: relative; z-index: 1; }
  .gzh-watermark { position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: __WM__; background-size: 460px 360px; }
  .follow-cta { display: flex; gap: 24px; align-items: center; justify-content: space-between;
    max-width: 780px; margin: 40px auto 8px; padding: 22px 26px;
    background: linear-gradient(135deg, #1E40AF, #0f2a6b); border-radius: 14px;
    color: #f6f4ec; box-shadow: 0 10px 30px rgba(30,64,175,.22); }
  .follow-cta .follow-title { font-family: var(--font-serif); font-size: 1.22rem; font-weight: 900; margin-bottom: 8px; }
  .follow-cta .follow-desc { font-family: var(--font-sans); font-size: .86rem; line-height: 1.7; opacity: .92; }
  .follow-cta .follow-actions { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 10px; }
  .follow-cta .follow-pill { font-family: var(--font-sans); font-size: .72rem; padding: 6px 12px;
    border: 1px solid rgba(246,244,236,.5); border-radius: 999px; }
  .follow-cta .gzh-qr { width: 120px; height: 120px; flex: 0 0 auto; border-radius: 10px;
    border: 2px solid rgba(246,244,236,.55); display: block; }
  .sidebar-gzh { font-family: var(--font-sans); font-size: .68rem; letter-spacing: .1em;
    color: rgba(246,244,236,.72); margin-top: 14px; padding-top: 12px;
    border-top: 1px solid rgba(246,244,236,.18); }
  .sidebar-gzh strong { color: #f6f4ec; }

  @media print {
    .gb-tabs, .gb-acc, .gb-card, .card-grid, .chapter-toc { break-inside: auto; }
    details.gb-acc { break-inside: avoid; }
    .gzh-watermark { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .follow-cta { break-inside: avoid; }
  }
"""
EXTRA_CSS = EXTRA_CSS.replace("__WM__", _wm_svg())

# ---------------------------------------------------------------- 目录结构
BOOK = [
    ("第一部分", "OVERVIEW", "认识千问办公：它是什么、能做什么", [
        ("product-introduction", "认识千问办公", "不止于对话，更注重交付"),
    ]),
    ("第二部分", "GETTING STARTED", "从零开始：选入口、装客户端、跑通第一个任务", [
        ("getting-started/usage-entry", "快速开始", "桌面端、网页端、钉钉内三种入口"),
        ("getting-started/basic-workflow", "网页端使用链路", "一句话交付成果的完整路径"),
        ("getting-started/desktop-workflow", "桌面端使用链路", "直连本地文件系统的工作方式"),
        ("getting-started/general-settings", "通用设置", "语言、主题与基础偏好"),
    ]),
    ("第三部分", "INSTALL & GET", "安装部署与订阅获取", [
        ("install/macos", "macOS 安装指南", "下载、授权与常见故障"),
        ("install/windows", "Windows 安装指南", "安装与环境依赖"),
        ("install/harmonyos", "HarmonyOS 安装指南", "鸿蒙设备安装说明"),
        ("getting-started/source-intro", "阿里云官网购买", "下单、开票与配额"),
        ("getting-started/privacy-security", "隐私与安全", "数据处理与权限边界"),
    ]),
    ("第四部分", "PLANS & BENEFITS", "个人版与企业版权益、套餐升降级规则", [
        ("benefits", "产品权益总览", "两类方案与适用场景"),
        ("benefits/personal", "个人版权益", "额度、功能与有效期"),
        ("benefits/plan-upgrade-downgrade", "套餐升降级策略", "生效时间、费用与权益变化"),
    ]),
    ("第五部分", "WEB", "网页端：免安装、云端跑、成果集中管理", [
        ("web", "网页端核心功能概览", "一站式办公体验的七项能力"),
        ("web/platform", "平台功能", "网页、网盘、扩展、定时任务、企业后台"),
        ("web/pages", "我的网页", "创建、编辑、发布与发布管控"),
        ("web/personal-drive", "个人网盘", "文件存储与任务调用"),
        ("web/scheduled-tasks", "网页端定时任务", "关闭浏览器也能执行"),
        ("features/extensions", "扩展：专家套件、技能与连接器", "能力扩展的三层结构"),
    ]),
    ("第六部分", "DESKTOP", "桌面端：本地文件、系统权限与自动化", [
        ("desktop", "桌面端核心功能概览", "面向日常办公的 AI 工作台"),
        ("desktop/settings", "系统设置", "通用、模型、权限与安全"),
        ("desktop/memory", "意识", "跨会话记忆与用户画像"),
        ("desktop/app-snapshots", "应用快照", "一键把屏幕内容带进对话"),
        ("desktop/computer-use", "电脑操控", "让 AI 直接操作你的电脑"),
        ("desktop/im-channels", "IM 频道", "接入即时通讯工具"),
        ("desktop/scheduled-tasks", "桌面端定时任务", "按项目组织与执行记录归档"),
        ("desktop/hooks", "Hooks", "在任务生命周期里插入自定义逻辑"),
        ("desktop/expert-kits", "专家套件", "面向岗位的能力组合"),
    ]),
    ("第七部分", "MODELS & EXTENSIONS", "模型选择、语音输入、技能与连接器", [
        ("features/model-selection", "网页端模型选择", "高级 / 基础 / 经济 / 前沿模型"),
        ("desktop/model-selection", "桌面端模型选择", "档位、折扣与自动刷新"),
        ("features/voice-input", "语音输入", "动口不动手的输入方式"),
        ("features/skills", "技能", "可复用的专业化工作流"),
        ("features/connectors", "连接器", "接入外部平台与数据"),
    ]),
    ("第八部分", "WORKSPACES", "三大工作台：设计、幻灯片、写作", [
        ("workspaces/design", "工作台 · 设计", "设计类任务的产出与规范"),
        ("workspaces/slides", "工作台 · 幻灯片", "PPT 生成与版式控制"),
        ("workspaces/writing", "工作台 · 写作", "长文、报告与文案"),
    ]),
    ("第九部分", "ENTERPRISE", "企业管理后台、单点登录与成员治理", [
        ("enterprise/admin", "企业管理后台", "组织、权限与资源总览"),
        ("enterprise/sso", "SSO 单点登录", "身份源对接与配置"),
        ("enterprise/credits", "积分管理", "额度分配与消耗监控"),
        ("enterprise/members", "成员管理", "邀请、角色与离职交接"),
    ]),
    ("第十部分", "ANNOUNCEMENTS", "官方上线公告与模型活动", [
        ("activity/qwen3.8-max-update", "千问办公正式上线", "多重惊喜福利"),
        ("docs/activity/glm-5.3-launch", "GLM-5.3 上线", "新星就位，抢先上手"),
        ("docs/activity/deepseek-v4-pro-member-unlimited", "DeepSeek V4 Pro 会员不限量", "限时畅用"),
    ]),
    ("第十一部分", "SUPPORT", "遇到问题时，怎么反馈、怎么提问、去哪查", [
        ("feedback", "问题反馈", "反馈渠道与处理流程"),
        ("feedback/how-to-ask", "提问指南", "让别人一眼看懂你的问题"),
        ("faq", "常见问题", "高频疑问速查"),
    ]),
]

APPENDIX = ("附录 A", "CHANGELOG", "客户端更新日志", [("release-notes/desktop", "客户端更新日志", "1.0.0 → 1.0.2 全量记录")])

CN_NUM = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]


def cn(n: int) -> str:
    return CN_NUM[n] if n < len(CN_NUM) else str(n)


def slug_id(slug: str) -> str:
    return "doc-" + slug.replace("/", "-")


def esc(s: str) -> str:
    return html_mod.escape(s, quote=False)


# ---------------------------------------------------------------- 章节内容加工
HEAD_SHIFT = {"h2": "h3", "h3": "h4", "h4": "h5", "h5": "h6"}


def downshift_headings(soup: BeautifulSoup):
    """正文标题整体降一级：章节标题占用 h2，正文从 h3 起"""
    heads = [h for h in soup.find_all(["h2", "h3", "h4", "h5"])]
    for h in heads:
        old = h.name
        h.name = HEAD_SHIFT[old]
        if h.get("class"):
            del h["class"]


def build_chapter_toc(soup: BeautifulSoup, prefix: str):
    """给 h2/h3 编号并生成章内导航"""
    heads = soup.find_all(["h2", "h3"])
    if not heads:
        return ""
    items = []
    for i, h in enumerate(heads, 1):
        hid = f"{prefix}-s{i}"
        h["id"] = hid
        text = h.get_text(strip=True)
        if not text:
            continue
        items.append((h.name, text, hid))
    if len(items) < 3:
        for h in heads:
            if h.get("id", "").startswith(prefix + "-s"):
                del h["id"]
        return ""
    lis = []
    for lvl, text, hid in items:
        cls = "sub" if lvl == "h3" else ""
        lis.append(f'<li class="{cls}"><a href="#{hid}">{esc(text)}</a></li>')
    return ('<div class="chapter-toc"><div class="ct-h">本章导航</div>'
            f'<ol>{"".join(lis)}</ol></div>')


CLS_MAP = [
    (("产品功能更新", "新功能", "功能更新", "新增"), "new"),
    (("体验优化", "优化", "改进"), "opt"),
    (("问题修复", "修复", "Bug"), "fix"),
]


def classify(text: str) -> str:
    for keys, cls in CLS_MAP:
        for k in keys:
            if k in text:
                return cls
    return "new"


def render_release_notes(page: dict) -> str:
    out = []
    for v in page["content"]:
        soup = BeautifulSoup(v["html"], "lxml")
        node = soup.select_one(".adoc-mdx-content") or soup.body or soup
        chunks = []
        cur_title, cur_items = None, []
        for child in list(node.children):
            if getattr(child, "name", None) is None:
                continue
            if child.name == "p" and child.find("strong"):
                if cur_items:
                    chunks.append((cur_title, cur_items))
                cur_title = child.get_text(strip=True)
                cur_items = []
            elif child.name in ("ul", "ol"):
                for li in child.find_all("li", recursive=False):
                    cur_items.append(li.decode_contents().strip())
            elif child.name == "p" and child.get_text(strip=True):
                cur_items.append(child.decode_contents().strip())
        if cur_items:
            chunks.append((cur_title, cur_items))
        body = []
        for title, items in chunks:
            cls = classify(title or "")
            body.append(f'<div class="cl-group">{esc(title or "更新")}</div>')
            for it in items:
                body.append(f'<div class="cl-tag {cls}">{it}</div>')
        out.append(
            f'<div class="cl-item"><div class="cl-head">'
            f'<span class="cl-ver">{esc(v["version"])}</span>'
            f'<span class="cl-date">{esc(v["date"])}</span></div>'
            f'{"".join(body)}</div>')
    return '<div class="changelog">' + "".join(out) + "</div>"


def render_wx_article(a: dict) -> str:
    """渲染一篇公众号文章：头图 + 来源信息条 + 正文。"""
    head = ""
    if a.get("cover_local"):
        head = (f'<figure class="gb-fig wx-cover">'
                f'<img class="wx-img" src="{esc(a["cover_local"])}" alt=""></figure>')
    meta = (
        f'<div class="wx-meta">'
        f'<span class="wx-meta__src">{esc(a.get("author") or "千问办公")}</span>'
        f'<span class="wx-meta__date">{esc(a.get("published", ""))}</span>'
        f'<a class="wx-meta__link" href="{esc(a["url"])}" target="_blank" '
        f'rel="noopener">在微信中查看原文 ↗</a>'
        f'</div>')
    return head + meta + a["content"]


def inline_local_images(doc: str) -> str:
    """把 wx_assets/ 下的图片内联成 base64，保住「单文件网页书」的特性。"""
    def repl(m):
        p = ROOT / m.group(1)
        if not p.exists():
            return m.group(0)
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return 'src="data:image/jpeg;base64,%s"' % b64

    return re.sub(r'src="(wx_assets/[^"]+)"', repl, doc)


# ---------------------------------------------------------------- 组装
def main():
    pages = json.loads((ROOT / "clean.json").read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in pages}

    # 公众号文章并入索引，标记为 kind="wx"
    wx_chaps = []
    for a in WX_ARTICLES:
        by_slug[a["slug"]] = dict(a, kind="wx")
        sub = a.get("desc") or ""
        wx_chaps.append((a["slug"], a["title"],
                         f'{a["published"]} · {sub[:26]}'.strip(" ·")))

    parts = list(BOOK) + [APPENDIX]
    n_parts = len(BOOK)
    if wx_chaps:
        # 插在「帮助与支持」之前，原本的支持部分顺延为第十二部分
        parts.insert(len(BOOK) - 1,
                     ("第十一部分", "OFFICIAL CASES",
                      "官方公众号发布的实践案例与产品动态", wx_chaps))
        sup = parts[len(BOOK)]
        parts[len(BOOK)] = ("第十二部分", sup[1], sup[2], sup[3])
        n_parts = len(BOOK) + 1
    used = set()
    chapters_html, toc_html = [], []
    idx = 0
    total_chars = 0

    for pi, (part_cn, part_en, part_desc, chaps) in enumerate(parts):
        short = part_desc.split("：")[0]
        toc_html.append(f'<div class="toc-part">▎{esc(part_cn)} · {esc(short)}</div>')
        chapters_html.append(
            f'<div class="part-break" data-part="{esc(part_cn)}　{esc(part_en)}"></div>')
        for slug, ctitle, csub in chaps:
            idx += 1
            page = by_slug.get(slug)
            if page is None:
                print("  !! MISSING", slug)
                continue
            used.add(slug)
            sid = "ch-%02d" % idx
            anchor = slug_id(slug)
            part_label = (f"第{cn(pi + 1)}部分" if part_cn != "附录 A"
                          else "附录 A")
            toc_html.append(
                f'<div class="toc-item"><a href="#{anchor}">'
                f'<span class="toc-num">{idx:02d}</span>{esc(ctitle)}</a></div>')

            if page["kind"] == "release-notes":
                content = render_release_notes(page)
                toc = ""
            elif page["kind"] == "wx":
                content = render_wx_article(page)
                toc = ""
            else:
                soup = BeautifulSoup(page["content"], "lxml")
                node = soup.select_one(".adoc-mdx-content")
                body = node.decode_contents() if node else page["content"]
                soup2 = BeautifulSoup(f"<div id=root>{body}</div>", "lxml")
                toc = build_chapter_toc(soup2, sid)
                downshift_headings(soup2)
                content = soup2.select_one("#root").decode_contents()

            total_chars += len(re.sub(r"<[^>]+>", "", content))
            src = page["url"]
            if page["kind"] == "wx":
                origin = ""  # 出处已经显示在文章顶部的信息条里
            else:
                origin = (f'<p class="origin">原文出处：<a href="{esc(src)}" target="_blank" '
                          f'rel="noopener">{esc(src)}</a></p>')

            chapters_html.append(f"""
<section class="chapter" id="{anchor}">
  <div class="chapter-header">
    <div class="chapter-num">{part_label} · 第 {idx:02d} 章</div>
    <h2 class="chapter-title">{esc(ctitle)}</h2>
    <div class="chapter-subtitle">{esc(csub)}</div>
  </div>
  {toc}
  {content}
  {origin}
</section>""")

    missing = [s for s in by_slug if s not in used]
    print("未编入章节的页面:", missing)

    # ---- 侧边栏 ----
    toc = "\n".join(toc_html)
    meta_chapters = idx
    meta_pages = max(1, round(total_chars / 900))
    meta_imgs = sum(
        (p["content"] if isinstance(p["content"], str)
         else "".join(v["html"] for v in p["content"])).count("gb-fig")
        for p in pages)
    meta_imgs += sum(a["content"].count("<img") + (1 if a.get("cover_local") else 0)
                     for a in WX_ARTICLES)

    structure_rows = []
    for part_cn, part_en, part_desc, chaps in parts:
        names = "、".join(c[1] for c in chaps)
        structure_rows.append(
            f"<tr><td><strong>{esc(part_cn)}</strong>　{esc(part_en)}</td>"
            f"<td>{esc(names)}</td></tr>")

    cover = f"""
<section class="cover" id="cover">
  <div class="cover-content">
    <div class="badge">ALIBABA QWENWORK · 官方文档整理 · 千问办公出品</div>
    <h1>千问办公 <span class="green">绿皮书</span></h1>
    <div class="tagline">不止于对话，更注重交付 · 一站式 AI 办公平台完全指南</div>
    <p class="desc">
      一本覆盖产品简介、快速上手、安装部署、权益订阅、网页端与桌面端核心能力、企业管理、官方公告与实战案例的千问办公完全手册。<br>
      内容完整整理自千问办公官方知识库（qwenwork.cn/docs）、官方更新日志站（docs.qwenwork.cn）
      与官方公众号「千问办公」的公开文章，
      含 {meta_chapters} 章正文、{meta_imgs} 张官方界面插图、全部客户端更新日志，结构与原文一致、可逐章对照查阅。<br>
      无论你是刚注册的新用户，还是想把 Agent 用进日常流程的老用户，都能在这里找到答案。
    </p>
    <div class="meta">
      <span><strong>{meta_chapters}</strong>章节</span>
      <span><strong>{meta_pages}</strong>页篇幅</span>
      <span><strong>{meta_imgs}</strong>官方插图</span>
    </div>
  </div>
  <div class="scroll-hint">向下滚动开始阅读</div>
</section>
"""

    copyright_page = """
<section class="chapter copyright" id="copyright">
  <div class="copyright-inner">
    <h2 class="copyright-title">千问办公绿皮书</h2>
    <p class="copyright-sub">不止于对话，更注重交付 · 官方文档完全整理版</p>
    <div class="copyright-block">
      <p><strong>内容来源</strong>　千问办公官方知识库（qwenwork.cn/docs）、官方更新日志站（docs.qwenwork.cn）、官方公众号「千问办公」</p>
      <p><strong>版本</strong>　v1.0 · 2026 年 9 月</p>
      <p><strong>篇幅</strong>　%d 大部分 · 1 附录 · %d 章 · 约 %d 页（网页版）</p>
      <p><strong>整理方式</strong>　官方文档结构化重排，保留原文表述、截图与操作步骤，未作主观增删</p>
    </div>
    <div class="copyright-block">
      <p class="cb-h">关于本书</p>
      <p>千问办公的功能迭代很快，官方文档也在持续更新。本书把分散在官方知识库、更新日志站与官方公众号上的 %d 篇内容，
      按「认识产品 → 上手使用 → 安装获取 → 权益订阅 → 网页端 → 桌面端 → 通用扩展 → 工作台 → 企业管理 → 官方公告 → 实践案例 → 帮助支持」的顺序重新编排，
      让你可以像读一本书那样，从头到尾系统掌握这款产品。</p>
      <p>官方文档章节末尾标注了<strong>原文出处链接</strong>，公众号文章在开头标注了发布日期与原文地址，
      如需核对官方最新表述，点击即可跳转。界面截图直接取自官方图床与官方推文，与官方发布保持一致。</p>
    </div>
    <div class="copyright-block">
      <p class="cb-h">版权与免责声明</p>
      <p>本书为面向千问办公用户的学习型资料汇编，正文内容全部来自千问办公官方文档，
      由编者进行结构化整理与版式重排，<strong>未改变原意</strong>。</p>
      <p>千问办公及其相关名称、标识、界面与功能描述归阿里巴巴集团所有。本书与阿里巴巴集团无官方隶属关系，
      书中内容不构成任何承诺。产品功能、定价、权益<strong>以千问办公官网实时信息为准</strong>。</p>
      <p>未经书面许可，不得以任何形式将本书主体内容用于商业用途；个人学习、团队内部传阅不受限。</p>
    </div>
    <div class="copyright-block">
      <p class="cb-h">致谢</p>
      <p>感谢千问办公文档团队把产品写得足够清楚——这是一本能被整理出来的前提；
      也感谢每一位愿意把重复劳动交给 AI、认真摸索新工作方式的职场同行。</p>
  <p class="copyright-sign">—— GoodTime · 公众号「宁的 AI 小站」 · 千问办公绿皮书编写组</p>
    </div>
  </div>
</section>
""" % (n_parts, meta_chapters, meta_pages, meta_chapters)

    preface = """
<section class="chapter" id="pre">
  <div class="chapter-header">
    <div class="chapter-num">序章 · PREFACE</div>
    <h2 class="chapter-title">关于绿皮书与使用说明</h2>
    <div class="chapter-subtitle">写给第一次打开千问办公的人</div>
  </div>

  <p>千问办公是阿里巴巴推出的一站式 AI 办公平台。它和「聊天机器人」最大的区别在于：
  <strong>你说目标，它交付成果</strong>——数据分析、PPT、视频剪辑、网页搭建，直接给出能用的文件，而不是一段建议。</p>

  <p>这本<strong>绿皮书</strong>把千问办公官方知识库里的全部文档，按从入门到进阶的顺序重新编排，
  配上官方界面截图与逐章的原文出处链接，让你既能系统通读，也能随时当手册翻查。</p>

  <div class="card-grid">
    <div class="card"><h4>内容完整</h4><p>覆盖官方文档全部 47 个页面，两个站点（qwenwork.cn/docs 与 docs.qwenwork.cn）无遗漏</p></div>
    <div class="card"><h4>结构清晰</h4><p>按「认识 → 上手 → 安装 → 权益 → 网页端 → 桌面端 → 扩展 → 工作台 → 企业 → 公告 → 支持」编排</p></div>
    <div class="card"><h4>可核对</h4><p>每章末尾附原文链接，官方更新后可一键跳转比对</p></div>
    <div class="card"><h4>可打印</h4><p>按 A4 出书规范排版，点右上角按钮即可导出 PDF 存档</p></div>
  </div>

  <h3>全书结构</h3>
  <table>
    <thead><tr><th>部分</th><th>包含章节</th></tr></thead>
    <tbody>
      %s
    </tbody>
  </table>

  <div class="callout info">
    <div class="callout-title">阅读建议</div>
    <p><strong>新用户</strong>：从第一部分读起，先把「快速开始」里的三种入口搞明白，再按自己用的端（网页端 / 桌面端）挑对应章节精读。</p>
    <p><strong>管理员</strong>：重点看第三部分（权益订阅）与第八部分（企业管理），SSO、积分、成员治理都在这里。</p>
    <p><strong>想追新的人</strong>：第九部分官方公告与附录更新日志放在一起看，能看出产品迭代的节奏。</p>
  </div>

  <h3>术语约定</h3>
  <p>本书沿用官方文档的中文术语：<strong>任务</strong>指一次完整的 AI 执行过程；<strong>技能</strong>是可复用的专业化工作流；
  <strong>连接器</strong>负责接入外部平台与数据；<strong>专家套件</strong>是面向特定岗位的能力组合；
  <strong>工作台</strong>是按产出类型（设计 / 幻灯片 / 写作）划分的工作模式。若同一功能在网页端与桌面端表现不同，本书分章说明并标注端别。</p>

  %s
</section>
""" % ("\n".join(structure_rows), FOLLOW_CTA)

    footer = f"""
<div class="book-footer">
  千问办公绿皮书 · v1.0 · 2026 年 9 月整理<br>
  内容来源：qwenwork.cn/docs · docs.qwenwork.cn　|　共 {meta_chapters} 章 · 约 {meta_pages} 页<br>
  <span class="page-tag">产品功能与权益以千问办公官网实时信息为准</span>
</div>
"""

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>千问办公绿皮书 · 官方文档完全整理版</title>
<meta name="description" content="千问办公（QwenWork）官方文档完全整理版绿皮书：产品简介、快速上手、安装部署、产品权益、网页端与桌面端核心能力、企业管理、官方公告与更新日志，共 {meta_chapters} 章。">
<style>
{CSS}
{EXTRA_CSS}
</style>
</head>
<body>

<div class="gzh-watermark"></div>
<div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
<button id="sidebar-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">目录</button>
<div id="page-footer"></div>
<button class="print-btn noprint" onclick="window.print()">打印 / 导出 PDF</button>

<nav id="sidebar">
  <div class="sidebar-header">
    <h1>千问办公绿皮书</h1>
    <div class="subtitle">官方文档完全整理版</div>
    <div class="version">v1.0 · 2026.09 · {meta_chapters} 章 · {n_parts} 大部分 · 约 {meta_pages} 页</div>
    <div class="sidebar-gzh">公众号 · <strong>宁的AI小站</strong></div>
  </div>
  <div class="toc">
    <div class="toc-item"><a href="#cover"><span class="toc-num">00</span>封面</a></div>
    <div class="toc-item"><a href="#pre"><span class="toc-num">序</span>关于绿皮书与使用说明</a></div>
{toc}
  </div>
</nav>

<main id="main">
<div class="content-wrap">
{cover}
{copyright_page}
{preface}
{"".join(chapters_html)}
{footer}
{FOLLOW_CTA}
</div>
</main>

<script>
  const progressFill = document.getElementById('progressFill');
  window.addEventListener('scroll', () => {{
    const scrollTop = window.pageYOffset;
    const docHeight = document.body.scrollHeight - window.innerHeight;
    progressFill.style.width = (scrollTop / Math.max(docHeight,1)) * 100 + '%';
  }});
  const tocLinks = document.querySelectorAll('.toc-item a');
  const chapters = document.querySelectorAll('.chapter, .cover');
  function updateActiveTOC() {{
    let current = '';
    chapters.forEach(ch => {{
      if (window.pageYOffset >= ch.offsetTop - 100) current = ch.id;
    }});
    tocLinks.forEach(link => {{
      link.classList.remove('active');
      if (link.getAttribute('href') === '#' + current) link.classList.add('active');
    }});
  }}
  window.addEventListener('scroll', updateActiveTOC);
  tocLinks.forEach(link => link.addEventListener('click', () => {{
    if (window.innerWidth <= 900) document.getElementById('sidebar').classList.remove('open');
  }}));
  updateActiveTOC();
</script>
</body>
</html>
"""
    doc = inline_local_images(doc)

    out = ROOT.parent / "index.html"
    out.write_text(doc, encoding="utf-8")
    print("WROTE", out, "size(KB) =", round(out.stat().st_size / 1024))
    print("chapters:", meta_chapters, "| chars:", total_chars, "| imgs:", meta_imgs,
          "| wx:", len(WX_ARTICLES))


if __name__ == "__main__":
    main()
