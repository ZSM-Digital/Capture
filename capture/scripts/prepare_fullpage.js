async () => {
  const topPause = __TOP_PAUSE__;
  const verifyDelay = __VERIFY_DELAY__;
  const maxAttempts = __MAX_ATTEMPTS__;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const scrollRoots = () => {
    const roots = [document.documentElement, document.body];
    for (const el of document.querySelectorAll("*")) {
      const s = getComputedStyle(el);
      if (
        (s.overflowY === "auto" || s.overflowY === "scroll" ||
         s.overflow === "auto" || s.overflow === "scroll") &&
        el.scrollHeight > el.clientHeight + 1
      ) {
        roots.push(el);
      }
    }
    return roots;
  };

  const scrollOffset = () =>
    Math.max(
      window.scrollY || 0,
      window.pageYOffset || 0,
      document.documentElement?.scrollTop || 0,
      document.body?.scrollTop || 0,
      ...scrollRoots().map((r) => r.scrollTop || 0)
    );

  const scrollAllToTop = () => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    for (const root of scrollRoots()) {
      root.scrollTop = 0;
      root.scrollLeft = 0;
    }
    document.querySelector("[data-capture-scroll-marker]")?.remove();
    const marker = document.createElement("div");
    marker.setAttribute("data-capture-scroll-marker", "1");
    marker.style.cssText =
      "position:absolute;top:0;left:0;width:1px;height:1px;pointer-events:none;opacity:0;";
    (document.body || document.documentElement).prepend(marker);
    marker.scrollIntoView({ block: "start", inline: "nearest", behavior: "instant" });
  };

  scrollAllToTop();
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    if (scrollOffset() <= 1) break;
    scrollAllToTop();
    await sleep(verifyDelay);
  }

  if (scrollOffset() > 1) {
    throw new Error(`failed to scroll to top (offset=${scrollOffset()}px)`);
  }

  await sleep(topPause);

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const isHidden = (el, style) =>
    style.display === "none" ||
    style.visibility === "hidden" ||
    parseFloat(style.opacity) === 0 ||
    el.hidden ||
    el.getAttribute("aria-hidden") === "true";

  const visibleWidth = (rect) =>
    Math.min(rect.right, vw) - Math.max(rect.left, 0);

  const visibleHeight = (rect) =>
    Math.min(rect.bottom, vh) - Math.max(rect.top, 0);

  const shouldHideLayer = (rect) =>
    rect.width <= 0 && rect.height <= 0
      ? true
      : visibleWidth(rect) < 1 ||
        visibleHeight(rect) < 1 ||
        rect.left >= vw - 0.5 ||
        rect.right <= 0.5;

  const positionedLayers = () => {
    const layers = [];
    for (const el of document.querySelectorAll("*")) {
      const style = getComputedStyle(el);
      const pos = style.position;
      if (pos !== "fixed" && pos !== "sticky") continue;
      layers.push(el);
    }
    const depth = (el) => {
      let d = 0;
      let node = el;
      while (node.parentElement) {
        d += 1;
        node = node.parentElement;
      }
      return d;
    };
    layers.sort((a, b) => depth(b) - depth(a));
    return layers;
  };

  const pinPositionedLayers = () => {
    for (const el of positionedLayers()) {
      const style = getComputedStyle(el);
      if (style.display === "none") continue;

      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;

      if (shouldHideLayer(rect) || isHidden(el, style)) {
        el.style.setProperty("display", "none", "important");
        el.setAttribute(
          "data-capture-hidden",
          isHidden(el, style) ? "invisible" : "offscreen"
        );
        continue;
      }

      const top = rect.top + window.scrollY;
      const left = rect.left + window.scrollX;
      el.style.setProperty("position", "absolute", "important");
      el.style.setProperty("top", `${top}px`, "important");
      el.style.setProperty("left", `${left}px`, "important");
      el.style.setProperty("right", "auto", "important");
      el.style.setProperty("bottom", "auto", "important");
      const maxW = vw - Math.max(0, left);
      if (rect.width > 0 && rect.width <= maxW) {
        el.style.setProperty("width", `${rect.width}px`, "important");
      }
    }
  };

  const clampDocumentWidth = () => {
    for (const root of [document.documentElement, document.body]) {
      root.style.setProperty("overflow-x", "hidden", "important");
      root.style.setProperty("max-width", `${vw}px`, "important");
      root.style.setProperty("width", `${vw}px`, "important");
    }
  };

  pinPositionedLayers();
  clampDocumentWidth();

  const layoutWidth = () => document.documentElement.scrollWidth || 0;

  if (layoutWidth() > vw + 2) {
    for (const el of document.querySelectorAll("*")) {
      const rect = el.getBoundingClientRect();
      if (rect.left < vw - 0.5 && rect.right > 0.5) continue;
      const style = getComputedStyle(el);
      if (isHidden(el, style)) continue;
      el.style.setProperty("display", "none", "important");
      el.setAttribute("data-capture-hidden", "overflow");
    }
    clampDocumentWidth();
  }

  if (layoutWidth() > vw + 2) {
__WIDTH_FAIL__
  }

  document.querySelector("[data-capture-scroll-marker]")?.remove();
}
