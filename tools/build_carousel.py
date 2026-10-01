#!/usr/bin/env python3
"""Render a Media Copilot text carousel from a slides JSON file to PNGs and a PDF.

Usage: build_carousel.py slides.json out_dir [--fonts DIR]

Slide types (one object per slide in "slides"):
  cover    {"lines": [...]}                       two or three short lines plus the promise; arrow added
  hero     {"headline": str, "deck": str?}         one big statement, optional small deck
  story    {"headline": str, "deck": str}          headline plus a one-to-three-sentence deck
  number   {"big": str, "text": str}               one big figure, short text under it
  quote    {"quote": str, "deck": str}             pull quote large, context under it
  list     {"lead": str, "items": [...], "tail"?}  lead line plus up to four short lines
  thesis   {"text": str}                           one or two quotable sentences, large
  closer   {"lines": [...], "question": str, "footer"?}
Emphasis: wrap words in [[double brackets]] to set them in the accent yellow. Sparingly.

Output: out_dir/carousel.html, out_dir/slide-01.png ..., out_dir/carousel.pdf
"""
import json, os, sys, re, html, argparse, shutil

W, H = 1080, 1350
PAD_X, PAD_Y = 100, 120          # 9.3%% side margins, 8.9%% top/bottom: inside the 3:4 crop safe zone
MIN_PX = 36

# Per-type ceilings. The fitter shrinks the slide's base size from MAX_PX until the text block
# fits inside MAX_FILL of the padded height, so short slides run big and long ones shrink.
MAX_PX   = {"cover": 84, "hero": 112, "story": 128, "number": 84, "quote": 120, "list": 80, "thesis": 100, "closer": 84}
MAX_FILL = {"cover": .74, "hero": .70, "story": .72, "number": .70, "quote": .72, "list": .72, "thesis": .66, "closer": .60}
DEFAULT_FILL = .72

