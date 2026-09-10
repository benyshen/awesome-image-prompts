#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish_to_github.py — 把采集的提示词+图片/视频一键发布到 awesome-image-prompts GitHub 库。

流程：媒体入库(images/ videos/，图压缩 1280px q75，视频>95MB ffmpeg 压制)
     -> 追加 data/prompts.json -> 重生成 docs/gallery.md -> 更新 README 计数
     -> git commit -> 经 socks5 代理 push origin main。

提示词来源优先级：同名 .txt/.md 边车文件 > 表单文本框。
GUI:  直接运行（或双击 发布到GitHub.bat）
CLI:  python tools/publish_to_github.py --cli --files a.jpg b.mp4 \
          --prompt "..." --source "小红书号xxx" [--category auto] [--no-push] [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import json
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_JSON = REPO / "data" / "prompts.json"
GALLERY_MD = REPO / "docs" / "gallery.md"
README = REPO / "README.md"
IMAGES_DIR = REPO / "images"
VIDEOS_DIR = REPO / "videos"

PROXY = "socks5h://127.0.0.1:10808"
GIT = shutil.which("git") or "git"
MAX_SIDE, JPEG_Q, VID_LIMIT = 1280, 75, 95_000_000
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VID_EXT = {".mp4", ".mov", ".webm", ".m4v"}

# ---------- 分类（与 scripts/build_repo.py 保持同一套规则） ----------
CATS = {
    "ui":           ("🖥️", "界面与社媒截图"), "infographic":  ("📊", "信息图与知识可视化"),
    "poster":       ("📰", "海报与版式设计"), "product":      ("🛍️", "商品与电商视觉"),
    "brand":        ("🏷️", "品牌与标识设计"), "architecture": ("🏛️", "建筑与空间场景"),
    "photo":        ("📷", "摄影与写真人像"), "illustration": ("🎨", "插画与艺术风格"),
    "character":    ("🧍", "角色与人物设定"), "scene":        ("🎬", "场景与叙事分镜"),
    "history":      ("🏮", "国风与历史题材"), "document":     ("📚", "文档与出版物料"),
    "video":        ("🎞️", "创意视频案例"), "other":        ("🧪", "综合与创意实验"),
    }
CAT_ORDER = list(CATS)
DESCS = {
    "ui": "App / 网页 / 直播 / 社媒界面、UI 样机与截图", "infographic": "信息图、图谱、科普百科、地图与结构化图解",
    "poster": "活动海报、封面、字体排版与强版式视觉", "product": "商品主图、详情页、包装与广告创意",
    "brand": "Logo、VI、吉祥物与品牌触点", "architecture": "建筑渲染、室内空间、城市规划与鸟瞰",
    "photo": "人像写真、手机摄影、胶片与商业摄影质感", "illustration": "插画、绘画流派、材质实验与装饰艺术",
    "character": "角色设计、卡牌、3D 玩具与形象设定", "scene": "分镜、故事场景、漫画叙事与世界观",
    "history": "古风卷轴、历史人物、传统题材与诗词视觉", "document": "白皮书、手册、处方、证书与出版版式",
    "video": "图生视频 / 文生视频提示词（播放见线上站）", "other": "创意实验、混合任务与实用杂项",
}
RULES = [
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


def classify(title: str, prompt: str, media: str) -> str:
    if media == "video":
        return "video"
    for pat, cat in RULES:
        if re.search(pat, title or "", re.I):
            return cat
    p = (prompt or "")[:800]
    for pat, cat in RULES:
        if re.search(pat, p, re.I):
            return cat
    return "other"


# ---------- 媒体处理 ----------
def compress_image(src: Path, dest_stem: Path) -> str:
    from PIL import Image
    dst = dest_stem.with_suffix(".jpg")
    im = Image.open(src)
    fmt = (im.format or "").upper()
    w, h = im.size
    if fmt == "JPEG" and max(w, h) <= MAX_SIDE and src.stat().st_size <= 400_000:
        dst = dest_stem.with_suffix(src.suffix.lower() or ".jpg")
        shutil.copyfile(src, dst)
        return dst.name
    im = im.convert("RGB")
    if max(w, h) > MAX_SIDE:
        r = MAX_SIDE / max(w, h)
        im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    dst.write_bytes(buf.getvalue())
    return dst.name


def ffprobe_height(src: Path) -> int:
    try:
        out = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error",
                              "-select_streams", "v:0", "-show_entries", "stream=height",
                              "-of", "csv=p=0", str(src)], capture_output=True, text=True, timeout=30)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return 0


