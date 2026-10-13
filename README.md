把网上下载的 Windows 光标包(.ani 动画 / .cur 静态)转换成浏览器可用的动画鼠标指针

即逐帧抽成 PNG + 热点坐标 + data.js 清单,配合 skill 自带的 CSS/JS 模板用 CSS 变量逐帧播放(浏览器原生不支持 .ani 动画光标)

放入当前项目的 .agents/skills/ 目录(放用户目录 ~/.agents/skills/ 则全局可用)

然后对 AI 说"把 XXX 光标包做成网页鼠标指针"即可
