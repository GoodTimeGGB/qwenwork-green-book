# -*- coding: utf-8 -*-
# 主题色：紫 → 千问官方绿（取样自千问章鱼吉祥物：主绿 #009039 / 亮绿 #42d87e / 深绿 #007c30）
import io

# ---------- gb_style.css ----------
p = "gb_style.css"
s = io.open(p, encoding="utf-8").read()
pairs = [
    # 纸墨色系带一点绿意
    ("--paper: #f7f5f0;", "--paper: #f5f8f4;"),
    ("--paper-raised: #fbfaf7;", "--paper-raised: #fafcf9;"),
    ("--ink: #26242e;", "--ink: #1d2a20;"),
    ("--ink-soft: #4b4858;", "--ink-soft: #44584b;"),
    ("--ink-mute: #7d7a8c;", "--ink-mute: #718578;"),
    ("--hairline: #dcd8e6;", "--hairline: #d2e4d5;"),
    # 品牌色阶：紫 → 千问绿
    ("--green-900: #2b2260;", "--green-900: #00481d;"),
    ("--green-800: #5246c8;", "--green-800: #00702c;"),
    ("--green-700: #615ced;", "--green-700: #009039;"),
    ("--green-600: #7a6bf0;", "--green-600: #35b263;"),
    ("--green-200: #dcd7f8;", "--green-200: #c4ecd2;"),
    ("--green-100: #f1effc;", "--green-100: #e9f7ee;"),
    # 侧边栏默认文字 / 高亮
    ("color: #d6d3f0;", "color: #c2e3cb;"),
    ("#b9acf8", "#42d87e"),
    # 关注卡片渐变
    ("linear-gradient(135deg,#615ced,#3b2e86)", "linear-gradient(135deg,#009039,#007c30)"),
    ("rgba(97,92,237,.28)", "rgba(0,144,57,.25)"),
]
for a, b in pairs:
    if a not in s:
        print("!! css 未找到:", a)
    s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("css recolored OK")

# ---------- build.py ----------
p2 = "build.py"
s2 = io.open(p2, encoding="utf-8").read()
pairs2 = [
    ("background: linear-gradient(135deg, #615ced, #3b2e86); border-radius: 14px;",
     "background: linear-gradient(135deg, #009039, #007c30); border-radius: 14px;"),
    ("color: #f6f4ec; box-shadow: 0 10px 30px rgba(97,92,237,.28); }",
     "color: #f5f8f4; box-shadow: 0 10px 30px rgba(0,144,57,.25); }"),
    ("fill='rgb(110,102,200)'", "fill='rgb(0,144,57)'"),   # 水印文字颜色
]
for a, b in pairs2:
    if a not in s2:
        print("!! build 未找到:", a[:60])
    s2 = s2.replace(a, b)
io.open(p2, "w", encoding="utf-8").write(s2)
print("build recolored OK")

# 残留检查
import re
for f, txt in (("gb_style.css", s), ("build.py", s2)):
    left = re.findall(r"(?:2b2260|5246c8|615ced|7a6bf0|dcd7f8|f1effc|b9acf8|d6d3f0|3b2e86|110,102,200|97,92,237)", txt)
    if left:
        print("残留:", f, set(left))
    else:
        print("无残留:", f)