def ingest_video(src: Path, dest_stem: Path, log) -> str | None:
    dst = dest_stem.with_suffix(".mp4")
    if src.suffix.lower() != ".mp4":
        log("  非 mp4 视频，ffmpeg 转码…")
    else:
        shutil.copyfile(src, dst)
        return dst.name
    ff = shutil.which("ffmpeg") or r"D:\tool\ffmpeg-full_build\ffmpeg-full_build\bin\ffmpeg.exe"
    h = ffprobe_height(src)
    vf = f"scale=-2:'min(1080,ih)'" if (h == 0 or h > 1080) else "null"
    cmd = [ff, "-y", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "fast",
           "-crf", "28", "-c:a", "aac", "-b:a", "128k", str(dst)]
    log("  ffmpeg 压制中…")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        log("  ✗ 转码失败: " + (r.stderr or "")[-300:])
        return None
    return dst.name


def prepare_media(src: Path, cid: int, log) -> tuple[str | None, str | None]:
    """返回 (image_rel, video_rel)，全 None 表示处理失败。"""
    stem = f"case{cid}"
    if src.suffix.lower() in VID_EXT:
        dest_stem = VIDEOS_DIR / stem
        name = ingest_video(src, dest_stem, log)
        if not name:
            return None, None
        if dest_stem.with_suffix(".mp4").stat().st_size > 100_000_000:
            log("  ✗ 压制后仍超 100MB，GitHub 拒绝，已放弃该文件")
            dest_stem.with_suffix(".mp4").unlink(missing_ok=True)
            return None, None
        return None, f"videos/{name}"
    name = compress_image(src, IMAGES_DIR / stem)
    return f"images/{name}", None


# ---------- 仓库数据 ----------
def load_db() -> dict:
    j = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    return j


def save_db(j: dict):
    j["items"].sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99, x["id"]))
    j["count"] = len(j["items"])
    j["built_at"] = time.strftime("%Y-%m-%d %H:%M")
    DATA_JSON.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")


def render_gallery(items: list[dict]):
    by = {c: [x for x in items if x["category"] == c] for c in CAT_ORDER}
    L = ["# 🖼️ 案例全库 · Full Gallery", "",
         f"共 **{len(items)}** 个公开案例，按场景分类。图片已压缩至 1280px 长边；"
         "视频案例存于 `videos/`，可在 GitHub Pages 画廊页直接播放。", "", "## 目录", ""]
    for c in CAT_ORDER:
        e, n = CATS[c]
        L.append(f"- [{e} {n}](#cat-{c})（{len(by[c])} 例）— {DESCS[c]}")
    L.append("")
    for c in CAT_ORDER:
        if not by[c]:
            continue
        e, n = CATS[c]
        L += [f'<a id="cat-{c}"></a>', "", f"## {e} {n}", f"_{DESCS[c]}_（{len(by[c])} 例）", ""]
        for it in sorted(by[c], key=lambda x: (-x["id"],)):
            L += [f'<a id="case-{it["id"]}"></a>', "",
                  f"### 例{it['id']}：{it['title']}", "",
                  f"*{it.get('created_at') or ''}*", ""]
            if it.get("image"):
                L += [f"![例{it['id']}]({it['image']})", ""]
            elif it.get("video"):
                L += [f"> 🎞️ 视频案例（Pages 版可在画廊页播放；仓库文件：`{it['video']}`）", ""]
            elif it.get("media_type") == "video":
                L += ["> 🎞️ 视频案例（文件较大未入库）", ""]
            L += ["```text", it.get("prompt") or "（未提供提示词）", "```",
                  f"来源：{it.get('source') or '未提供'}", ""]
    GALLERY_MD.write_text("\n".join(L), encoding="utf-8")


