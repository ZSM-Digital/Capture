    for (const root of [document.documentElement, document.body]) {
      root.style.setProperty("overflow-x", "clip", "important");
      root.style.setProperty("max-width", `${vw}px`, "important");
    }
