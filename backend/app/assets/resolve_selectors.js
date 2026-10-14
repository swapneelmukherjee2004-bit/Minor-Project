/* Maps arbitrary CSS selectors (e.g. from axe-core) to this project's canonical selector form. */
(selectors) => {
  const cssPath = (el) => {
    if (el.id && document.querySelectorAll(`[id="${CSS.escape(el.id)}"]`).length === 1) return "#" + CSS.escape(el.id);
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      if (cur.id && document.querySelectorAll(`[id="${CSS.escape(cur.id)}"]`).length === 1) {
        parts.unshift("#" + CSS.escape(cur.id));
        break;
      }
      const tag = cur.tagName.toLowerCase();
      const same = cur.parentElement ? Array.from(cur.parentElement.children).filter((c) => c.tagName === cur.tagName) : [cur];
      parts.unshift(same.length > 1 ? `${tag}:nth-of-type(${same.indexOf(cur) + 1})` : tag);
      cur = cur.parentElement;
    }
    return parts.join(" > ") || el.tagName.toLowerCase();
  };
  return selectors.map((s) => {
    try { const el = document.querySelector(s); return el ? cssPath(el) : null; } catch (e) { return null; }
  });
}