def update_readme(n: int):
    try:
        t = README.read_text(encoding="utf-8")
        t = re.sub(r"(/badge/Cases-)\d+", rf"\g<1>{n}", t)
        t = re.sub(r"收录 \*\*\d+\*\* 个社区公开案例", f"收录 **{n}** 个社区公开案例", t)
        README.write_text(t, encoding="utf-8")
    except Exception:
        pass


def auto_title(prompt: str, fallback: str) -> str:
    for line in (prompt or "").splitlines():
        line = line.strip().strip("#").strip()
        if len(line) >= 4 and line.lower() not in ("prompt", "prompts", "提示词", "标题", "title", "prompt："):
            return line[:30] + ("…" if len(line) > 30 else "")
    return fallback[:30]


# ---------- git ----------
def git(*args, proxy=False):
    cmd = [GIT]
    if proxy:
        cmd += ["-c", f"http.proxy={PROXY}", "-c", f"https.proxy={PROXY}"]
    cmd += list(args)
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r


def commit_and_push(paths: list[str], msg: str, log) -> bool:
    git("add", "--", *paths)
    st = git("status", "--porcelain")
    if not st.stdout.strip():
        log("git: 无变更，跳过提交")
        return True
    r = git("commit", "-m", msg)
    if r.returncode != 0:
        log("git commit 失败: " + (r.stderr or r.stdout)[-300:])
        return False
    log("已提交: " + msg)
    for attempt in range(1, 4):
        p = git("push", "origin", "HEAD:refs/heads/main", proxy=True)
        if p.returncode == 0:
            log(f"✓ 已推送到 GitHub (try {attempt})")
            return True
        log(f"push try{attempt} 失败: " + (p.stderr or p.stdout)[-200:].replace("\n", " "))
        time.sleep(3)
    p = git("push", "origin", "HEAD:refs/heads/main")  # 直连兜底
    if p.returncode == 0:
        log("✓ 已推送（直连）")
        return True
    log("✗ 推送失败，本地提交已保留——下次发布或手动 git push 会一并上传")
    return False


