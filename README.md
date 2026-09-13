# MyBlog

基于 [Magzine 主题](themes/magzine/README.md) 的个人 Hexo 博客。

常用命令:`hexo clean && hexo generate`(构建)/ `hexo server`(本地预览)/ `hexo deploy`(部署)。

## web-cursor-converter skill(Windows 光标包 → 网页动画光标)

位置:[`.agents/skills/web-cursor-converter/`](.agents/skills/web-cursor-converter/)

把网上下载的 Windows 光标包(`.ani` 动画 / `.cur` 静态)转换成浏览器可用的动画鼠标指针:逐帧抽成 PNG + 热点坐标 + `data.js` 清单,配合 skill 自带的 CSS/JS 模板用 CSS 变量逐帧播放(浏览器原生不支持 .ani 动画光标)。

**给别人用**:整个 `web-cursor-converter/` 文件夹拷给对方,放进他们的 `.agents/skills/` 目录(放用户目录 `~/.agents/skills/` 则全局可用),`pip install pillow`,然后对 AI 说"把 XXX 光标包做成网页鼠标指针"即可。

**本博客的 regenerate**:博客当前的阿尼亚光标资源在 `themes/magzine/source/cursors/anya/`(由该 skill 生成,勿手改)。想换尺寸或换光标包时:

```bash
python .agents/skills/web-cursor-converter/scripts/cursor_convert.py <光标包目录> themes/magzine/source/cursors/anya 32
```

注意:前端 `themes/magzine/source/js/anya-cursor.js` 读取的是 `window.ANYA_CURSOR`,skill 生成的是 `window.WEB_CURSOR`,重新生成后把 data.js 里的变量名改回 `ANYA_CURSOR` 即可(或把 js 里两处引用同步改掉)。

开关:主题 `_config.yml` 里 `cursor.enable`
