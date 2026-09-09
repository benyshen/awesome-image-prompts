# -*- coding: utf-8 -*-
"""
Build the awesome-image-prompts GitHub repo content from the live 无限创意集市
(gallery.db on NAS Z:\\web\\promptmaster_web, mirroring http://192.168.28.100:8600/).

Reads only visibility='public' rows. Outputs:
  data/prompts.json      - full structured dataset
  docs/gallery.md        - browsable markdown gallery by category
  images/*.jpg           - optimized case images (max 1280px, q75 progressive)
Run from repo root:  python scripts/build_repo.py
"""
import io
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DB = Path(os.environ.get("GALLERY_DB", r"Z:\web\promptmaster_web\data\gallery.db"))
SRC_IMG = Path(os.environ.get("GALLERY_IMG", r"Z:\web\promptmaster_web\static\images"))
MAX_SIDE = 1280
QUALITY = 75

CATS = {
    "ui":           ("🖥️", "界面与社媒截图", "App / 网页 / 直播 / 社媒界面、UI 样机与截图"),
    "infographic":  ("📊", "信息图与知识可视化", "信息图、图谱、科普百科、地图与结构化图解"),
    "poster":       ("📰", "海报与版式设计", "活动海报、封面、字体排版与强版式视觉"),
    "product":      ("🛍️", "商品与电商视觉", "商品主图、详情页、包装与广告创意"),
    "brand":        ("🏷️", "品牌与标识设计", "Logo、VI、吉祥物与品牌触点"),
    "architecture": ("🏛️", "建筑与空间场景", "建筑渲染、室内空间、城市规划与鸟瞰"),
    "photo":        ("📷", "摄影与写真人像", "人像写真、手机摄影、胶片与商业摄影质感"),
    "illustration": ("🎨", "插画与艺术风格", "插画、绘画流派、材质实验与装饰艺术"),
    "character":    ("🧍", "角色与人物设定", "角色设计、卡牌、3D 玩具与形象设定"),
    "scene":        ("🎬", "场景与叙事分镜", "分镜、故事场景、漫画叙事与世界观"),
    "history":      ("🏮", "国风与历史题材", "古风卷轴、历史人物、传统题材与诗词视觉"),
    "document":     ("📚", "文档与出版物料", "白皮书、手册、处方、证书与出版版式"),
    "video":        ("🎞️", "创意视频案例", "图生视频 / 文生视频提示词（播放见线上站）"),
    "other":        ("🧪", "综合与创意实验", "创意实验、混合任务与实用杂项"),
}
CAT_ORDER = ["ui", "infographic", "poster", "product", "brand", "architecture",
             "photo", "illustration", "character", "scene", "history", "document",
             "video", "other"]

TITLE_RULES = [
    (r"界面|样机|截图|直播|dashboard|\bapp\b|网站|网页|\bui\b|首页|主页|朋友圈|微博|推特|x的?内容|screenshot|interface", "ui"),
    (r"信息图|图谱|可视化|百科|科普|关系图|流程图|思维导图|图解|数据图|图表|地图|infographic|diagram|chart", "infographic"),
    (r"海报|封面|排版|版式|字体|字报|传单|明信片|日历|手举牌|书签|poster|typograph|flyer", "poster"),
    (r"商品|电商|包装|产品|详情图|主图|亚马逊|淘宝|带货|\bproduct\b|e-?commerce|packaging|amazon", "product"),
    (r"品牌|徽标|标志|\blogo\b|\bvi\b|吉祥物|门头|名片|brand|maskot|mascot", "brand"),
    (r"建筑|空间|室内|城市|街景|鸟瞰|渲染图|住宅|房屋|街区|architect|interior|\bcity\b|building", "architecture"),
    (r"摄影|写真|人像|\bccd\b|胶片|生活照|photoreal|portrait|photography|selfie|\bfilm\b|camera", "photo"),
    (r"插画|绘画|手绘|水彩|油画|动漫|像素|线稿|工笔|浮世绘|版画|涂鸦|艺术风|illustrat|\bwatercolor\b|sketch", "illustration"),
    (r"角色|卡牌|圣斗士|头像|手办|玩具|人设|少女|佳人|美少女|character|\bcard\b|figurine|manga", "character"),
    (r"分镜|漫画|叙事|场景|故事|电影感|世界观|废墟|太空|storyboard|cinematic|\bscene\b", "scene"),
    (r"古风|历史|大唐|李白|三国|玄武门|敦煌|宋代?|唐代?|明代?|清代?|杜甫|武则天|朱元璋|皇宫|御用|古建|国潮", "history"),
    (r"文档|白皮书|手册|说明书|药方|处方|证书|报告|试卷|合同|document|manual|certificate", "document"),
]
PROMPT_HINT = TITLE_RULES


def copy_video(fname: str, dst_dir: Path) -> str | None:
    """Copy a source .mp4 into videos/ if under the GitHub 100MB hard limit."""
    src = SRC_IMG / fname
    if not src.exists() or src.stat().st_size > 95_000_000:
        return None
    out = dst_dir / fname
    if not out.exists() or out.stat().st_size != src.stat().st_size:
        out.write_bytes(src.read_bytes())
    return f"videos/{fname}"