# ---------- 核心发布 ----------
def publish(files: list[Path], prompt_text: str, title: str, source: str,
            category: str, log, push=True, dry=False) -> list[int]:
    j = load_db()
    next_id = max(x["id"] for x in j["items"]) + 1
    touched, added = [], []
    for f in files:
        cid = next_id + len(added)
        log(f"[例{cid}] {f.name}")
        if f.suffix.lower() not in IMG_EXT | VID_EXT:
            log("  跳过：不是图片/视频")
            continue
        sidecar = None
        for ext in (".txt", ".md"):
            if f.with_suffix(ext).exists():
                sidecar = f.with_suffix(ext)
                break
        if sidecar:
            prompt = sidecar.read_text(encoding="utf-8", errors="replace").strip()
            log(f"  提示词取自边车 {sidecar.name}（{len(prompt)} 字）")
        else:
            prompt = (prompt_text or "").strip()
        media = "video" if f.suffix.lower() in VID_EXT else "image"
        t = title.strip() if len(files) == 1 else ""
        title_final = t or auto_title(prompt, f.stem)
        cat = classify(title_final, prompt, media) if category == "auto" else category
        if dry:
            img_rel = f"images/case{cid}.jpg" if media == "image" else None
            vid_rel = None if media == "image" else f"videos/case{cid}.mp4"
        else:
            img_rel, vid_rel = prepare_media(f, cid, log)
            if not img_rel and not vid_rel:
                continue
        entry = {
            "id": cid, "title": title_final, "prompt": prompt,
            "image": img_rel, "media_type": media, "source": source.strip() or "未提供",
            "orig_category": "GitHub投稿", "category": cat,
            "created_at": time.strftime("%Y-%m-%d"),
            "live_url": "http://192.168.28.100:8600/",
        }
        if vid_rel:
            entry["video"] = vid_rel
        j["items"].append(entry)
        added.append(cid)
        touched += [p for p in (img_rel, vid_rel) if p]
    if not added:
        log("没有可入库的文件")
        return []
    if dry:
        log("[dry-run] 不写库不提交。将新增: " + ", ".join(f"例{i}" for i in added))
        return added
    save_db(j)
    render_gallery(j["items"])
    update_readme(len(j["items"]))
    touched += ["data/prompts.json", "docs/gallery.md", "README.md"]
    msg = f"feat: add case{'s' if len(added) > 1 else ''} {', '.join(map(str, added))} — {added and title or ''}"
    msg = msg.rstrip(" —") or f"feat: add {len(added)} case(s)"
    if push:
        commit_and_push(touched, msg[:120], log)
    else:
        log("（--no-push）本地已写入，未提交：" + msg)
    log(f"完成：新增 {len(added)} 例 -> https://benyshen.github.io/awesome-image-prompts/")
    return added


