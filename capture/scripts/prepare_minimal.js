async () => {
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  for (const root of [document.documentElement, document.body]) {
    root.scrollTop = 0;
    root.scrollLeft = 0;
    root.style.setProperty("overflow-x", "hidden", "important");
    root.style.setProperty("max-width", `${window.innerWidth}px`, "important");
  }
}
