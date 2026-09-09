# 贡献指南 · Contributing

欢迎补充新案例、修正分类与出处。

## 条目格式

每个案例在 `data/prompts.json` 中是一个对象：

```json
{
  "id": 656,
  "title": "例656：城市生命系统图谱",
  "prompt": "完整原始提示词，不删减",
  "image": "images/case656.jpg",
  "media_type": "image",
  "source": "小红书号xxxxxxx",
  "orig_category": "魔法画廊",
  "category": "infographic",
  "live_url": "http://192.168.28.100:8600/#item-656"
}
```

`category` 取值：`ui / infographic / poster / product / brand / architecture / photo / illustration / character / scene / history / document / video / other`。

## 三种贡献方式

1. **开 Issue**：贴出案例图 + 完整提示词 + 出处，注明建议分类。
2. **提 PR**：把压缩后的图（长边 ≤1280px，JPEG，<400KB）放到 `images/`，在 `data/prompts.json` 增加条目，并重跑 `python scripts/build_repo.py` 同步 `docs/gallery.md`。
3. **集市投稿**：在 <http://192.168.28.100:8600/>（局域网）注册投稿，审核通过后由维护者在下次 `build_repo.py` 时自动入库。

## 图片规范

- 只收**公开可访问**的社区案例，保留原始出处，不主张第三方内容权利。
- 长边压至 1280px、JPEG q75 以内；GIF/视频不上库（视频用 `live_url` 指回集市站）。
- 涉及真实人物肖像、品牌商标的条目请在 Issue 中说明授权情况。
