/**
 * cursor-template.js — 自定义动画鼠标指针(逐帧动画驱动)
 *
 * 浏览器 CSS cursor 不支持动画图,所以由转换脚本把 Windows 光标包(.ani)
 * 逐帧转成 PNG,这里按 data.js 记录的帧率逐帧切换 CSS 变量。
 *
 * 引入顺序:先 data.js,再本文件(放在 </body> 前,或 pjax 站点常驻位置)。
 *
 * 内置行为:
 *   - 仅桌面(pointer: fine)运行,触屏自动跳过;
 *   - 系统"减少动态效果"时不做动画,静态第 0 帧由 CSS 兜底提供;
 *   - 预加载全部帧,避免指针状态首次切换时闪回系统指针;
 *   - 标签页后台暂停,回来自动恢复;
 *   - 各状态帧率独立(按 data.js 里各自的 ms),rAF 驱动;
 *   - 挂在 <html> 上的 CSS 变量,pjax 换页无需重建。
 */
(function () {
  "use strict";

  var data = window.WEB_CURSOR;
  if (!data) return;

  if (!window.matchMedia("(pointer: fine)").matches) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  // 从本脚本自身的 src 推导光标资源目录,兼容子目录部署。
  // 要求 data.js 与本脚本同目录或按下方 base 规则调整。
  var base = "/cursors/mypack/";
  var script =
    document.currentScript ||
    (function () {
      var all = document.querySelectorAll('script[src*="cursor"]');
      return all[all.length - 1];
    })();
  if (script && script.src) {
    // .../cursors/mypack/cursor.js -> .../cursors/mypack/
    base = script.src.replace(/[^\/]*\.js.*$/, "");
  }

  var root = document.documentElement;
  var animated = [];

  Object.keys(data).forEach(function (key) {
    var st = data[key];
    if (!st.frames || !st.frames.length) return;
    st._imgs = st.frames.map(function (path) {
      var img = new Image();
      img.src = base + path;
      return img;
    });
    if (st.frames.length > 1) animated.push(key);
  });
  if (!animated.length) return;

  // 每个状态独立的帧游标与计时;rAF 单循环驱动所有状态
  var state = {};
  var rafId = null;

  function paintFrame(key, index) {
    var st = data[key];
    var img = st._imgs[index];
    // 帧未加载完就沿用上一帧,避免闪回系统指针
    if (!img.complete || !img.naturalWidth) return;
    root.style.setProperty(
      "--cursor-" + key,
      "url(" + img.src + ") " + st.hotspot[0] + " " + st.hotspot[1]
    );
  }

  function tick(now) {
    for (var i = 0; i < animated.length; i++) {
      var key = animated[i];
      var cur = state[key];
      if (now >= cur.next) {
        // next 以固定步长推进,掉帧时不累积快进
        cur.next = Math.max(cur.next + (data[key].ms || 100), now);
        cur.frame = (cur.frame + 1) % data[key].frames.length;
        paintFrame(key, cur.frame);
      }
    }
    rafId = requestAnimationFrame(tick);
  }

  function resetSchedule() {
    var now = performance.now();
    animated.forEach(function (key) {
      state[key].next = now + (data[key].ms || 100);
    });
  }

  // 立即铺上第 0 帧(把 CSS 静态兜底换成带热点的正式光标),再进入动画循环
  animated.forEach(function (key) {
    state[key] = { frame: 0, next: 0 };
    paintFrame(key, 0);
  });
  resetSchedule();
  rafId = requestAnimationFrame(tick);

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      cancelAnimationFrame(rafId);
      rafId = null;
    } else if (!rafId) {
      // 恢复时重置计时,避免瞬间连跳多帧
      resetSchedule();
      rafId = requestAnimationFrame(tick);
    }
  });
})();