# ---------- GUI ----------
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, scrolledtext, ttk

    root = tk.Tk()
    root.title("集市提示词 → GitHub 发布器")
    root.geometry("820x700")
    BG, CARD, TX, MUT, AC = "#12141b", "#1b1f2a", "#e8ebf1", "#8b94a7", "#5eead4"
    root.configure(bg=BG)

    files: list[Path] = []
    q: queue.Queue[str] = queue.Queue()

    lb = tk.Listbox(root, bg=CARD, fg=TX, selectbackground=AC, relief="flat", height=9,
                    font=("Microsoft YaHei UI", 10))
    lb.pack(fill="x", padx=14, pady=(12, 4))

    def refresh():
        lb.delete(0, "end")
        for f in files:
            lb.insert("end", f"  {f.name}  ·  {f.suffix[1:].upper()}  ·  {round(f.stat().st_size/1024)}KB")

    def add_files():
        exts = sorted(IMG_EXT | VID_EXT)
        got = filedialog.askopenfilenames(title="选择图片/视频",
                                          filetypes=[("媒体", " ".join("*" + e for e in exts)), ("所有", "*.*")])
        for g in got:
            p = Path(g)
            if p not in files:
                files.append(p)
        refresh()

    def add_folder():
        d = filedialog.askdirectory(title="选择包含媒体的文件夹")
        if not d:
            return
        for p in sorted(Path(d).iterdir()):
            if p.suffix.lower() in IMG_EXT | VID_EXT and p not in files:
                files.append(p)
        refresh()

    def remove_sel():
        for i in sorted(lb.curselection(), reverse=True):
            files.pop(i)
        refresh()

    bar = tk.Frame(root, bg=BG); bar.pack(fill="x", padx=14)
    for label, fn in [("＋ 添加文件", add_files), ("📁 添加文件夹", add_folder), ("－ 移除选中", remove_sel)]:
        tk.Button(bar, text=label, command=fn, bg=CARD, fg=TX, activebackground=AC,
                  relief="flat", padx=10, pady=4, font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(0, 8))

    form = tk.Frame(root, bg=BG); form.pack(fill="x", padx=14, pady=(10, 0))
    tk.Label(form, text="标题(多文件留空=自动)", bg=BG, fg=MUT, font=("Microsoft YaHei UI", 9)).grid(row=0, column=0, sticky="w")
    e_title = tk.Entry(form, bg=CARD, fg=TX, insertbackground=TX, relief="flat", width=30)
    e_title.grid(row=0, column=1, padx=6, sticky="we")
    tk.Label(form, text="来源", bg=BG, fg=MUT, font=("Microsoft YaHei UI", 9)).grid(row=0, column=2, sticky="w")
    e_src = tk.Entry(form, bg=CARD, fg=TX, insertbackground=TX, relief="flat", width=26)
    e_src.grid(row=0, column=3, padx=6, sticky="we")
    tk.Label(form, text="分类", bg=BG, fg=MUT, font=("Microsoft YaHei UI", 9)).grid(row=0, column=4, sticky="w")
    cb = ttk.Combobox(form, values=["auto"] + [f"{CATS[k][0]}{v}" for k, v in
                     [(k, CATS[k][1]) for k in CAT_ORDER]], state="readonly", width=20)
    cb.current(0); cb.grid(row=0, column=5, padx=6)
    form.columnconfigure(1, weight=1); form.columnconfigure(3, weight=1)

    tk.Label(root, text="提示词（留空则读取每个媒体的同名 .txt/.md）", bg=BG, fg=MUT,
             font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=14, pady=(10, 2))
    t_prompt = scrolledtext.ScrolledText(root, bg=CARD, fg=TX, insertbackground=TX, relief="flat",
                                         height=6, font=("Microsoft YaHei UI", 10))
    t_prompt.pack(fill="x", padx=14)

    go = tk.Button(root, text="🚀 发布上传（写入仓库 + 推送 GitHub）", command=lambda: start(False),
                   bg=AC, fg="#0b0d12", font=("Microsoft YaHei UI", 12, "bold"), relief="flat", padx=16, pady=8)
    go.pack(pady=12)
    dryb = tk.Button(root, text="干跑（只看计划，不写不推）", command=lambda: start(True),
                     bg=CARD, fg=MUT, relief="flat", padx=10, pady=2)
    dryb.pack(pady=(0, 6))

    logbox = scrolledtext.ScrolledText(root, bg="#0b0d12", fg="#9fe8d8", relief="flat", height=11,
                                       font=("Consolas", 9), state="disabled")
    logbox.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def dolog(s):
        q.put(s)

    def pump():
        try:
            while True:
                s = q.get_nowait()
                logbox.configure(state="normal")
                logbox.insert("end", s + "\n")
                logbox.see("end")
                logbox.configure(state="disabled")
        except queue.Empty:
            pass
        root.after(120, pump)

    def start(dry):
        if not files and not dry:
            dolog("请先添加媒体文件")
            return
        go.configure(state="disabled")

        def work():
            try:
                cat = CAT_ORDER[cb.current() - 1] if cb.current() > 0 else "auto"
                publish(list(files), t_prompt.get("1.0", "end"), e_title.get(),
                        e_src.get(), cat, dolog, push=not dry, dry=dry)
                if not dry:
                    dolog("— 队列中的文件已处理，可清空继续下一批 —")
                    files.clear(); root.after(0, refresh)
            except Exception as ex:
                import traceback
                dolog("✗ 异常: " + str(ex) + "\n" + traceback.format_exc()[-600:])
            finally:
                root.after(0, lambda: go.configure(state="normal"))

        threading.Thread(target=work, daemon=True).start()

    pump()
    root.mainloop()


# ---------- main ----------
def _fix_console():
    # pythonw.exe has no console; force UTF-8 for any stray stderr writes
    # so GBK codepage never crashes the process on Chinese output.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="发布提示词案例到 GitHub 库")
    ap.add_argument("--cli", action="store_true", help="无界面模式")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--prompt", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--category", default="auto")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.cli:
        run_gui()
        return
    log = print
    added = publish([Path(f) for f in a.files], a.prompt, a.title, a.source,
                    a.category, log, push=not a.no_push, dry=a.dry_run)
    sys.exit(0 if added else 1)


if __name__ == "__main__":
    _fix_console()
    main()
