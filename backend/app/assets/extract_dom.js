/* Extracts a bounded, structured accessibility context from the rendered page.
   Returns plain JSON. Runs inside the page (untrusted content): never eval()s anything. */
(opts) => {
  const LIM = opts.limits;
  const txt = (s, n = 160) => (s || "").replace(/\s+/g, " ").trim().slice(0, n);
  const refs = new Map();
  const list = [];

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
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
  };
  const ref = (el) => {
    if (refs.has(el)) return refs.get(el);
    const id = "e" + (list.length + 1);
    refs.set(el, id);
    list.push(el);
    return id;
  };
  const labelledBy = (el) => {
    const ids = (el.getAttribute("aria-labelledby") || "").split(/\s+/).filter(Boolean);
    return ids.map((i) => document.getElementById(i)).filter(Boolean).map((n) => n.textContent).join(" ");
  };
  const accName = (el) => {
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return txt(aria);
    const lb = labelledBy(el);
    if (lb.trim()) return txt(lb);
    if (el.tagName === "IMG") return txt(el.getAttribute("alt"));
    if (el.labels && el.labels.length) return txt(Array.from(el.labels).map((l) => l.textContent).join(" "));
    if (el.tagName === "INPUT" && ["button", "submit", "reset"].includes(el.type)) return txt(el.value);
    const t = txt(el.textContent);
    if (t) return t;
    const img = el.querySelector && el.querySelector("img[alt]");
    if (img) return txt(img.getAttribute("alt"));
    return txt(el.getAttribute("title"));
  };
  const nearby = (el) => {
    const bits = [];
    const cap = el.closest("figure") && el.closest("figure").querySelector("figcaption");
    if (cap) bits.push("caption: " + txt(cap.textContent, 200));
    const p = el.parentElement;
    if (p) bits.push("parent text: " + txt(p.textContent, 240));
    let h = el.previousElementSibling;
    let n = 0;
    while (h && n < 3 && !/^H[1-6]$/.test(h.tagName)) { h = h.previousElementSibling; n++; }
    if (h && /^H[1-6]$/.test(h.tagName)) bits.push("preceding heading: " + txt(h.textContent, 120));
    return bits.join(" | ");
  };
  const html = (el) => txt(el.outerHTML, LIM.html);
  const style = (el) => {
    const cs = getComputedStyle(el);
    return { color: cs.color, backgroundColor: cs.backgroundColor, fontSize: cs.fontSize, fontWeight: cs.fontWeight };
  };
  const base = (el) => ({ ref: ref(el), selector: cssPath(el), html: html(el), visible: visible(el) });

  const out = {};
  out.title = txt(document.title, 300);
  out.lang = document.documentElement.getAttribute("lang") || "";
  out.url = location.href;
  out.viewport = { width: innerWidth, height: innerHeight, scrollHeight: document.documentElement.scrollHeight };
  out.counts = {};
  const take = (name, sel, fn) => {
    const all = Array.from(document.querySelectorAll(sel));
    out.counts[name] = all.length;
    return all.slice(0, LIM.perType).map(fn);
  };

  out.headings = take("headings", "h1,h2,h3,h4,h5,h6,[role=heading]", (el) => ({
    ...base(el), level: el.getAttribute("aria-level") ? +el.getAttribute("aria-level") : (/^H[1-6]$/.test(el.tagName) ? +el.tagName[1] : null),
    text: txt(el.textContent), fontSize: getComputedStyle(el).fontSize,
  }));
  out.images = take("images", "img,[role=img],svg[role=img],input[type=image]", (el) => ({
    ...base(el), tag: el.tagName.toLowerCase(), alt: el.hasAttribute("alt") ? el.getAttribute("alt") : null,
    ariaLabel: el.getAttribute("aria-label"), role: el.getAttribute("role"),
    src: txt(el.getAttribute("src") || "", 120), inLink: !!el.closest("a,button"),
    width: Math.round(el.getBoundingClientRect().width), height: Math.round(el.getBoundingClientRect().height),
    nearbyText: nearby(el),
  }));
  out.links = take("links", "a[href]", (el) => ({
    ...base(el), text: txt(el.textContent), ariaLabel: el.getAttribute("aria-label"), accessibleName: accName(el),
    href: txt(el.getAttribute("href"), 120), nearbyText: nearby(el), style: style(el),
  }));
  out.buttons = take("buttons", "button,[role=button],input[type=button],input[type=submit],input[type=reset]", (el) => ({
    ...base(el), tag: el.tagName.toLowerCase(), visibleText: txt(el.tagName === "INPUT" ? el.value : el.textContent),
    ariaLabel: el.getAttribute("aria-label"), accessibleName: accName(el), nearbyText: nearby(el), style: style(el),
  }));
  out.formControls = take("formControls", "input:not([type=hidden]):not([type=button]):not([type=submit]):not([type=reset]),select,textarea", (el) => ({
    ...base(el), tag: el.tagName.toLowerCase(), type: el.type || null, name: el.getAttribute("name"),
    labelText: el.labels && el.labels.length ? txt(Array.from(el.labels).map((l) => l.textContent).join(" ")) : "",
    ariaLabel: el.getAttribute("aria-label"), accessibleName: accName(el), placeholder: el.getAttribute("placeholder"),
    required: el.required || el.getAttribute("aria-required") === "true",
    describedBy: txt(((el.getAttribute("aria-describedby") || "").split(/\s+/).map((i) => (document.getElementById(i) || {}).textContent || "").join(" "))),
    ariaInvalid: el.getAttribute("aria-invalid"), nearbyText: nearby(el),
  }));
  out.landmarks = take("landmarks", "header,nav,main,aside,footer,[role=banner],[role=navigation],[role=main],[role=complementary],[role=contentinfo],[role=search]", (el) => ({
    ...base(el), tag: el.tagName.toLowerCase(), role: el.getAttribute("role"), ariaLabel: el.getAttribute("aria-label"),
  }));
  out.messages = take("messages", "[role=alert],[role=status],[aria-live],.error,.error-message,[class*=error]", (el) => ({
    ...base(el), role: el.getAttribute("role"), ariaLive: el.getAttribute("aria-live"), text: txt(el.textContent, 240),
  }));
  out.styledTextCandidates = (() => {
    const res = [];
    for (const el of document.querySelectorAll("div,p,span,strong,b")) {
      if (res.length >= 15) break;
      if (el.closest("h1,h2,h3,h4,h5,h6,[role=heading],button,a,label")) continue;
      if (el.children.length > 0 && el.querySelector("div,p,ul,ol")) continue;
      const t = txt(el.textContent, 100);
      if (!t || t.length > 80 || !visible(el)) continue;
      const cs = getComputedStyle(el);
      if (parseFloat(cs.fontSize) >= 22 && parseInt(cs.fontWeight, 10) >= 600) {
        res.push({ ...base(el), tag: el.tagName.toLowerCase(), text: t, fontSize: cs.fontSize, fontWeight: cs.fontWeight });
      }
    }
    return res;
  })();
  out.visibleTextSample = txt(document.body ? document.body.innerText : "", LIM.bodyText);
  return out;
}
