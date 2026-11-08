# auto-tutorial

录制一次网页操作，自动生成带截图、标注和编号步骤的图文教程。

## 它解决什么问题

写"怎么在教务系统选课""怎么在后台发布活动"这种教程时，人要一边操作、一边截图、一边裁图、一边画红框、最后排版。一个 10 步的流程要花一小时。

本项目把这套流程自动化：**你正常操作一遍，工具自动产出草稿**。

## 当前状态

`v0.2` 骨架可跑通：录制 → 事件流 → 合并步骤 → 裁剪标注 → Markdown。
用演示数据验证过：4 条事件自动合并为 3 个步骤，输出 `output/tutorial.md` 与 3 张带红框和序号的截图。

尚未实现：画面差异去重、Word / HTML 导出、步骤人工确认页、打包。


## 目录结构

```
extension/   浏览器扩展：采集操作事件与截图（Chrome MV3）
pipeline/    处理链：frames.py 合并步骤 / annotate.py 裁剪标注 / render.py 成文 / run.py 命令行入口
tools/       演示数据生成脚本
docs/        设计文档
```

## 快速开始（第 1 周验证用）

1. 打开 Chrome 或 Edge，访问 `chrome://extensions`
2. 右上角打开「开发者模式」
3. 点「加载已解压的扩展程序」，选择本仓库的 `extension/` 目录
4. 打开任意网页，点浏览器工具栏上的扩展图标 → 开始录制（图标出现 REC 标记）
5. 在页面上点几下、输入一点内容，再点一次图标结束录制
6. 截图会保存到浏览器下载目录下的 `auto-tutorial/` 子目录
7. 事件流（点击坐标、元素文字、页面地址）存在扩展的 `chrome.storage.local` 中，可在扩展页的「检查视图」控制台里查看

如果能顺利产出"5 次点击 → 5 张截图 + 5 条事件记录"，说明路线成立，可以继续做后面的抽帧与成文。

### 只验证处理链（不需要装扩展）

```bash
pip install -r requirements.txt

# 生成演示页面和 4 条事件
python tools/make_demo.py

# 事件流 -> 教程
python pipeline/run.py --events samples/events.json --shots samples/shots --out output
```

会得到 `output/tutorial.md`、`output/steps/*.png`（裁剪 + 红框 + 序号）、`output/steps.json`。

常用参数：`--title` 指定标题，`--window 1500` 调合并阈值（毫秒），`--format docx` 或 `both` 额外导出 Word（需 `pip install python-docx`）。

## 技术路线

| 环节 | 做法 | 状态 |
|---|---|---|
| 采集 | Chrome MV3 扩展，监听 click / change，事件后 400ms 调 `captureVisibleTab` 截图 | 已有骨架 |
| 抽帧 | 同页同类型事件在 1.5 秒内合并，合并后按最后一次操作定位 | 已实现（基础版） |
| 标注 | 按 dpr 换算坐标，裁 760×440 焦点区，框外压暗，画红框与序号 | 已实现（基础版） |
| 成文 | Markdown 模板；Word 可选 | Markdown 已实现，Word 待验证 |

## 分工

- 甲（采集与抽帧）：`extension/`、`pipeline/frames.py`
- 乙（标注与成文）：`pipeline/annotate.py`、`pipeline/render.py`

## 里程碑

- W1：采集跑通，能产出截图与事件流
- W2–4：MVP，从事件流生成一份 Markdown 教程
- W5–7：步骤合并与去重
- W8–10：截图裁剪与标注
- W11–12：Word / HTML 导出
- W13：步骤确认页
- W14–16：样例库、打包、文档

## 开发环境

- Python 3.10+（用于 pipeline）
- Chrome / Edge（用于扩展调试）
- 无需 GPU，无需大模型