CSS = """
@font-face{font-family:"Oswald";font-weight:400;src:url("fonts/oswald-latin-400-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald";font-weight:500;src:url("fonts/oswald-latin-500-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald";font-weight:600;src:url("fonts/oswald-latin-600-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald";font-weight:700;src:url("fonts/oswald-latin-700-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald Ext";font-weight:400;src:url("fonts/oswald-latin-ext-400-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald Ext";font-weight:500;src:url("fonts/oswald-latin-ext-500-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald Ext";font-weight:600;src:url("fonts/oswald-latin-ext-600-normal.woff2") format("woff2")}
@font-face{font-family:"Oswald Ext";font-weight:700;src:url("fonts/oswald-latin-ext-700-normal.woff2") format("woff2")}
@font-face{font-family:"Inter";font-weight:400;src:url("fonts/inter-latin-400-normal.woff2") format("woff2")}
@font-face{font-family:"Inter";font-weight:500;src:url("fonts/inter-latin-500-normal.woff2") format("woff2")}
@font-face{font-family:"Inter";font-weight:600;src:url("fonts/inter-latin-600-normal.woff2") format("woff2")}

:root{
  --mc-blue:#004AAD;        /* brand primary */
  --mc-accent:#7AA1D4;      /* brand accent: cover arrow, gradient wash */
  --mc-teal:#1CB5C2;        /* teal end of the brand's diagonal wash, kept under 15%% opacity */
  --mc-yellow:#FFD54A;      /* emphasis color for [[marked]] words; two slides per set at most */
  --ink:#FFFFFF;
  --head:"Oswald","Oswald Ext",sans-serif;
  --body:"Inter",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#111}
body{font-family:var(--head);color:var(--ink);-webkit-font-smoothing:antialiased}
.slide{
  position:relative;width:%(W)dpx;height:%(H)dpx;overflow:hidden;
  padding:%(PY)dpx %(PX)dpx;
  display:flex;flex-direction:column;justify-content:center;
  background:
    linear-gradient(135deg, rgba(122,161,212,.16) 0%%, rgba(122,161,212,0) 42%%),
    linear-gradient(135deg, rgba(28,181,194,0) 58%%, rgba(28,181,194,.13) 100%%),
    var(--mc-blue);
  break-after:page;page-break-after:always;
}
.slide:last-child{break-after:auto;page-break-after:auto}
.content{width:100%%;text-align:left;line-height:1.12;letter-spacing:.004em}
.content *{overflow-wrap:break-word}
.cover .line,.headline,.thesis p,.closer .line,.list .lead{text-wrap:balance}
.deck,.number p,.list li,.closer .question{text-wrap:pretty}
em.hi{font-style:normal;color:var(--mc-yellow)}

/* cover: three short lines, heavy, arrow under the last */
.cover .line{font-weight:700;display:block}
.cover .line+.line{margin-top:.3em}
.cover .arrow{display:block;width:3.4em;height:auto;margin-top:.5em;margin-left:.04em}

/* hero: one big statement, optional small deck */
.hero .headline{font-weight:700;line-height:1.08}
.hero .deck{font-weight:400;font-size:.42em;line-height:1.25;margin-top:1.1em;max-width:92%%}

/* story: headline plus deck */
.story .headline{font-weight:700;line-height:1.06}
.story .deck{font-weight:400;font-size:.55em;line-height:1.24;margin-top:.8em}

/* number: big figure, short text */
.number .big{font-weight:700;font-size:2.1em;line-height:1;white-space:nowrap;letter-spacing:-.01em;display:block;margin-bottom:.3em}
.number p{font-weight:500;font-size:.95em;line-height:1.16}

/* pull quote: the quote large, context small */
.quote .q{font-weight:700;font-size:1.55em;line-height:1.05;display:block;margin-bottom:.45em;white-space:nowrap}
.quote .deck{font-weight:400;font-size:.62em;line-height:1.24}

/* list: lead line plus short lines */
.list .lead{font-weight:700;margin-bottom:.55em}
.list ul{list-style:none}
.list li{font-weight:400;font-size:.8em;line-height:1.2;padding-left:.85em;text-indent:-.85em;margin-top:.42em}
.list li::before{content:"\\2022";display:inline-block;width:.85em;text-indent:0;font-weight:700}
.list .tail{font-weight:500;margin-top:.6em}

/* thesis: one or two quotable sentences */
.thesis p{font-weight:600;line-height:1.14}

/* closer */
.closer .line{font-weight:700;display:block}
.closer .question{font-weight:400;margin-top:.7em;font-size:.82em;line-height:1.2}
.footer{position:absolute;left:%(PX)dpx;bottom:64px;font-family:var(--body);font-weight:500;font-size:28px;letter-spacing:.02em;opacity:.85}

@media print{ @page{size:%(W)dpx %(H)dpx;margin:0} html,body{background:transparent} }
""" % {"W": W, "H": H, "PX": PAD_X, "PY": PAD_Y}

