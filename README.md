# 无限创意提示词库 · Awesome Image Prompts

[![Cases](https://img.shields.io/badge/Cases-673-blueviolet?style=flat-square)](docs/gallery.md)
[![Categories](https://img.shields.io/badge/Categories-14-green?style=flat-square)](#️-分类总览)
[![Online](https://img.shields.io/badge/在线浏览-GitHub_Pages-brightgreen?style=flat-square)](https://benyshen.github.io/awesome-image-prompts/)
[![License](https://img.shields.io/badge/License-CC--BY--NC--4.0-lightgrey?style=flat-square)](#免责声明)

> **Prompt as Code** ｜ AI 图像/视频提示词逆向工程案例库。收录 **673** 个社区公开案例（源自「条码帮·无限创意集市」），
> 每个案例保留 **配图/视频 + 完整提示词 + 来源出处**，并按 14 个场景重新分类，结构化 JSON 可直接供 Agent / 脚本复用。
> 组织方式学习 [awesome-gpt-image-2](https://github.com/freestylefly/awesome-gpt-image-2)（Prompt as Code 理念）。

**中文** ｜ [English](#english)

## 🌐 快速入口

- 🖼️ **[在线画廊（GitHub Pages）](https://benyshen.github.io/awesome-image-prompts/)** — 瀑布流浏览、关键词搜索、分类筛选、一键复制提示词
- 📖 **[案例全库 Markdown 版](docs/gallery.md)** — 按分类逐例展示，适合直接阅读 / Git 内检索
- 🧱 **[结构化数据 `data/prompts.json`](data/prompts.json)** — 全量案例：`id / title / prompt / image / category / source / media_type`，供程序与 Agent 调用
- ✍️ **[提示词写作模板与套路](docs/templates.md)** — 从 631 例中提炼的 8 类可复用写作框架
- 📮 投稿 / 勘误：在本仓库 [开 Issue](../../issues) 或直接 PR（条目格式见 `docs/CONTRIBUTING.md`）

## 🗂️ 分类总览

| 分类 | 数量 | 说明 |
|---|---|---|
| 📰 [海报与版式设计](docs/gallery.md#cat-poster) | 122 | 活动海报、封面、字体排版与强版式视觉 |
| 📷 [摄影与写真人像](docs/gallery.md#cat-photo) | 99 | 人像写真、CCD/胶片质感、手机与商业摄影 |
| 🖥️ [界面与社媒截图](docs/gallery.md#cat-ui) | 73 | App / 网页 / 直播 / 朋友圈与社媒界面、UI 样机截图 |
| 📊 [信息图与知识可视化](docs/gallery.md#cat-infographic) | 69 | 信息图、图谱、科普百科、地图与结构化图解 |
| 🎨 [插画与艺术风格](docs/gallery.md#cat-illustration) | 46 | 插画、绘画流派、材质实验与装饰艺术 |
| 🏛️ [建筑与空间场景](docs/gallery.md#cat-architecture) | 42 | 建筑渲染、室内空间、城市规划与鸟瞰 |
| 🧍 [角色与人物设定](docs/gallery.md#cat-character) | 31 | 角色设计、卡牌、手办与形象设定 |
| 🧪 [综合与创意实验](docs/gallery.md#cat-other) | 29 | 创意实验、混合任务与实用杂项 |
| 🎬 [场景与叙事分镜](docs/gallery.md#cat-scene) | 27 | 分镜、故事场景、漫画叙事与世界观 |
| 🎞️ [创意视频案例](docs/gallery.md#cat-video) | 27 | 图生视频 / 文生视频提示词（视频已入仓库 `videos/`，Pages 页可直接播放） |
| 🛍️ [商品与电商视觉](docs/gallery.md#cat-product) | 26 | 商品主图、详情页、包装与广告创意 |
| 🏷️ [品牌与标识设计](docs/gallery.md#cat-brand) | 19 | Logo、VI、吉祥物与品牌触点 |
| 🏮 [国风与历史题材](docs/gallery.md#cat-history) | 18 | 古风卷轴、历史人物、传统题材与诗词视觉 |
| 📚 [文档与出版物料](docs/gallery.md#cat-document) | 3 | 白皮书、手册、处方笺与出版版式 |

## ⚡️ 项目理念

散落在群聊和小红书里的优秀案例，只有被**拆解成结构化协议**后才可复用。本仓库把每个案例落成三件套：

1. **Result** — 生成结果图（压缩至 1280px，仓库自托管）
2. **Prompt** — 完整原始提示词（不删减，可整段复制）
3. **Schema** — `data/prompts.json` 中的结构化字段（分类 / 来源 / 媒介类型）

- 🧱 原子化分类：按**用途场景**而非画风切分，找模板先定场景
- ⚙️ 工作流友好：JSON 直接喂给 Agent、脚本与批量生成管线
- 🧬 可持续增量：`scripts/build_repo.py` 从集市数据库一键重建全库

## 🛠️ 维护脚本

```bash
# 从集市 SQLite（默认 Z:\web\promptmaster_web\data\gallery.db，可用 GALLERY_DB 覆盖）
# 重新生成 prompts.json / gallery.md 并压缩图片到 images/
python scripts/build_repo.py
```

## 📺 姊妹站

线下部署版（含视频播放、社区投稿、会员体系）：<http://192.168.28.100:8600/>（局域网）

## 免责声明

本仓库仅整理**公开可访问**的社区提示词与示例图用于学习研究，不主张对任何第三方原创内容的权利；条目均尽力保留原始出处（小红书号等）。内容不代表可商用，商用请先取得原作者授权。如您是权利人且认为某条目不应展示，请开 Issue 指明条目链接，我们会尽快核实移除。

---

## English

A **Prompt-as-Code** library of 631 reverse-engineered AI image/video prompt cases, re-organized into 14 use-case categories. Each case keeps its result image, full original prompt, and source credit; the whole gallery is available as structured JSON (`data/prompts.json`) for agents and automation, rendered as a static site on GitHub Pages, and browsable as Markdown (`docs/gallery.md`). Structure inspired by [awesome-gpt-image-2](https://github.com/freestylefly/awesome-gpt-image-2). Community content is organized for learning and research only — see the disclaimer for licensing notes.