def classify(title: str, prompt: str, media: str) -> str:
    if media == "video":
        return "video"
    t = title or ""
    for pat, cat in TITLE_RULES:
        if re.search(pat, t, re.I):
            return cat
    p = (prompt or "")[:800]
    for pat, cat in PROMPT_HINT:
        if re.search(pat, p, re.I):
            return cat
    return "other"


def clean_source(s: str) -> str:
    if not s:
        return "未提供"
    return s.replace("\\_", "_").strip()


def nice_title(item):
    t = (item["title"] or "").strip()
    t = re.sub(r"^例\d+[:：]\s*", "", t)
    generic = re.fullmatch(r"(?i)(gpt[\s\-]*image[\s\-]*2?|gemini.*|nano\s*banana.*|sora.*|\s*)", t or "x")
    if not t or t in ("例",) or generic:
        seed = re.sub(r"\s+", " ", item["prompt"] or "").strip()
        t = seed[:30] + ("…" if len(seed) > 30 else "")
    return t


def optimize_image(fname: str, dst: Path) -> str | None:
    """Copy/convert one source file into an optimized JPEG. Returns new name."""
    src = SRC_IMG / fname
    if not src.exists():
        return None
    if fname.lower().endswith(".mp4"):
        return None  # videos handled by copy_video
    from PIL import Image
    im = Image.open(src)
    fmt = (im.format or "").upper()
    w, h = im.size
    need = fmt != "JPEG" or max(w, h) > MAX_SIDE or src.stat().st_size > 400_000
    if not need:
        dst.write_bytes(src.read_bytes())
        return fname
    im = im.convert("RGB")
    if max(w, h) > MAX_SIDE:
        r = MAX_SIDE / max(w, h)
        im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
    out = dst.with_suffix(".jpg")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    out.write_bytes(buf.getvalue())
    return out.name


def main():
    if not SRC_DB.exists():
        sys.exit(f"DB not found: {SRC_DB} (mount Z: or set GALLERY_DB)")
    cur = sqlite3.connect(f"file:{SRC_DB.as_posix()}?mode=ro", uri=True).cursor()
    rows = cur.execute(
        "select id,title,prompt,image,source,category,media_type from items "
        "where visibility='public' order by id").fetchall()

    (REPO / "data").mkdir(exist_ok=True)
    (REPO / "docs").mkdir(exist_ok=True)
    img_out = REPO / "images"
    img_out.mkdir(exist_ok=True)

    vid_out = REPO / "videos"
    vid_out.mkdir(exist_ok=True)
    items, copied, vids = [], 0, 0
    for (i, title, prompt, image, source, cat, media) in rows:
        it = {
            "id": i,
            "title": nice_title({"title": title, "prompt": prompt}),
            "prompt": (prompt or "").strip(),
            "image": image,
            "media_type": media,
            "source": clean_source(source),
            "orig_category": cat,
            "category": classify(title or "", prompt or "", media),
            "live_url": "http://192.168.28.100:8600/",
        }
        if image and media == "image":
            new = optimize_image(image, img_out / image)
            if new:
                it["image"] = f"images/{new}"
                copied += 1
            else:
                it["image"] = None
        else:
            it["image"] = None
            it["video"] = copy_video(image, vid_out) if image else None
            vids += 1
        items.append(it)

    items.sort(key=lambda x: (CAT_ORDER.index(x["category"]), x["id"]))
    json.dump({"count": len(items), "items": items},
              open(REPO / "data" / "prompts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ---- docs/gallery.md ----
    by = {c: [x for x in items if x["category"] == c] for c in CAT_ORDER}
    L = ["# 🖼️ 案例全库 · Full Gallery", "",
         f"共 **{len(items)}** 个公开案例，按场景分类。图片已压缩至 1280px 长边；"
         "视频案例请移步 [线上站](http://192.168.28.100:8600/) 播放。", "",
         "## 目录", ""]
    for c in CAT_ORDER:
        e, n, d = CATS[c]
        L.append(f"- [{e} {n}](#{'cat-' + c})（{len(by[c])} 例）— {d}")
    L.append("")
    for c in CAT_ORDER:
        if not by[c]:
            continue
        e, n, d = CATS[c]
        L += [f'<a id="cat-{c}"></a>', "", f"## {e} {n}", f"_{d}_（{len(by[c])} 例）", ""]
        for it in by[c]:
            L.append(f'<a id="case-{it["id"]}"></a>')
            L.append("")
            L.append(f"### 例{it['id']}：{it['title']}")
            L.append("")
            if it["image"]:
                L.append(f"![例{it['id']}]({it['image']})")
                L.append("")
            elif it.get("video"):
                L.append(f"> 🎞️ 视频案例（Pages 版可在画廊页播放；仓库文件：`{it['video']}`）")
                L.append("")
            elif it["media_type"] == "video":
                L.append(f"> 🎞️ 视频案例（文件较大未入库），[在线播放]({it['live_url']})")
                L.append("")
            body = it["prompt"] or "（未提供提示词）"
            L += ["```text", body, "```", "", f"来源：{it['source']}", ""]
    (REPO / "docs" / "gallery.md").write_text("\n".join(L), encoding="utf-8")

    print(f"items={len(items)} images_optimized={copied} videos={vids}")
    from collections import Counter
    print(Counter(x['category'] for x in items).most_common())


if __name__ == "__main__":
    main()