ARROW_SVG = (
    '<svg class="arrow" viewBox="0 0 300 110" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M14 70 C 60 54, 120 44, 176 48 C 214 51, 246 56, 276 54" stroke="#7AA1D4" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M232 20 C 246 34, 262 46, 280 54 C 262 62, 246 76, 236 92" stroke="#7AA1D4" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

def smarten(s):
    """Typographic quotes: straight quotes in the JSON become curly on the slide."""
    s = re.sub(r'(^|[\s(\[])"', '\\1\u201c', s)
    s = s.replace('"', '\u201d')
    s = re.sub(r"(^|[\s(\[])'", '\\1\u2018', s)
    s = s.replace("'", '\u2019')
    return s

def esc(s):
    """Escape for HTML, curl the quotes, and turn [[x]] into the emphasis span."""
    parts = re.split(r'(\[\[.*?\]\])', s)
    out = []
    for p in parts:
        if p.startswith('[[') and p.endswith(']]'):
            out.append('<em class="hi">' + html.escape(smarten(p[2:-2]), quote=False) + '</em>')
        else:
            out.append(html.escape(smarten(p), quote=False))
    return ''.join(out)

def render_slide(s):
    t = s["type"]
    if t == "cover":
        body = "".join(f'<span class="line">{esc(l)}</span>' for l in s["lines"]) + ARROW_SVG
    elif t == "hero":
        body = f'<p class="headline">{esc(s["headline"])}</p>'
        if s.get("deck"):
            body += f'<p class="deck">{esc(s["deck"])}</p>'
    elif t == "story":
        body = f'<p class="headline">{esc(s["headline"])}</p><p class="deck">{esc(s["deck"])}</p>'
    elif t == "number":
        body = f'<span class="big">{esc(s["big"])}</span><p>{esc(s["text"])}</p>'
    elif t == "quote":
        body = f'<span class="q">{esc(s["quote"])}</span><p class="deck">{esc(s["deck"])}</p>'
    elif t == "list":
        body = f'<p class="lead">{esc(s["lead"])}</p><ul>' + "".join(f'<li>{esc(i)}</li>' for i in s["items"]) + '</ul>'
        if s.get("tail"):
            body += f'<p class="tail">{esc(s["tail"])}</p>'
    elif t == "thesis":
        body = f'<p>{esc(s["text"])}</p>'
    elif t == "closer":
        body = "".join(f'<span class="line">{esc(l)}</span>' for l in s["lines"])
        body += f'<p class="question">{esc(s["question"])}</p>'
    else:
        raise ValueError(f"unknown slide type {t}")
    footer = f'<div class="footer">{esc(s["footer"])}</div>' if s.get("footer") else ""
    return f'<section class="slide {t}" data-type="{t}"><div class="content">{body}</div>{footer}</section>'

def build_html(data):
    slides = "\n".join(render_slide(s) for s in data["slides"])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(data.get("title","Carousel"))}</title>'
            f'<style>{CSS}</style></head><body>\n{slides}\n</body></html>')

FIT_JS = """
(cfg) => {
  const inner = cfg.H - 2*cfg.PY;
  const out = [];
  document.querySelectorAll('.slide').forEach(sl => {
    const type = sl.dataset.type;
    const maxH = inner * (cfg.MAX_FILL[type] || cfg.DEFAULT_FILL);
    const c = sl.querySelector('.content');
    let lo = cfg.MIN_PX, hi = cfg.MAX_PX[type] || 72, best = lo;
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      c.style.fontSize = mid + 'px';
      const h = c.getBoundingClientRect().height;
      const fitsW = c.scrollWidth <= c.clientWidth + 1;
      if (h <= maxH && fitsW) { best = mid; lo = mid; } else { hi = mid; }
    }
    c.style.fontSize = best + 'px';
    const h = c.getBoundingClientRect().height;
    out.push({type, fontPx: Math.round(best*10)/10, fill: Math.round(100*h/inner)});
  });
  return out;
}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slides")
    ap.add_argument("out")
    ap.add_argument("--fonts", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
    a = ap.parse_args()

    data = json.load(open(a.slides))
    os.makedirs(a.out, exist_ok=True)
    fonts_dst = os.path.join(a.out, "fonts")
    if os.path.abspath(a.fonts) != os.path.abspath(fonts_dst):
        shutil.copytree(a.fonts, fonts_dst, dirs_exist_ok=True)
    html_path = os.path.join(a.out, "carousel.html")
    open(html_path, "w").write(build_html(data))

    cfg = {"H": H, "PY": PAD_Y, "MIN_PX": MIN_PX, "MAX_PX": MAX_PX, "MAX_FILL": MAX_FILL, "DEFAULT_FILL": DEFAULT_FILL}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto("file://" + os.path.abspath(html_path))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        fit = pg.evaluate(FIT_JS, cfg)
        for i, el in enumerate(pg.query_selector_all(".slide"), 1):
            el.screenshot(path=os.path.join(a.out, f"slide-{i:02d}.png"), type="png")
        pg.emulate_media(media="print")
        pg.evaluate(FIT_JS, cfg)   # same sizes under print media
        pdf_path = os.path.join(a.out, "carousel.pdf")
        pg.pdf(path=pdf_path, width=f"{W}px", height=f"{H}px", print_background=True,
               prefer_css_page_size=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        b.close()

    for i, f in enumerate(fit, 1):
        print(f"slide {i:02d} {f['type']:7s} {f['fontPx']:5.1f}px  fill {f['fill']:3d}%")
    print("wrote", len(fit), "PNGs and", pdf_path)

if __name__ == "__main__":
    main()
