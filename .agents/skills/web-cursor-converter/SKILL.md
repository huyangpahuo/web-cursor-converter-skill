---
name: web-cursor-converter
description: Convert Windows cursor packs (.ani/.cur) into web-usable animated mouse cursors — PNG frame sequences + hotspot data + a CSS/JS frame-animation frontend for any website or blog. Use whenever the user mentions custom mouse cursors (鼠标指针/光标/自定义光标), hands over .ani or .cur files, asks why a cursor pack doesn't work in a browser, or wants their own animated cursor on their site — even if they just say "帮我做个小鼠标" and drop a folder of .ani files.
---

# Web Cursor Converter

Windows 光标包是 `.ani`(动画)/`.cur`(静态)格式,**浏览器不原生支持**(CSS cursor 只认静态 .cur/.png/.svg,动画图一律不支持)。本 skill 把光标包逐帧转成 PNG + 热点数据,再用 CSS 变量 + JS 定时逐帧切换,实现"会动的鼠标指针"。

## 工作流

### 1. 找到光标包,确认状态

光标包通常是一个文件夹,内含多个 `.ani` 和若干 `.cur`、`Installer.inf`、readme。先 `ls` 看一眼文件名——它们对应鼠标的不同状态(箭头、手指、文本 I 形、忙碌…)。

### 2. 运行转换脚本

依赖:Python + Pillow(`pip install pillow`)。

```bash
python scripts/cursor_convert.py <光标包目录> <输出目录> [尺寸px]
# 例:
python scripts/cursor_convert.py ~/Downloads/MyCursorPack ./public/cursors/mypack 32
```

脚本会:
- 解析每个 .ani(RIFF 容器)逐帧抽出内嵌的 .cur;
- 用 Pillow 解码、等比缩放到目标尺寸(源一般是 128px,网页建议 32px;最大别超 128,Chrome 会拒绝);
- 从 ICONDIRENTRY 读出热点坐标(点击生效点)并按缩放比例换算;
- 输出 `<输出目录>/<state>/<i>.png` + `<输出目录>/data.js`(内容为 `window.WEB_CURSOR = {...}`:每个状态的帧列表、每帧毫秒数、热点)。

文件名 → 状态名的映射表在脚本顶部 `STATE_MAP`(收集了常见光标包命名)。**没映射到的文件**会以文件名小写作为状态名输出,把打印出来的映射结果给用户看一眼,确认哪些状态要接到前端。

### 3. 接入前端(全局,全站生效)

把 `assets/cursor-template.css` 和 `assets/cursor-template.js` 复制进站点并全局引入(`<head>` 引 CSS,`</body>` 前引 JS,JS 要在 data.js 之后):

```html
<script src="/cursors/mypack/data.js"></script>
<script src="/js/cursor.js"></script>
```

模板需要按实际生成结果改两处:
1. **CSS 里的资源基路径**:模板默认 `/cursors/anya/`,替换成你的输出目录对应的站点路径;
2. **只保留实际生成的状态**:模板预写了全部常见状态,把 `data.js` 里没有的删掉即可(JS 端按 `window.WEB_CURSOR` 里实际存在的状态动画,CSS 的兜底规则多几条无害)。

模板已内置的行为,不要破坏:
- CSS 每条规则 `var()` 的第二参数是**静态兜底**(第 0 帧),JS 挂掉也有光标;
- JS 只在 `(pointer: fine)` 的桌面设备运行动画;触屏自动跳过;
- 系统"减少动态效果"(`prefers-reduced-motion`)时停留在静态第 0 帧;
- 标签页切后台暂停动画;单帧状态(如缩放光标)不进入动画循环;
- JS 从自身 `<script src>` 推导资源路径,支持子目录部署。

### 4. 验证

起个本地服务器,浏览器打开后:
- 读 `getComputedStyle(document.documentElement).getPropertyValue('--cursor-normal')` 应看到 url 且帧号随时间变化;
- 悬停链接/按钮 → 手指状态;进输入框 → 文本状态;
- `(pointer: coarse)` 模拟触屏应完全无动画、无报错。

## 常见坑(转换失败或显示异常时读这个)

详见 [references/windows-cursor-format.md](references/windows-cursor-format.md)——包含 .ani 的 RIFF 结构、热点字段位置、ICO 内嵌 BMP 的高度双倍问题、浏览器对 cursor 图的尺寸限制,以及 Hexo/静态站接入时"光标包文件夹被原样部署"的体积陷阱。

## 给别人的交付清单

帮别人做完后,交付四样东西:
1. `<state>/*.png` 帧图目录(部署到站点静态目录);
2. `data.js`;
3. 按其站点路径改好基路径的 cursor.css;
4. cursor.js(通常不用改)。
