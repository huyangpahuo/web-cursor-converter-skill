# Windows 光标格式与浏览器限制备忘

做自定义网页光标失败时,九成踩在下面某一条上。

## .ani 文件结构(RIFF 容器)

```
RIFF....ACON
├─ anih  (36字节头,第7个uint32=默认每帧行jiffie数,1 jiffie=1/60秒)
├─ rate  (可选,每帧的jiffie数组;毫秒 = jiffie × 1000/60)
├─ seq   (可选,帧播放顺序)
└─ LIST('fram')
   ├─ icon  (一个完整的 .cur 文件!)
   ├─ icon
   └─ ...
```

解析要点:遍历 RIFF 块时**块大小按 2 字节对齐**(`size & 1` 补齐),否则第二帧开始全部错位。

## .cur/.ico 内部(ICONDIRENTRY)

```
偏移 0-3  : bWidth, bHeight, bColorCount, bReserved(各1字节)
偏移 4-5  : wPlanes   —— 在 .cur 里被复用为 热点X
偏移 6-7  : wBitCount —— 在 .cur 里被复用为 热点Y
偏移 8-11 : dwBytesInRes
偏移 12-15: dwImageOffset
```

两个经典坑:
1. **热点在 entry 的 4-8 字节**,不是文件头,也不是 entry 末尾;
2. **图像数据不要自己切片喂解码器**——ICO 内嵌 BMP 的 biHeight 是"高×2"(XOR 掩码+AND 掩码),自己按 `dwImageOffset/dwBytesInRes` 切出来给 Pillow 会报 "truncated" 或得到 2 倍高的图。**把整个 .cur 文件直接给 `Image.open`**,它知道怎么处理;热点单独按上表读。

多尺寸 .cur(含多帧 entry):图像取最大的,热点取对应 entry 的。

## 浏览器限制

- **CSS cursor 不支持任何动画格式**(gif/apng/webp/ani 都不行),动画只能靠 JS 逐帧切换 `cursor: url(...)` 或 CSS 变量;
- cursor 图尺寸上限约 **128px**(Chrome/Firefox),超了整条 cursor 声明作废回退关键字——所以源光标(通常 128px)要缩小到 32px 左右再用;
- `cursor: url(...) x y, keyword` 的 **x y 是热点**,必须提供且在图内,否则点击位置偏移;热点坐标要跟图片一起按缩放比例换算;
- 换帧用 **CSS 变量**(`--cursor-normal` 等)挂在 `:root` 上,比遍历元素改 style 便宜得多;pjax/SPA 站点变量在 document 上,换页不丢;
- 合成后的 `url()` 一定要带**关键字兜底**(`, auto` / `, pointer`),资源 404 时不至于没有指针;
- 触屏设备没有指针,用 `(pointer: fine)` 判断跳过;尊重 `(prefers-reduced-motion: reduce)`;
- **iframe 内部无法接管**(B站/YouTube 播放器等),那是独立文档。

## 站点接入陷阱

- **光标包别原样放进站点的静态目录**:一个 .ani 动辄几百 KB,整包 8MB+ 会被原样部署到线上。转换完成后把原始包移出静态目录,只留 PNG 帧 + data.js;
- 帧图记得预加载(模板 JS 已做),否则指针状态首次切换会闪回系统指针;
- Hexo 等静态站:资源放 `source/cursors/<pack>/`(或主题 source 下),模板 JS 从自身 script src 推导路径,子目录部署也可用。

## Python 侧

- 依赖 `pillow`(`pip install pillow`),无需其他;
- `Image.LANCZOS` 缩小像素图效果好;PNG 保存用 `optimize=True`;
- 光标是透明像素图,一律 `convert("RGBA")` 再缩放。
