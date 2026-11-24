# auto-tutorial

录制一次网页操作，自动生成带截图、标注和编号步骤的图文教程。

## 它解决什么问题

写"怎么在教务系统选课""怎么在后台发布活动"这种教程时，人要一边操作、一边截图、一边裁图、一边画红框、最后排版。一个 10 步的流程要花一小时。

本项目把这套流程自动化：**你正常操作一遍，工具自动产出草稿**。

## 当前状态

`v0.7` 全链路打通：录制 → 自动导出事件流 → 合并步骤 → 裁剪标注 → 复核删改 → Markdown / Word / HTML。

- 录制结束时自动把 `events.json` 和截图一起写进下载目录的 `auto-tutorial/`，不用再去控制台抄事件
- 红框按页面元素的真实宽高绘制（读不到尺寸时退回固定经验值）；复核页里红框可拖动、右下角手柄缩放
- 输入类步骤不展示具体填写内容：密码打码、其余输入值清空，文案写成「输入账号 / 密码…」；下拉框写成「选择【选项】」
- 同一输入框的多次输入（打字防抖批次 + 失焦 change）自动合并；相邻重复帧（同控件、画面几乎无变化）自动合并
- 疑似点在表单/卡片空白处的游离点击步骤，在复核页标黄提示优先检查；缺截图时生成占位标注图
- 复核页顶部有步骤缩略导航，可跳转、标记打码步骤；可删步、改文案、调整顺序、在图上拖框打码后二次成文
- 内置三套演示样例（登录选课 / 注册 / 发布活动），见 `samples/`

尚未实现：桌面任意软件录制（二期）；新标签页跳转后的操作采集（一期限制）。


## 目录结构

```
extension/   浏览器扩展：采集操作事件与截图（Chrome MV3）
pipeline/    处理链：frames.py 合并步骤 / annotate.py 裁剪标注 / render.py 成文 / run.py 命令行入口
tools/       演示数据生成脚本
docs/        设计文档
```

## 快速开始（完整链路）

**第一步：录一次操作**

1. 打开 Chrome 或 Edge，访问 `chrome://extensions`
2. 右上角打开「开发者模式」
3. 点「加载已解压的扩展程序」，选择本仓库的 `extension/` 目录
4. 打开要演示的网页，点工具栏上的扩展图标开始录制（图标出现 REC 红标）
5. 正常操作一遍：点按钮、填输入框、切换菜单
6. 再点一次图标结束录制

结束时会自动往浏览器的下载目录里写两份东西（实际目录以 `Ctrl+J` 下载记录为准，不一定是 Downloads）：

```
auto-tutorial/
├── events.json          # 事件流：坐标、元素名字、宽高、页面地址、截图文件名
├── 001_1730...png       # 每次操作后的整屏截图
├── 003_1730...png
└── ...
```

**弹窗 / 验证码没被截到怎么办**：点击事件会即时抓一张定位画面，输入完成 400ms 后截图；如果验证码、协议弹窗更晚才出现，在 `edge://extensions` 打开本扩展的「检查视图 / 服务工具」控制台，看到弹窗后执行：

```js
chrome.runtime.sendMessage({kind:"capture-now"})
```

会补一张当前画面，并替换最近一步的截图。

**第二步：生成教程**

```powershell
python pipeline\run.py `
  --events "$env:USERPROFILE\Downloads\auto-tutorial\events.json" `
  --shots  "$env:USERPROFILE\Downloads\auto-tutorial" `
  --out output
