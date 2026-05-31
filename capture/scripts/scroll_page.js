async () => {
  const stepDelay = __STEP_DELAY__;
  const endPause = __END_PAUSE__;
  const maxSteps = __MAX_STEPS__;
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

  const scrollAllTo = (top) => {
    window.scrollTo({ top, left: 0, behavior: "instant" });
    for (const root of scrollRoots()) {
      root.scrollTop = top;
      root.scrollLeft = 0;
    }
  };

  const maxScrollTop = () => {
    let max = Math.max(
      document.documentElement?.scrollHeight ?? 0,
      document.body?.scrollHeight ?? 0,
      document.documentElement?.offsetHeight ?? 0,
      document.body?.offsetHeight ?? 0
    ) - window.innerHeight;
    for (const root of scrollRoots()) {
      if (root === document.documentElement || root === document.body) continue;
      max = Math.max(max, root.scrollHeight - root.clientHeight);
    }
    return Math.max(0, max);
  };

  const step = Math.max(window.innerHeight * 0.85, 400);
  const maxY = maxScrollTop();
  let y = 0;
  let steps = 0;

  while (y < maxY && steps < maxSteps) {
    y = Math.min(y + step, maxY);
    scrollAllTo(y);
    await sleep(stepDelay);
    steps += 1;
  }

  scrollAllTo(maxY);
  await sleep(endPause);
}
