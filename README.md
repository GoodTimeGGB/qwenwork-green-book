# 千问办公绿皮书

把「千问办公」两个官方知识库的全部内容，重排成一本可以直接读、可以打印成书的单文件网页书。

- **落地页 / 跳转入口**：[wangjn.site/tools/qianwen.html](https://wangjn.site/tools/qianwen.html)
- **本地打开**：双击 `index.html`，无需服务器、无外部依赖

## 这本书是什么

内容 100% 来自官方公开文档，按「认识产品 → 上手使用 → 安装获取 → 权益订阅 → 网页端 → 桌面端 → 通用扩展 → 工作台 → 企业管理 → 官方公告 → 帮助支持」的顺序重新编排，共 **11 大部分 + 1 附录、48 章（47 篇官方文档）**，保留 **122 张官方界面截图、96 张表格、75 个代码块**。

| 部分 | 主题 | 覆盖内容 |
| --- | --- | --- |
| 第一部分 | 认识千问办公 | 产品定位、核心能力 |
| 第二部分 | 从零开始 | 入口选择、基础工作流 |
| 第三部分 | 安装部署与订阅获取 | 客户端下载、安装、订阅 |
| 第四部分 | 权益与套餐 | 个人版/企业版权益、升降级规则 |
| 第五部分 | 网页端 | 网盘、个人空间 |
| 第六部分 | 桌面端 | 界面、设置、快照、Hooks |
| 第七部分 | 模型与扩展 | 模型选择、语音输入、技能、连接器 |
| 第八部分 | 工作台 | 三大工作台 |
| 第九部分 | 企业管理 | 管理后台、SSO、成员治理 |
| 第十部分 | 官方公告 | 上线公告与模型活动 |
| 第十一部分 | 帮助与支持 | 反馈渠道、提问方法 |
| 附录 A | 客户端更新日志 | 1.0.0 → 1.0.2 全量 changelog |

## 数据来源

| 来源 | 说明 |
| --- | --- |
| `https://qwenwork.cn/docs` | 产品文档主站 |
| `https://docs.qwenwork.cn` | 更新日志与补充文档 |

抓取入口是两站的 `/llms.txt` 全文索引，逐页取 SSR HTML 后做结构化解析。**内容版权归原作者（千问办公官方）所有**，本项目只做格式重排与归档，不做任何内容改写。

## 目录结构

```
.
├── index.html            # 绿皮书成品（单文件，可直接打开/部署）
├── 千问办公绿皮书.html    # 同上，中文名副本
├── tools/
│   └── qianwen.html      # wangjn.site 上的落地页（导览 + 跳转）
└── pipeline/             # 抓取 → 清洗 → 构建 流水线
    ├── crawl.py          # ① 读 llms.txt 索引 → 缓存 HTML → pages.json
    ├── transform.py      # ② bs4 语义化组件转换 → clean.json
    ├── build.py          # ③ 套用书页版式 → ../index.html
    ├── shot.py           # ④ playwright 截图抽查
    ├── gb_style.css      # 参考站版式骨架备份
    ├── pages.json        # 抓取中间产物
    └── clean.json        # 清洗后内容数据
```

## 重新生成（官方文档更新后）

```bash
pip install beautifulsoup4 lxml playwright
playwright install chromium

cd pipeline
python crawl.py        # 抓取最新文档到 pipeline/raw/ 并生成 pages.json
python transform.py    # 清洗为 clean.json
python build.py        # 输出 ../index.html 与 ../千问办公绿皮书.html
python shot.py         # 可选：截图抽查渲染效果
```

`build.py` 里的 `BOOK` 常量控制章节编排顺序；`transform.py` 负责把官方渲染器的 callout / step / card / accordion / tab 组件转成书页版式对应的 `gb-*` 类。

## 页面特性

- 深绿侧边栏目录，点击跳转，移动端自动收起
- 每章带「本章导航」与**原文出处链接**
- `Ctrl/Cmd + P` 直接打印：已内置 A4 出书排版（页码、页眉、分页控制）

## 版式来源

书页版式（纸墨风、衬线书体、三线表、扉页分部）参考自 [workbuddy-green-book.wangjn.site](https://workbuddy-green-book.wangjn.site/)，感谢原作者的视觉设计。

## License

内容归千问办公官方所有。项目代码（抓取 / 清洗 / 构建脚本）采用 MIT License，见 [LICENSE](LICENSE)。