```

得到 `output/tutorial.md`、`output/steps/*.png`（裁剪 + 红框 + 序号）、`output/steps.json`、`output/review.html`。
多次录制会覆盖 `events.json`，想保留就先把整个 `auto-tutorial/` 目录另存。

**第三步：人工复核（可选）**

1. 浏览器打开 `output/review.html`：顶部缩略图可跳转；每张卡片对应一步，直接展示成品标注图；可改步骤说明文字，勾选「删除此步」去掉多余步骤，拖左侧手柄或用 ↑ / ↓ 按钮调整步骤先后顺序；红框可拖动、右下角手柄缩放
2. 需要隐藏的手机号、密码、验证码等内容，在图上按住拖框即可打马赛克；可撤销上一块或清空本步全部马赛克；标黄卡片是疑似游离点击，请优先检查
3. 点「导出修改后的 steps.json」下载编辑结果（含文案、顺序、马赛克区域与调整后的红框）
4. 用 `--steps` 跳过事件合并，按复核后的步骤重新成文：

```powershell
python pipeline\run.py `
  --steps  steps.json `
  --shots  "$env:USERPROFILE\Downloads\auto-tutorial" `
  --out output --format all
```

### 只验证处理链（不需要装扩展）

```bash
pip install -r requirements.txt

# 生成全部演示样例（samples/login、samples/register、samples/publish）
python tools/make_demo.py
# 只生成某一套：python tools/make_demo.py --flow register

# 事件流 -> 教程（samples/ 根目录为默认 login 流程，兼容旧路径）
python pipeline/run.py --events samples/events.json --shots samples/shots --out output
```

常用参数：`--title` 指定标题，`--window 1500` 调合并阈值（毫秒），`--format` 可选 `md` / `docx` / `html` / `both` / `all`（Word 需 `pip install python-docx`）；`--crop-w/--crop-h` 调裁剪区尺寸，`--dedupe-threshold` 调重复帧判定阈值，`--no-dedupe` 关闭重复帧合并。

### 自测

```bash
python tools/pipeline_selftest.py   # 处理链：扩展格式的 events.json -> 教程
node   tools/extension_selftest.js  # 扩展逻辑：事件不丢 / 截图分批 / 导出 JSON
```

### 打包扩展

```bash
python tools/package.py   # 产出 dist/auto-tutorial-extension-<版本>.zip
```

zip 内为扩展根目录文件，可直接在 Chrome / Edge 的扩展页面「加载已解压的扩展程序」时选择解压目录。

## 已知坑

- **Windows 显示缩放不是 100% 时**，截图是物理像素、事件坐标是 CSS 像素，靠 `devicePixelRatio` 换算；如果某张图红框偏了，先确认录制时缩放值没变（换显示器、改缩放都会变）。
- **截图时机**：点击事件即时抓一张定位画面（避免被随后弹出的弹窗盖住按钮），输入完成 400ms 后截图。晚出现的弹窗用上面的 `capture-now` 补拍；点击后页面若立刻跳转，仍可能截到跳转后的画面。
- Chrome 限制每秒最多 2 次 `captureVisibleTab`，所以录制时操作别快到 0.5 秒一次以上，否则会掉图（脚本会告警"缺少对应截图"）。

### 录出来的 events.json 是空的、没有截图

按顺序排查：

1. 在 `edge://extensions` 重新加载扩展后，**一定要刷新要录制的网页**——重载扩展不会把脚本注入已经打开的页面
2. 开始录制后，页面右上角应出现红色「● 录制中」角标；看不到就说明 content.js 没注入到这个页面
3. 打开扩展的「检查视图 / 服务工具」控制台：页面控制台应有 `content.js 已加载` 和点击时的 `上报事件` 日志；服务工具控制台应有 `开始录制`、`收到事件 #n` 日志
4. 先用 `example.com` 这种纯静态页面试一次，排除目标站点的限制
5. 上次录制异常中断可能留下"正在录制"的残留状态，新版本打开扩展时会自动复位

## 技术路线

| 环节 | 做法 | 状态 |
|---|---|---|
| 采集 | Chrome MV3 扩展，监听 click / change / input（400ms 防抖）；事件即时登记并记录元素宽高；点击即时截图定位、输入 400ms 批次截屏；结束录制自动导出 events.json | 已实现 |
| 抽帧 | 同字段的点击+输入合并为一步；同框多次输入合并；勾选的 click/change 合并；同一控件上的连续点选（图形验证码）合并；相邻同控件重复帧按画面差异合并；其余每个点击独立成步 | 已实现 |
| 标注 | 按 dpr 换算坐标，裁 680×400 焦点区，按元素真实宽高画红框，框外压暗，标序号；缺图生成占位图 | 已实现 |
| 成文 | Markdown / Word / HTML 模板，输入类具体值不进教程；另出复核页删步改文案、调序、红框拖动缩放、人工框选马赛克、缩略导航 | 已实现 |

## 分工

- 甲（采集与抽帧）：`extension/`、`pipeline/frames.py`
- 乙（标注与成文）：`pipeline/annotate.py`、`pipeline/render.py`

## 里程碑

- W1：采集跑通，能产出截图与事件流
- W2–4：MVP，从事件流生成一份 Markdown 教程
- W5–7：步骤合并与去重（已完成）
- W8–10：截图裁剪与标注
- W11–12：Word / HTML 导出
- W13：步骤确认页（已完成）
- W14–16：样例库、打包、文档（扩展打包脚本已就位）

## 开发环境

- Python 3.10+（用于 pipeline）
- Chrome / Edge（用于扩展调试）
- 无需 GPU，无需大模型
