import re
from pathlib import Path

import fitz  # PyMuPDF
from opencc import OpenCC
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
INPUT_PDF = ROOT.parent / "Scars_to_Your_Beautiful(1).pdf"
OUT_DIR = ROOT
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_TXT = OUT_DIR / "Scars_to_Your_Beautiful_简体.txt"
OUT_HTML = OUT_DIR / "index.html"
OUT_PDF = OUT_DIR / "Scars_to_Your_Beautiful_简体.pdf"


def extract_text_pymupdf(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        # Use layout-aware blocks to reduce broken line wraps from PDF exports.
        # Each block: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks") or []
        blocks_sorted = sorted(blocks, key=lambda b: (b[1], b[0]))
        parts: list[str] = []
        for b in blocks_sorted:
            t = (b[4] or "").replace("\r\n", "\n").replace("\r", "\n")
            t = "\n".join(line.rstrip() for line in t.split("\n")).strip()
            if not t:
                continue
            parts.append(t)
        text = "\n\n".join(parts).strip() + "\n"
        pages.append(text)
    return pages


def normalize_text(text: str) -> str:
    # Normalize line endings and remove trailing spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # Collapse excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def build_notion_like_html(title: str, full_text_sc: str) -> str:
    # Render from "Summary" onward (skip AO3 metadata header)
    lines_all = full_text_sc.splitlines()
    start_idx = 0
    for i, line in enumerate(lines_all):
        if line.strip() == "Summary":
            start_idx = i
            break
    lines = lines_all[start_idx:]

    toc: list[tuple[str, str]] = [("Summary", "summary")]
    body_parts: list[str] = ['<h2 id="summary" class="h2">Summary</h2>']

    chapter_re = re.compile(r"^Chapter\s+(\d+)\b", re.IGNORECASE)
    for line in lines[1:]:
        m = chapter_re.match(line.strip())
        if m:
            ch = m.group(1)
            anchor = f"chapter-{ch}"
            toc.append((f"Chapter {ch}", anchor))
            body_parts.append(f'<h2 id="{anchor}" class="h2">Chapter {ch}</h2>')
            continue

        s = line.strip()
        if s == "":
            body_parts.append('<div class="spacer"></div>')
        elif s in {"現在", "過去"}:
            body_parts.append(f'<h3 class="label">{escape_html(s)}</h3>')
        else:
            body_parts.append(
                f'<div class="block" tabindex="-1"><p>{escape_html(s)}</p></div>'
            )

    toc_html = "\n".join(
        f'<li><a href="#{anchor}">{escape_html(name)}</a></li>' for name, anchor in toc
    )
    body_html = "\n".join(body_parts)

    product_name = "touchfish"
    return f"""<!doctype html>
<html lang="zh-Hans">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape_html(product_name)}</title>
    <meta name="color-scheme" content="light dark" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <!-- pdf.js: v4 npm 包不再附带 legacy UMD（旧 CDN 路径 404）。固定使用 3.x legacy 以保证 window.pdfjsLib -->
    <script src="https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/legacy/build/pdf.min.js"></script>
    <script>
      // pdf.js worker (legacy build exposes global `window.pdfjsLib`)
      if (window.pdfjsLib && window.pdfjsLib.GlobalWorkerOptions) {{
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
          'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/legacy/build/pdf.worker.min.js';
      }}
    </script>
    <script src="https://cdn.jsdelivr.net/npm/opencc-js@1.0.5/dist/umd/full.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js"></script>
    <style>
      :root {{
        /* touchfish — artful, dark-first, neon accents */
        --font-display: "Space Grotesk", ui-sans-serif, system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
        --font-body: ui-sans-serif, system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
        --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;

        --bg: #070914;
        --paper: rgba(12, 15, 34, 0.72);
        --paper-solid: #0b1020;
        --fg: rgba(255, 255, 255, 0.92);
        --muted: rgba(255, 255, 255, 0.70);
        --subtle: rgba(255, 255, 255, 0.52);
        --border: rgba(255, 255, 255, 0.12);
        --border-2: rgba(255, 255, 255, 0.18);
        --surface: rgba(255, 255, 255, 0.06);
        --surface-2: rgba(255, 255, 255, 0.10);
        --link: #7df9ff; /* neon-cyan */
        --accent: #a78bfa; /* purple */
        --accent-2: #38bdf8; /* cyan */
        --accent-3: #fbbf24; /* amber */
        --sel: rgba(125, 249, 255, 0.18);

        --shadow: 0 20px 64px rgba(0, 0, 0, 0.62);
        --shadow-sm: 0 10px 28px rgba(0, 0, 0, 0.48);
        --maxw: 860px;
        --radius: 16px;
        --radius-lg: 22px;
        --focus: rgba(125, 249, 255, 0.28);
        --paper-border: color-mix(in srgb, var(--border) 88%, transparent);
        --caret: rgba(255, 255, 255, 0.74);

        --mesh:
          radial-gradient(1200px 520px at 18% -8%, rgba(167, 139, 250, 0.22), transparent 62%),
          radial-gradient(980px 520px at 82% 0%, rgba(56, 189, 248, 0.18), transparent 60%),
          radial-gradient(860px 520px at 50% 110%, rgba(251, 191, 36, 0.10), transparent 56%);
        --grid:
          linear-gradient(to right, rgba(255,255,255,0.045) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255,255,255,0.045) 1px, transparent 1px);
      }}
      @media (prefers-color-scheme: light) {{
        :root {{
          --bg: #f7f7fb;
          --paper: rgba(255, 255, 255, 0.84);
          --paper-solid: #ffffff;
          --fg: rgba(15, 23, 42, 0.96);
          --muted: rgba(15, 23, 42, 0.70);
          --subtle: rgba(15, 23, 42, 0.52);
          --border: rgba(15, 23, 42, 0.10);
          --border-2: rgba(15, 23, 42, 0.14);
          --surface: rgba(15, 23, 42, 0.04);
          --surface-2: rgba(15, 23, 42, 0.06);
          --link: #2563eb;
          --accent: #7c3aed;
          --accent-2: #0891b2;
          --accent-3: #b45309;
          --sel: rgba(37, 99, 235, 0.14);
          --shadow: 0 18px 56px rgba(15, 23, 42, 0.14);
          --shadow-sm: 0 10px 28px rgba(15, 23, 42, 0.10);
          --focus: rgba(37, 99, 235, 0.22);
          --caret: rgba(15, 23, 42, 0.72);
          --mesh:
            radial-gradient(1100px 520px at 16% -10%, rgba(124, 58, 237, 0.12), transparent 62%),
            radial-gradient(980px 520px at 84% 0%, rgba(8, 145, 178, 0.10), transparent 60%),
            radial-gradient(860px 520px at 50% 110%, rgba(180, 83, 9, 0.08), transparent 56%);
          --grid:
            linear-gradient(to right, rgba(15,23,42,0.055) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(15,23,42,0.055) 1px, transparent 1px);
        }}
      }}
      /* Eye-care preset (manual toggle) */
      body.eye {{
        --bg: #fbf7ef;
        --paper: #fff8ea;
        --fg: rgba(52, 44, 34, 0.92);
        --muted: rgba(52, 44, 34, 0.62);
        --subtle: rgba(52, 44, 34, 0.44);
        --border: rgba(52, 44, 34, 0.12);
        --surface: rgba(52, 44, 34, 0.045);
        --surface-2: rgba(52, 44, 34, 0.065);
        --link: #2563eb;
        --sel: rgba(35, 131, 226, 0.12);
        --shadow: 0 14px 40px rgba(52, 44, 34, 0.10);
        --grad: radial-gradient(760px 220px at 20% 0%, rgba(37, 99, 235, 0.10), transparent 62%),
                radial-gradient(640px 220px at 80% 10%, rgba(14, 165, 233, 0.10), transparent 55%);
      }}
      body.dim {{
        filter: saturate(0.96) brightness(0.96);
      }}
      body.wide {{
        --maxw: 920px;
      }}
      body.comfort {{
        --maxw: 760px;
      }}
      * {{ box-sizing: border-box; }}
      html {{ scroll-behavior: smooth; }}
      body {{
        margin: 0;
        background:
          var(--mesh),
          var(--bg);
        color: var(--fg);
        font-family: var(--font-body);
        line-height: 1.72;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
      }}
      body::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
          var(--grid);
        background-size: 42px 42px;
        opacity: 0.35;
        mix-blend-mode: overlay;
      }}
      body::after {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
          linear-gradient(to bottom, rgba(255,255,255,0.06), transparent 16%, transparent 84%, rgba(255,255,255,0.04)),
          repeating-linear-gradient(
            to bottom,
            rgba(255,255,255,0.018) 0px,
            rgba(255,255,255,0.018) 1px,
            transparent 2px,
            transparent 6px
          );
        opacity: 0.16;
        mix-blend-mode: overlay;
      }}
      .layout {{
        display: grid;
        grid-template-columns: 260px 1fr;
        gap: 18px;
        max-width: 1180px;
        padding: 18px 16px 28px;
        margin: 0 auto;
        align-items: start;
        isolation: isolate;
      }}
      .layout::before {{
        content: "";
        position: absolute;
        /* create a subtle column divider line */
        left: calc(16px + 260px + 9px);
        top: 0;
        bottom: 0;
        width: 1px;
        background: color-mix(in srgb, var(--border) 70%, transparent);
        opacity: 0.6;
        pointer-events: none;
        display: none;
      }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 100;
        backdrop-filter: blur(18px) saturate(1.2);
        background: color-mix(in srgb, var(--paper-solid) 72%, transparent);
        border-bottom: 1px solid color-mix(in srgb, var(--border) 80%, transparent);
        box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset;
      }}
      .hotkeys {{
        display: none;
        color: var(--subtle);
        font-size: 12px;
      }}
      .topbar-inner {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }}
      .brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }}
      .logo {{
        width: 22px;
        height: 22px;
        border-radius: 8px;
        background: linear-gradient(135deg, color-mix(in srgb, var(--link) 96%, #0000), color-mix(in srgb, #38bdf8 62%, #0000));
        box-shadow: var(--shadow-sm);
        position: relative;
        flex: none;
      }}
      .logo::after {{
        content: "";
        position: absolute;
        inset: 6px 5px 6px 8px;
        border-radius: 999px;
        border: 2px solid rgba(255, 255, 255, 0.92);
        border-left-color: transparent;
        border-bottom-color: transparent;
        transform: rotate(18deg);
        opacity: 0.95;
      }}
      .dot {{
        width: 9px;
        height: 9px;
        border-radius: 999px;
        background: color-mix(in srgb, var(--link) 18%, var(--surface-2));
        border: 1px solid var(--border);
      }}
      .brand-title {{
        font-size: 13px;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-family: var(--font-mono);
        letter-spacing: 0.02em;
      }}
      .file-btn {{
        position: relative;
        overflow: hidden;
      }}
      .file-btn input[type="file"] {{
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
      }}

      /* Library (entry GUI) */
      .library {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 18px 16px 34px;
      }}
      .hero {{
        position: relative;
        border: 1px solid var(--paper-border);
        background: color-mix(in srgb, var(--paper-solid) 70%, transparent);
        border-radius: var(--radius-lg);
        padding: 22px 22px;
        box-shadow: var(--shadow);
        overflow: hidden;
      }}
      .hero::before {{
        content: "";
        position: absolute;
        inset: -2px;
        background: radial-gradient(820px 320px at 18% 0%, rgba(167,139,250,0.32), transparent 60%),
                    radial-gradient(760px 320px at 82% 10%, rgba(56,189,248,0.24), transparent 60%),
                    radial-gradient(900px 420px at 50% 110%, rgba(251,191,36,0.10), transparent 60%);
        opacity: 0.65;
        filter: blur(0px);
        pointer-events: none;
      }}
      .hero::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(to bottom, rgba(255,255,255,0.06), transparent 36%, rgba(255,255,255,0.02));
        pointer-events: none;
      }}
      .hero-head {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
      }}
      .hero h1 {{
        margin: 0 0 6px;
        font-family: var(--font-display);
        font-size: clamp(22px, 2.3vw, 30px);
        letter-spacing: -0.03em;
        line-height: 1.12;
        background: linear-gradient(90deg, color-mix(in srgb, var(--link) 96%, white), color-mix(in srgb, var(--accent) 82%, white));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }}
      .hero p {{
        margin: 0;
        color: var(--muted);
        font-size: 14px;
      }}
      .hero-actions {{
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .i {{
        width: 16px;
        height: 16px;
        display: inline-block;
        vertical-align: -3px;
      }}
      .i svg {{
        width: 16px;
        height: 16px;
        stroke: currentColor;
        fill: none;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      .primary {{
        border: 1px solid transparent;
        background: color-mix(in srgb, var(--link) 92%, #0000);
        color: #fff;
        border-radius: 12px;
        padding: 10px 12px;
        cursor: pointer;
        font: inherit;
        font-size: 13.5px;
        line-height: 1;
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }}
      .primary:hover {{
        filter: brightness(0.98);
      }}
      .secondary {{
        border: 1px solid var(--border);
        background: transparent;
        color: var(--fg);
        border-radius: 12px;
        padding: 10px 12px;
        cursor: pointer;
        font: inherit;
        font-size: 13.5px;
        line-height: 1;
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }}
      .secondary:hover {{
        background: color-mix(in srgb, var(--paper) 90%, var(--surface));
      }}
      .value {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 10px;
        margin-top: 14px;
      }}
      @media (max-width: 980px) {{
        .value {{ grid-template-columns: 1fr; }}
      }}
      .value-item {{
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 12px 12px;
        background: color-mix(in srgb, var(--paper) 94%, var(--surface));
      }}
      .value-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
      }}
      .value-item b {{
        display: block;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 0;
      }}
      .value-item div {{
        font-size: 13px;
        color: var(--muted);
        line-height: 1.6;
      }}
      .cards {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-top: 14px;
      }}
      @media (max-width: 980px) {{
        .cards {{ grid-template-columns: repeat(2, 1fr); }}
      }}
      @media (max-width: 680px) {{
        .cards {{ grid-template-columns: 1fr; }}
      }}
      .card {{
        border: 1px solid var(--border);
        background: var(--paper);
        border-radius: 14px;
        padding: 14px 14px;
        box-shadow: none;
        cursor: pointer;
        transition: background 120ms ease, border-color 120ms ease;
        min-height: 96px;
      }}
      .card:hover {{
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        border-color: color-mix(in srgb, var(--link) 18%, var(--border));
      }}
      .card .t {{
        font-size: 15px;
        margin: 0 0 6px;
        color: var(--fg);
        font-weight: 650;
      }}
      .card .d {{
        font-size: 13px;
        color: var(--muted);
        margin: 0;
        line-height: 1.6;
      }}
      .section-title {{
        margin: 16px 4px 10px;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 800;
      }}
      .recent {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
      }}
      .recent-item {{
        border: 1px solid var(--border);
        background: var(--paper);
        border-radius: 14px;
        padding: 12px 12px;
        box-shadow: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }}
      .recent-right {{
        display: flex;
        align-items: center;
        gap: 10px;
        flex: none;
      }}
      .recent-del {{
        width: 30px;
        height: 30px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 88%, var(--surface-2));
        color: var(--subtle);
        display: grid;
        place-items: center;
        cursor: pointer;
        user-select: none;
      }}
      .recent-del:hover {{
        border-color: color-mix(in srgb, var(--accent-3) 30%, var(--border));
        background: color-mix(in srgb, var(--accent-3) 14%, var(--paper));
        color: color-mix(in srgb, var(--accent-3) 76%, var(--fg));
      }}
      .recent-del:active {{
        transform: translateY(1px);
      }}
      .recent-left {{
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }}
      .doc-ico {{
        width: 28px;
        height: 28px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        display: grid;
        place-items: center;
        color: var(--subtle);
        flex: none;
      }}
      .doc-ico svg {{
        width: 16px;
        height: 16px;
        stroke: currentColor;
        fill: none;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      .recent-item .name {{
        min-width: 0;
      }}
      .recent-item:hover {{
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        border-color: color-mix(in srgb, var(--link) 14%, var(--border));
      }}
      .recent-item .name {{
        font-size: 13.5px;
        color: var(--fg);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .recent-item .meta {{
        font-size: 12px;
        color: var(--muted);
        margin: 0;
        white-space: nowrap;
      }}
      .view {{
        display: none;
      }}
      .view.show {{
        display: block;
      }}
      /* Keep reader as grid; only library is block */
      .layout.view.show {{
        display: grid;
      }}
      .toc {{
        position: sticky;
        top: 18px;
        align-self: start;
        background: var(--paper);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px 12px 10px;
        box-shadow: var(--shadow);
        z-index: 1;
      }}
      .toc-head {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }}
      .toc h2 {{
        margin: 2px 0 10px 2px;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 700;
      }}
      .toc ul {{
        list-style: none;
        padding: 0;
        margin: 10px 0 0;
        max-height: calc(100vh - 170px);
        overflow: auto;
      }}
      .toc li {{ margin: 2px 0; }}
      .toc a {{
        display: block;
        padding: 7px 10px;
        border-radius: 10px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.3;
        text-decoration: none;
        transition: background 120ms ease, color 120ms ease;
        position: relative;
      }}
      .toc a:hover {{
        background: var(--surface-2);
        color: var(--fg);
        text-decoration: none;
      }}
      .toc a.active {{
        background: var(--sel);
        color: var(--fg);
      }}
      .toc a.active::before {{
        content: "";
        position: absolute;
        left: 6px;
        top: 8px;
        bottom: 8px;
        width: 2px;
        border-radius: 2px;
        background: color-mix(in srgb, var(--link) 70%, transparent);
      }}
      .icon-btn {{
        border: 1px solid var(--border);
        background: transparent;
        color: var(--muted);
        border-radius: 10px;
        padding: 7px 10px;
        cursor: pointer;
        font: inherit;
        font-size: 13px;
        line-height: 1;
      }}
      .icon-btn:hover {{
        background: color-mix(in srgb, var(--paper) 90%, var(--surface));
        color: var(--fg);
      }}
      .layout.collapsed {{
        grid-template-columns: 1fr;
      }}
      .layout.collapsed .toc {{
        display: none;
      }}
      .overlay {{
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.28);
        opacity: 0;
        pointer-events: none;
        transition: opacity 160ms ease;
        z-index: 40;
      }}
      .floating {{
        position: fixed;
        right: 14px;
        bottom: 14px;
        z-index: 60;
        display: flex;
        gap: 10px;
        align-items: center;
      }}
      .fab {{
        border: 1px solid var(--border);
        background: var(--surface);
        color: var(--fg);
        border-radius: 999px;
        padding: 10px 12px;
        box-shadow: var(--shadow);
        cursor: pointer;
        font: inherit;
        font-size: 13px;
        line-height: 1;
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }}
      .fab:hover {{
        background: var(--surface-2);
      }}
      .panel {{
        position: fixed;
        right: 14px;
        bottom: 64px;
        z-index: 70;
        width: min(360px, calc(100vw - 28px));
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 88%, var(--bg));
        border-radius: 16px;
        box-shadow: var(--shadow);
        padding: 12px;
        display: none;
      }}
      .panel.show {{ display: block; }}
      .panel h4 {{
        margin: 4px 6px 10px;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }}
      .row {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        padding: 0 6px 6px;
      }}
      .chip {{
        border: 1px solid var(--border);
        background: transparent;
        color: var(--fg);
        border-radius: 999px;
        padding: 8px 10px;
        cursor: pointer;
        font: inherit;
        font-size: 13px;
        line-height: 1;
      }}
      .chip:hover {{ background: var(--surface-2); }}
      .chip[aria-pressed="true"] {{
        background: var(--sel);
        border-color: color-mix(in srgb, var(--link) 40%, var(--border));
      }}
      .hint {{
        padding: 6px 8px 2px;
        color: var(--subtle);
        font-size: 12px;
        line-height: 1.5;
      }}
      /* Stealth: instant cover + innocuous title/icon */
      body.stealth .doc-inner {{
        filter: blur(10px);
        pointer-events: none;
        user-select: none;
      }}
      body.stealth .toc {{
        filter: blur(10px);
        pointer-events: none;
      }}
      .stealth-cover {{
        position: fixed;
        inset: 0;
        z-index: 999;
        display: none;
        background: linear-gradient(180deg, color-mix(in srgb, var(--bg) 95%, transparent), var(--bg));
      }}
      body.stealth .stealth-cover {{
        display: block;
      }}
      /* Stealth UI: "docs" layout (Feishu-like, generic) */
      .fs-shell {{
        max-width: 1220px;
        margin: 22px auto;
        height: calc(100vh - 44px);
        border: 1px solid var(--border);
        background: var(--paper);
        border-radius: 18px;
        box-shadow: var(--shadow);
        overflow: hidden;
        display: grid;
        grid-template-rows: 48px 1fr;
      }}
      .fs-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 14px;
        border-bottom: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 90%, var(--bg));
      }}
      .fs-exit {{
        margin-left: 8px;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--muted);
        border-radius: 10px;
        padding: 7px 10px;
        font-size: 12.5px;
        cursor: pointer;
      }}
      .fs-exit:hover {{
        background: var(--surface-2);
        color: var(--fg);
      }}
      .fs-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }}
      .fs-logo {{
        width: 20px;
        height: 20px;
        border-radius: 6px;
        background: linear-gradient(135deg, #3b82f6, #60a5fa);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25);
      }}
      .fs-docname {{
        font-size: 13px;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 520px;
      }}
      .fs-actions {{
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .fs-pill {{
        border: 1px solid var(--border);
        background: transparent;
        color: var(--muted);
        border-radius: 999px;
        padding: 7px 10px;
        font-size: 12.5px;
        line-height: 1;
      }}
      .fs-pill.primary {{
        color: #ffffff;
        border-color: transparent;
        background: linear-gradient(135deg, #2563eb, #3b82f6);
      }}
      .fs-avatar {{
        width: 26px;
        height: 26px;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: var(--surface);
        display: grid;
        place-items: center;
        font-size: 12px;
        color: var(--muted);
      }}
      .fs-body {{
        display: grid;
        grid-template-columns: 280px 1fr 260px;
        height: 100%;
      }}
      .fs-left {{
        border-right: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        padding: 12px 10px;
      }}
      .fs-left h5 {{
        margin: 10px 10px 8px;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }}
      .fs-item {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 10px;
        margin: 2px 2px;
        border-radius: 12px;
        color: var(--muted);
        border: 1px solid transparent;
      }}
      .fs-item.active {{
        background: var(--sel);
        color: var(--fg);
        border-color: color-mix(in srgb, var(--link) 32%, var(--border));
      }}
      .fs-ico {{
        width: 18px;
        height: 18px;
        border-radius: 6px;
        border: 1px solid var(--border);
        background: var(--surface);
      }}
      .fs-main {{
        padding: 18px 22px;
        overflow: auto;
      }}
      .fs-breadcrumb {{
        color: var(--subtle);
        font-size: 12.5px;
        margin: 4px 0 10px;
      }}
      .fs-title {{
        font-size: 26px;
        margin: 0 0 8px;
        letter-spacing: -0.01em;
      }}
      .fs-meta {{
        color: var(--muted);
        font-size: 12.5px;
        margin: 0 0 16px;
      }}
      .fs-h2 {{
        font-size: 15px;
        margin: 18px 0 8px;
      }}
      .fs-p {{
        margin: 0 0 10px;
        color: var(--muted);
        font-size: 13.5px;
        line-height: 1.7;
      }}
      .fs-callout {{
        border: 1px solid var(--border);
        background: var(--surface);
        border-radius: 14px;
        padding: 12px 12px;
        margin: 12px 0;
      }}
      .fs-callout b {{
        display: block;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 6px;
      }}
      .fs-table {{
        width: 100%;
        border-collapse: collapse;
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        margin: 10px 0 12px;
      }}
      .fs-table th, .fs-table td {{
        border-bottom: 1px solid var(--border);
        padding: 10px 10px;
        font-size: 12.5px;
        color: var(--muted);
        text-align: left;
      }}
      .fs-table th {{
        color: var(--subtle);
        background: color-mix(in srgb, var(--paper) 86%, var(--surface));
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 11.5px;
      }}
      .fs-check {{
        display: flex;
        gap: 10px;
        align-items: flex-start;
        margin: 8px 0;
        font-size: 13px;
        color: var(--muted);
      }}
      .fs-box {{
        width: 16px;
        height: 16px;
        border-radius: 5px;
        border: 1px solid var(--border);
        background: var(--paper);
        margin-top: 2px;
        flex: none;
      }}
      .fs-right {{
        border-left: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        padding: 12px 12px;
      }}
      .fs-right h5 {{
        margin: 10px 8px 8px;
        font-size: 12px;
        color: var(--subtle);
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }}
      .fs-outline a {{
        display: block;
        padding: 8px 10px;
        border-radius: 10px;
        color: var(--muted);
        text-decoration: none;
        font-size: 12.5px;
      }}
      .fs-outline a:hover {{
        background: var(--surface-2);
        color: var(--fg);
      }}
      .fs-footerhint {{
        margin: 12px 8px 0;
        color: var(--subtle);
        font-size: 12px;
      }}
      @media (max-width: 980px) {{
        .fs-shell {{ border-radius: 0; margin: 0; height: 100vh; }}
        .fs-body {{ grid-template-columns: 240px 1fr; }}
        .fs-right {{ display: none; }}
      }}
      @media (max-width: 720px) {{
        .fs-body {{ grid-template-columns: 1fr; }}
        .fs-left {{ display: none; }}
      }}
      .overlay.show {{
        opacity: 1;
        pointer-events: auto;
      }}
      a {{
        color: var(--link);
        text-decoration: none;
      }}
      a:hover {{ text-decoration: underline; }}
      .doc {{
        background: var(--paper);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 30px 28px 46px;
        box-shadow: var(--shadow);
        position: relative;
        z-index: 0;
      }}
      .doc-inner {{
        max-width: var(--maxw);
        margin: 0 auto;
      }}
      .title {{
        margin: 0 0 8px 0;
        font-size: 32px;
        line-height: 1.2;
        letter-spacing: -0.02em;
      }}
      .meta {{
        margin: 0 0 18px 0;
        color: var(--muted);
        font-size: 14px;
      }}
      .banner {{
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--paper) 92%, var(--surface));
        border-radius: 14px;
        padding: 12px 12px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.6;
        margin: 10px 0 14px;
      }}
      .banner strong {{
        color: var(--fg);
        font-weight: 700;
      }}

      /* PDF upload / parse status (always visible fixed panel) */
      .pdf-task {{
        position: fixed;
        left: 16px;
        right: 16px;
        bottom: 88px;
        z-index: 160;
        max-width: 520px;
        margin: 0 auto;
        pointer-events: auto;
      }}
      .pdf-task[hidden] {{
        display: none !important;
      }}
      .pdf-task-inner {{
        border: 1px solid var(--paper-border);
        border-radius: var(--radius-lg);
        background: color-mix(in srgb, var(--paper-solid) 82%, transparent);
        backdrop-filter: blur(18px) saturate(1.15);
        box-shadow: var(--shadow-sm);
        padding: 14px 14px 12px;
      }}
      .pdf-task-head {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 10px;
      }}
      .pdf-task-badge {{
        font-family: var(--font-mono);
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 999px;
        border: 1px solid color-mix(in srgb, var(--link) 42%, transparent);
        color: var(--link);
        background: color-mix(in srgb, var(--link) 10%, transparent);
        flex: none;
      }}
      .pdf-task-file {{
        font-size: 13px;
        color: var(--muted);
        word-break: break-all;
        line-height: 1.45;
        flex: 1;
        min-width: 0;
      }}
      .pdf-task-dismiss {{
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--surface) 88%, transparent);
        color: var(--fg);
        border-radius: 10px;
        width: 32px;
        height: 32px;
        cursor: pointer;
        font-size: 18px;
        line-height: 1;
        flex: none;
      }}
      .pdf-task-steps {{
        display: grid;
        gap: 6px;
        margin-bottom: 10px;
      }}
      .pdf-task-step {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--subtle);
      }}
      .pdf-task-step .dot {{
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: color-mix(in srgb, var(--border) 85%, transparent);
        border: 1px solid color-mix(in srgb, var(--border) 92%, transparent);
      }}
      .pdf-task-step.done {{
        color: color-mix(in srgb, var(--accent-3) 72%, var(--muted));
      }}
      .pdf-task-step.done .dot {{
        background: color-mix(in srgb, var(--accent-3) 52%, transparent);
        border-color: color-mix(in srgb, var(--accent-3) 58%, transparent);
      }}
      .pdf-task-step.active {{
        color: var(--fg);
        font-weight: 600;
      }}
      .pdf-task-step.active .dot {{
        background: color-mix(in srgb, var(--link) 55%, transparent);
        border-color: color-mix(in srgb, var(--link) 65%, transparent);
        box-shadow: 0 0 0 4px color-mix(in srgb, var(--link) 14%, transparent);
      }}
      .pdf-task-step.err {{
        color: color-mix(in srgb, #fb7185 72%, var(--muted));
      }}
      .pdf-task-bar {{
        height: 8px;
        border-radius: 999px;
        overflow: hidden;
        background: color-mix(in srgb, var(--surface) 92%, transparent);
        border: 1px solid color-mix(in srgb, var(--border) 82%, transparent);
      }}
      .pdf-task-bar-fill {{
        height: 100%;
        width: 0%;
        border-radius: 999px;
        background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 78%, white), color-mix(in srgb, var(--link) 76%, white));
        transition: width 220ms ease;
      }}
      .pdf-task-bar-fill.indeterminate {{
        width: 42% !important;
        animation: pdf-task-pulse 1.2s ease-in-out infinite alternate;
      }}
      @keyframes pdf-task-pulse {{
        0% {{ transform: translateX(-30%); opacity: 0.55; }}
        100% {{ transform: translateX(170%); opacity: 1; }}
      }}
      .pdf-task-detail {{
        margin-top: 8px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        line-height: 1.55;
        word-break: break-word;
      }}
      .h2 {{
        margin: 26px 0 10px;
        font-size: 20px;
        line-height: 1.3;
      }}
      h3.label {{
        margin: 18px 0 8px;
        font-size: 12px;
        color: var(--subtle);
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      p {{
        margin: 0 0 10px 0;
        white-space: pre-wrap;
        font-size: 16px;
        letter-spacing: 0.01em;
      }}
      .spacer {{
        height: 10px;
      }}
      .block {{
        position: relative;
        padding-left: 12px;
        margin-left: -12px;
        border-radius: 10px;
        transition: background 120ms ease;
      }}
      .block:hover {{
        background: var(--surface);
      }}
      /* Notion-like left "handle" hint */
      .block::before {{
        content: "⋮⋮";
        position: absolute;
        left: -4px;
        top: 6px;
        width: 16px;
        height: 18px;
        display: grid;
        place-items: center;
        color: var(--subtle);
        font-size: 12px;
        line-height: 1;
        opacity: 0;
        transform: translateX(-2px);
        transition: opacity 120ms ease, transform 120ms ease;
        user-select: none;
      }}
      .block:hover::before {{
        opacity: 0.9;
        transform: translateX(0);
      }}
      .tools {{
        display: flex;
        gap: 10px;
        align-items: center;
        margin: 6px 0 0;
        flex-wrap: wrap;
      }}
      .btn {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--fg);
        cursor: pointer;
        font: inherit;
        font-size: 14px;
      }}
      .btn:hover {{ background: color-mix(in srgb, var(--paper) 90%, var(--surface)); }}
      .search {{
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px 12px;
        background: transparent;
        color: var(--fg);
        outline: none;
        font-size: 14px;
      }}
      .search:focus {{
        border-color: color-mix(in srgb, var(--link) 45%, var(--border));
        box-shadow: 0 0 0 4px var(--focus);
      }}
      .kbd {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
          "Courier New", monospace;
        border: 1px solid var(--border);
        border-bottom-width: 2px;
        border-radius: 8px;
        padding: 2px 6px;
        font-size: 12px;
        color: var(--muted);
      }}
      mark {{
        background: rgba(250, 204, 21, 0.28);
        color: inherit;
        padding: 0 2px;
        border-radius: 4px;
      }}

      /* Mobile: off-canvas TOC + reading-friendly typography */
      @media (max-width: 900px) {{
        .layout {{
          grid-template-columns: 1fr;
          gap: 14px;
          padding: 14px 12px 20px;
        }}
        .layout::before {{ display: none; }}
        .topbar-inner {{
          padding: 10px 12px;
        }}
        .doc {{
          padding: 22px 18px 30px;
          border-radius: var(--radius);
        }}
        .title {{
          font-size: 26px;
        }}
        p {{
          font-size: 15.5px;
          letter-spacing: 0.008em;
        }}
        .hotkeys {{
          display: block;
        }}

        .toc {{
          position: fixed;
          left: 12px;
          top: 58px;
          bottom: 12px;
          width: min(330px, calc(100vw - 24px));
          max-height: none;
          transform: translateX(calc(-100% - 16px));
          transition: transform 180ms ease;
          z-index: 50;
        }}
        .layout.toc-open .toc {{
          transform: translateX(0);
        }}
        .toc ul {{
          max-height: calc(100vh - 210px);
        }}
        /* On mobile, "collapsed" should not permanently hide TOC */
        .layout.collapsed .toc {{
          display: block;
        }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand">
          <span class="logo" aria-hidden="true"></span>
          <div class="brand-title">{escape_html(product_name)}</div>
        </div>
        <div class="tools">
          <span class="icon-btn file-btn" title="上传 PDF（自动繁转简并排版）">
            上传PDF
            <input id="filePdf" type="file" accept="application/pdf" />
          </span>
          <button class="icon-btn" id="btnToggleToc" type="button" title="折叠/展开目录">目录</button>
          <button class="icon-btn" id="btnDownloadPdfTop" type="button" title="下载（简体PDF/简体TXT）">下载</button>
          <button class="icon-btn" id="btnStealth" type="button" title="一键切换（Esc）">切换</button>
        </div>
      </div>
    </header>

    <div class="pdf-task" id="pdfTask" hidden aria-live="polite" aria-label="PDF 导入进度">
      <div class="pdf-task-inner">
        <div class="pdf-task-head">
          <span class="pdf-task-badge">PDF 导入</span>
          <div class="pdf-task-file" id="pdfTaskFile">—</div>
          <button type="button" class="pdf-task-dismiss" id="pdfTaskDismiss" title="关闭进度">×</button>
        </div>
        <div class="pdf-task-steps" id="pdfTaskSteps"></div>
        <div class="pdf-task-bar" aria-hidden="true">
          <div class="pdf-task-bar-fill" id="pdfTaskBarFill"></div>
        </div>
        <div class="pdf-task-detail" id="pdfTaskDetail"></div>
      </div>
    </div>

    <div class="overlay" id="overlay" aria-hidden="true"></div>
    <div class="stealth-cover" id="stealthCover" aria-hidden="true">
      <div class="fs-shell">
        <div class="fs-top">
          <div class="fs-brand">
            <div class="fs-logo" aria-hidden="true"></div>
            <div class="fs-docname">文档 / 团队空间 / 入职与协作 / 飞书文档使用指南</div>
          </div>
          <div class="fs-actions">
            <span class="fs-pill">只读</span>
            <span class="fs-pill">评论</span>
            <span class="fs-pill primary">共享</span>
            <div class="fs-avatar" title="Me">G</div>
            <button class="fs-exit" id="btnExitStealth" type="button" title="返回阅读（Esc）">返回阅读</button>
          </div>
        </div>
        <div class="fs-body">
          <aside class="fs-left">
            <h5>最近打开</h5>
            <div class="fs-item"><span class="fs-ico" aria-hidden="true"></span> 周会纪要（模板）</div>
            <div class="fs-item"><span class="fs-ico" aria-hidden="true"></span> OKR 对齐 · Q2</div>
            <div class="fs-item active"><span class="fs-ico" aria-hidden="true"></span> 飞书文档使用指南</div>
            <div class="fs-item"><span class="fs-ico" aria-hidden="true"></span> 产品需求评审清单</div>
            <h5>空间</h5>
            <div class="fs-item"><span class="fs-ico" aria-hidden="true"></span> 团队空间</div>
            <div class="fs-item"><span class="fs-ico" aria-hidden="true"></span> 项目资料</div>
          </aside>
          <main class="fs-main">
            <div class="fs-breadcrumb">团队空间 / 入职与协作 / 文档</div>
            <h1 class="fs-title">飞书文档使用指南</h1>
            <div class="fs-meta">最后编辑：刚刚 · 权限：团队可见 · 状态：草稿</div>

            <div class="fs-callout">
              <b>提示</b>
              <div class="fs-p">这是一个只读指南页面。按 <span class="kbd">Shift</span> + <span class="kbd">Esc</span> 可快速返回阅读。</div>
            </div>

            <h2 class="fs-h2" id="fs-sec-1">1. 快速开始</h2>
            <p class="fs-p">- 用标题（H1/H2/H3）组织结构；用清单追踪事项；用表格记录对齐信息。</p>
            <div class="fs-check"><span class="fs-box" aria-hidden="true"></span> 创建文档并设置标题</div>
            <div class="fs-check"><span class="fs-box" aria-hidden="true"></span> 插入目录并检查层级</div>
            <div class="fs-check"><span class="fs-box" aria-hidden="true"></span> 共享给相关同事（只读/可评论）</div>

            <h2 class="fs-h2" id="fs-sec-2">2. 常用快捷操作</h2>
            <table class="fs-table" aria-label="快捷操作">
              <thead>
                <tr><th>场景</th><th>推荐做法</th><th>备注</th></tr>
              </thead>
              <tbody>
                <tr><td>记录会议</td><td>使用模板 + 清单</td><td>会后 10 分钟内同步</td></tr>
                <tr><td>需求对齐</td><td>表格记录范围/风险/Owner</td><td>避免口头信息丢失</td></tr>
                <tr><td>知识沉淀</td><td>章节化 + 目录 + 链接</td><td>便于检索</td></tr>
              </tbody>
            </table>

            <h2 class="fs-h2" id="fs-sec-3">3. 协作规范</h2>
            <p class="fs-p">建议用「评论」提出问题，用「@」指定负责人；修改较大时在顶部摘要区写清楚变更点。</p>
            <div class="fs-callout">
              <b>建议</b>
              <div class="fs-p">文档标题用「主题 + 日期」命名；重要页面固定到空间置顶。</div>
            </div>
          </main>
          <aside class="fs-right">
            <h5>大纲</h5>
            <div class="fs-outline">
              <a href="#fs-sec-1">快速开始</a>
              <a href="#fs-sec-2">常用快捷操作</a>
              <a href="#fs-sec-3">协作规范</a>
            </div>
            <div class="fs-footerhint">Shift + Esc：快速返回阅读</div>
          </aside>
        </div>
      </div>
    </div>

    <!-- Entry GUI (Library) -->
    <section class="library view show" id="viewLibrary">
      <div class="hero">
        <div class="hero-head">
          <div>
            <h1>touchfish</h1>
            <p>把 PDF 变成更好读的简体版：自动繁转简、目录、护眼、摸鱼一键切换。</p>
          </div>
          <div class="hero-actions">
            <button class="primary" id="btnHeroUpload" type="button">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 20h16"/></svg>
              </span>
              上传 PDF
            </button>
            <button class="secondary" id="btnHeroSample" type="button">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"/><path d="M14 2v5h5"/></svg>
              </span>
              打开内置文章
            </button>
            <button class="secondary" id="btnHeroStealth" type="button">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/></svg>
              </span>
              演示摸鱼
            </button>
          </div>
        </div>
        <div class="value">
          <div class="value-item">
            <div class="value-head">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M4 19a2 2 0 0 0 2 2h12"/><path d="M6 17V4a2 2 0 0 1 2-2h10v15H8a2 2 0 0 0-2 2z"/></svg>
              </span>
              <b>阅读体验</b>
            </div>
            <div>沉浸式排版、章节目录、搜索高亮，适合长文阅读。</div>
          </div>
          <div class="value-item">
            <div class="value-head">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>
              </span>
              <b>简体输出</b>
            </div>
            <div>自动繁转简，并支持下载简体 TXT（便于复制到笔记）。</div>
          </div>
          <div class="value-item">
            <div class="value-head">
              <span class="i" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12c.6.5 1 1.2 1 2h6c0-.8.4-1.5 1-2a7 7 0 0 0-4-12z"/></svg>
              </span>
              <b>上班友好</b>
            </div>
            <div><span class="kbd">Esc</span> 一键切换遮罩；<span class="kbd">Alt</span>+<span class="kbd">B</span> 老板键跳转。</div>
          </div>
        </div>
      </div>

      <div class="section-title">最近打开</div>
      <div class="recent" id="recentList"></div>
    </section>

    <!-- Reader -->
    <div class="layout view" id="viewReader">
      <aside class="toc">
        <div class="toc-head">
          <h2>目录</h2>
          <button class="icon-btn" id="btnCollapse" type="button" title="折叠目录">⟨</button>
        </div>
        <input id="q" class="search" placeholder="搜索（回车高亮）  " />
        <div class="tools">
          <button class="btn" id="btnDownloadPdf" type="button">下载简体 PDF</button>
          <span class="kbd">⌘/Ctrl + F</span>
        </div>
        <ul>
          {toc_html}
        </ul>
      </aside>
      <main class="doc" id="doc">
        <div class="doc-inner">
          <h1 class="title" id="docTitle">{escape_html(title)}</h1>
          <p class="meta" id="docMeta">上传任意 PDF → 自动繁转简 → 沉浸式排版阅读。</p>
          <div class="banner" id="runtimeBanner" style="display:none"></div>
          <div id="docBody">
            {body_html}
          </div>
        </div>
      </main>
    </div>
    <div class="floating">
      <button class="fab" id="btnPanel" type="button" title="阅读设置">设置</button>
      <button class="fab" id="btnQuickToggle" type="button" title="一键切换（Esc）">一键切换</button>
    </div>
    <div class="panel" id="panel" role="dialog" aria-label="阅读设置">
      <h4>护眼与显示</h4>
      <div class="row">
        <button class="chip" id="chipEye" type="button" aria-pressed="false">护眼（暖色）</button>
        <button class="chip" id="chipDim" type="button" aria-pressed="false">轻微变暗</button>
      </div>
      <h4>阅读密度</h4>
      <div class="row">
        <button class="chip" id="chipComfort" type="button" aria-pressed="true">舒适</button>
        <button class="chip" id="chipWide" type="button" aria-pressed="false">更宽</button>
      </div>
      <h4>快速切换</h4>
      <div class="row">
        <button class="chip" id="chipStealth" type="button" aria-pressed="false">一键切换（老板键）</button>
      </div>
      <div class="hint">
        老板键跳转（可改）：<br />
        <span class="kbd">Alt</span> + <span class="kbd">B</span> → 打开
        <input id="bossUrl" class="search" style="margin-top:8px" placeholder="https://你的工作页面/Notion/飞书文档" />
        <button class="chip" id="btnSaveBossUrl" type="button" style="margin-top:8px">保存跳转地址</button>
      </div>
      <div class="hint">
        快捷键：<span class="kbd">Esc</span>（一键切换）
        · <span class="kbd">Shift</span> + <span class="kbd">Esc</span>（一键切换）
        · <span class="kbd">Alt</span> + <span class="kbd">\\</span>（目录）
      </div>
    </div>
    <script>
      const samplePdfName = {repr(str(OUT_PDF.name))};
      const sampleTxtName = {repr(str(OUT_TXT.name))};
      const initialText = {repr(full_text_sc)};
      const viewLibrary = document.getElementById('viewLibrary');
      const viewReader = document.getElementById('viewReader');
      const layout = viewReader; // reader root
      const overlay = document.getElementById('overlay');
      const collapseKey = 'scars_preview_toc_collapsed';
      const tocOpenKey = 'scars_preview_toc_open';
      const prefsKey = 'scars_preview_prefs_v1';
      const bossUrlKey = 'scars_preview_boss_url_v1';
      const recentKey = 'scars_preview_recent_v1';
      const panel = document.getElementById('panel');
      const btnPanel = document.getElementById('btnPanel');
      const btnStealth = document.getElementById('btnStealth');
      const btnQuickToggle = document.getElementById('btnQuickToggle');
      const stealthCover = document.getElementById('stealthCover');
      const bossUrlInput = document.getElementById('bossUrl');
      const btnSaveBossUrl = document.getElementById('btnSaveBossUrl');
      const btnExitStealth = document.getElementById('btnExitStealth');
      const filePdf = document.getElementById('filePdf');
      const docTitleEl = document.getElementById('docTitle');
      const docMetaEl = document.getElementById('docMeta');
      const runtimeBannerEl = document.getElementById('runtimeBanner');
      const pdfTask = document.getElementById('pdfTask');
      const pdfTaskFile = document.getElementById('pdfTaskFile');
      const pdfTaskSteps = document.getElementById('pdfTaskSteps');
      const pdfTaskBarFill = document.getElementById('pdfTaskBarFill');
      const pdfTaskDetail = document.getElementById('pdfTaskDetail');
      const pdfTaskDismiss = document.getElementById('pdfTaskDismiss');

      /** pdf.js legacy UMD 挂在 window.pdfjsLib */
      function getPdfJs() {{
        return window.pdfjsLib;
      }}

      const docBodyEl = document.getElementById('docBody');
      const tocListEl = document.querySelector('.toc ul');
      const recentListEl = document.getElementById('recentList');
      const btnHeroUpload = document.getElementById('btnHeroUpload');
      const btnHeroSample = document.getElementById('btnHeroSample');
      const btnHeroStealth = document.getElementById('btnHeroStealth');

      let currentTxtBlobUrl = '';
      function downloadUrl(url, filename) {{
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }}
      function setDownloadMode(mode, filenameHint) {{
        // mode: 'sample' | 'txt'
        const btn = document.getElementById('btnDownloadPdf');
        const btnTop = document.getElementById('btnDownloadPdfTop');
        if (mode === 'sample') {{
          btn.textContent = '下载简体 PDF';
          btnTop.textContent = '下载';
          btn.onclick = () => window.location.href = samplePdfName;
          btnTop.onclick = () => window.location.href = samplePdfName;
          return;
        }}
        btn.textContent = '下载简体 TXT';
        btnTop.textContent = '下载TXT';
        btn.onclick = () => {{
          if (currentTxtBlobUrl) downloadUrl(currentTxtBlobUrl, (filenameHint || 'document') + '_简体.txt');
        }};
        btnTop.onclick = btn.onclick;
      }}
      setDownloadMode('sample');

      const svgFavicon = (bg, fg, text) =>
        'data:image/svg+xml;utf8,' +
        encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
          <rect width="64" height="64" rx="14" fill="${{bg}}"/>
          <text x="32" y="40" font-size="28" text-anchor="middle" fill="${{fg}}" font-family="Arial, sans-serif">${{text}}</text>
        </svg>`);
      function setFavicon(href) {{
        let link = document.querySelector('link[rel="icon"]');
        if (!link) {{
          link = document.createElement('link');
          link.rel = 'icon';
          document.head.appendChild(link);
        }}
        link.href = href;
      }}

      function setCollapsed(v) {{
        layout.classList.toggle('collapsed', v);
        try {{ localStorage.setItem(collapseKey, v ? '1' : '0'); }} catch (_) {{}}
      }}
      function getCollapsed() {{
        try {{ return localStorage.getItem(collapseKey) === '1'; }} catch (_) {{ return false; }}
      }}
      setCollapsed(getCollapsed());

      function setTocOpen(v) {{
        layout.classList.toggle('toc-open', v);
        overlay.classList.toggle('show', v);
        try {{ localStorage.setItem(tocOpenKey, v ? '1' : '0'); }} catch (_) {{}}
      }}
      function getTocOpen() {{
        try {{ return localStorage.getItem(tocOpenKey) === '1'; }} catch (_) {{ return false; }}
      }}

      // Default mobile: TOC closed. Desktop: respect collapsed state.
      const isMobile = window.matchMedia('(max-width: 900px)').matches;
      setTocOpen(isMobile ? false : getTocOpen());

      document.getElementById('btnCollapse').addEventListener('click', () => {{
        if (window.matchMedia('(max-width: 900px)').matches) {{
          setTocOpen(false);
        }} else {{
          setCollapsed(true);
        }}
      }});
      document.getElementById('btnToggleToc').addEventListener('click', () => {{
        if (window.matchMedia('(max-width: 900px)').matches) {{
          setTocOpen(!layout.classList.contains('toc-open'));
        }} else {{
          setCollapsed(!layout.classList.contains('collapsed'));
        }}
      }});
      overlay.addEventListener('click', () => setTocOpen(false));
      window.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape') setTocOpen(false);
      }});

      // Preferences + quick toggles
      const state = {{
        eye: false,
        dim: false,
        density: 'comfort', // comfort|wide
        stealth: false,
      }};
      const titleNormal = document.title;
      const titleStealth = '飞书文档使用指南';

      function loadPrefs() {{
        try {{
          const raw = localStorage.getItem(prefsKey);
          if (!raw) return;
          const obj = JSON.parse(raw);
          if (typeof obj.eye === 'boolean') state.eye = obj.eye;
          if (typeof obj.dim === 'boolean') state.dim = obj.dim;
          if (obj.density === 'comfort' || obj.density === 'wide') state.density = obj.density;
        }} catch (_) {{}}
      }}
      function savePrefs() {{
        try {{
          localStorage.setItem(prefsKey, JSON.stringify({{
            eye: state.eye,
            dim: state.dim,
            density: state.density,
          }}));
        }} catch (_) {{}}
      }}

      function applyState() {{
        document.body.classList.toggle('eye', state.eye);
        document.body.classList.toggle('dim', state.dim);
        document.body.classList.toggle('wide', state.density === 'wide');
        document.body.classList.toggle('comfort', state.density === 'comfort');
        document.body.classList.toggle('stealth', state.stealth);
        stealthCover.setAttribute('aria-hidden', state.stealth ? 'false' : 'true');

        // Chips
        document.getElementById('chipEye').setAttribute('aria-pressed', state.eye ? 'true' : 'false');
        document.getElementById('chipDim').setAttribute('aria-pressed', state.dim ? 'true' : 'false');
        document.getElementById('chipComfort').setAttribute('aria-pressed', state.density === 'comfort' ? 'true' : 'false');
        document.getElementById('chipWide').setAttribute('aria-pressed', state.density === 'wide' ? 'true' : 'false');
        document.getElementById('chipStealth').setAttribute('aria-pressed', state.stealth ? 'true' : 'false');

        // Stealth cosmetics (title + favicon)
        if (state.stealth) {{
          document.title = titleStealth;
          setFavicon(svgFavicon('#2563eb', '#ffffff', 'D'));
        }} else {{
          document.title = titleNormal;
          setFavicon(svgFavicon('#2563eb', '#ffffff', 't'));
        }}
      }}

      function togglePanel() {{
        panel.classList.toggle('show');
      }}
      btnPanel.addEventListener('click', togglePanel);
      document.addEventListener('click', (e) => {{
        const within = panel.contains(e.target) || btnPanel.contains(e.target);
        if (!within) panel.classList.remove('show');
      }});

      function toggleStealth() {{
        state.stealth = !state.stealth;
        applyState();
      }}
      btnStealth.addEventListener('click', toggleStealth);
      btnQuickToggle.addEventListener('click', toggleStealth);
      document.getElementById('chipStealth').addEventListener('click', toggleStealth);
      btnExitStealth.addEventListener('click', () => {{
        if (state.stealth) toggleStealth();
      }});
      document.getElementById('chipEye').addEventListener('click', () => {{
        state.eye = !state.eye;
        savePrefs();
        applyState();
      }});
      document.getElementById('chipDim').addEventListener('click', () => {{
        state.dim = !state.dim;
        savePrefs();
        applyState();
      }});
      document.getElementById('chipComfort').addEventListener('click', () => {{
        state.density = 'comfort';
        savePrefs();
        applyState();
      }});
      document.getElementById('chipWide').addEventListener('click', () => {{
        state.density = 'wide';
        savePrefs();
        applyState();
      }});

      // Keyboard shortcuts
      window.addEventListener('keydown', (e) => {{
        const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
        const isTyping = tag === 'input' || tag === 'textarea';

        // Shift+Esc: always toggle stealth (fast)
        if (e.key === 'Escape' && e.shiftKey) {{
          e.preventDefault();
          toggleStealth();
          return;
        }}
        // Esc: single-key toggle (when not typing). If stealth is on, Esc always returns.
        if (e.key === 'Escape' && !isTyping) {{
          if (state.stealth) {{
            e.preventDefault();
            toggleStealth();
            return;
          }}
          // If panels are open, close them first; otherwise toggle into stealth.
          if (panel.classList.contains('show')) {{
            panel.classList.remove('show');
            return;
          }}
          if (layout.classList.contains('toc-open')) {{
            setTocOpen(false);
            return;
          }}
          // enter stealth
          e.preventDefault();
          toggleStealth();
          return;
        }}
        // Alt+Backslash: toggle TOC (doesn't fight browser Ctrl+F)
        if (e.key === '\\\\' && e.altKey) {{
          e.preventDefault();
          document.getElementById('btnToggleToc').click();
          return;
        }}
        // Alt+E: eye-care
        if ((e.key === 'e' || e.key === 'E') && e.altKey) {{
          e.preventDefault();
          state.eye = !state.eye;
          savePrefs();
          applyState();
          return;
        }}
        // Alt+B: boss key jump (open configured URL)
        if ((e.key === 'b' || e.key === 'B') && e.altKey) {{
          e.preventDefault();
          const url = getBossUrl();
          if (url) window.open(url, '_blank', 'noopener,noreferrer');
          return;
        }}
      }});

      function getBossUrl() {{
        try {{
          return (localStorage.getItem(bossUrlKey) || '').trim();
        }} catch (_) {{
          return '';
        }}
      }}
      function setBossUrl(url) {{
        try {{
          localStorage.setItem(bossUrlKey, (url || '').trim());
        }} catch (_) {{}}
      }}
      bossUrlInput.value = getBossUrl();
      btnSaveBossUrl.addEventListener('click', () => {{
        setBossUrl(bossUrlInput.value);
        panel.classList.remove('show');
      }});

      // Double click blank area: toggle stealth (fast)
      document.addEventListener('dblclick', (e) => {{
        const target = e.target;
        const inControls =
          target.closest('.panel') ||
          target.closest('.toc') ||
          target.closest('.topbar') ||
          target.closest('a') ||
          target.closest('button') ||
          target.closest('input');
        if (inControls) return;
        toggleStealth();
      }});

      // Single click on stealth cover background: return
      stealthCover.addEventListener('click', (e) => {{
        const inside = e.target.closest('.fs-shell');
        if (inside) return;
        if (state.stealth) toggleStealth();
      }});

      loadPrefs();
      applyState();

      // Runtime diagnostics for PDF upload availability
      function showBanner(html) {{
        runtimeBannerEl.innerHTML = html;
        runtimeBannerEl.style.display = 'block';
      }}
      function hideBanner() {{
        runtimeBannerEl.style.display = 'none';
      }}
      if (!getPdfJs()) {{
        showBanner(
          '<strong>上传 PDF 暂不可用。</strong> pdf.js 未能加载（多为脚本 404、广告拦截或离线）。请刷新、检查网络/拦截插件，或稍后再试。'
        );
      }} else {{
        hideBanner();
      }}

      function showLibrary() {{
        viewLibrary.classList.add('show');
        viewReader.classList.remove('show');
      }}
      function showReader() {{
        viewReader.classList.add('show');
        viewLibrary.classList.remove('show');
      }}
      function normalizeViewStateOnRoute() {{
        // When switching views via back/forward, close overlays for a predictable UI.
        try {{ panel.classList.remove('show'); }} catch (_) {{}}
        try {{ setTocOpen(false); }} catch (_) {{}}
      }}

      // --- Lightweight routing (fix: browser Back from reader should return Home instead of leaving/blank) ---
      // We keep URLs stable (static site) and use History entries per view.
      // TOC navigation still uses hashes; Back will first traverse hashes, then restore Home via history state.
      function ensureInitialRoute() {{
        try {{
          const st = history.state || null;
          if (!st || (st.view !== 'library' && st.view !== 'reader')) {{
            history.replaceState({{ view: 'library' }}, '', location.href);
          }}
        }} catch (_) {{}}
      }}
      function navigateLibrary(replace) {{
        normalizeViewStateOnRoute();
        showLibrary();
        try {{
          if (replace) history.replaceState({{ view: 'library' }}, '', location.pathname + location.search);
          else history.pushState({{ view: 'library' }}, '', location.pathname + location.search);
        }} catch (_) {{}}
      }}
      function navigateReader(meta, replace) {{
        normalizeViewStateOnRoute();
        showReader();
        try {{
          const st = {{ view: 'reader' }};
          if (meta && typeof meta === 'object') Object.assign(st, meta);
          // Keep hash as-is for chapter navigation; do not overwrite here.
          if (replace) history.replaceState(st, '', location.href);
          else history.pushState(st, '', location.href);
        }} catch (_) {{}}
      }}
      window.addEventListener('popstate', (e) => {{
        const st = (e && e.state) ? e.state : null;
        if (!st || st.view === 'library') {{
          navigateLibrary(true);
          return;
        }}
        if (st.view === 'reader') {{
          // Best-effort restore for reader view.
          showReader();
          normalizeViewStateOnRoute();
          // If we have an id, try restore from recent cache.
          try {{
            if (st.recentId) {{
              const it = loadRecent().find(x => x && x.id === st.recentId);
              if (it) {{
                makeTxtDownload(it.text || '');
                setDownloadMode('txt', (it.name || 'document'));
                renderText(it.text || '', it.name || 'document.pdf');
              }}
            }}
          }} catch (_) {{}}
        }}
      }});

      function loadRecent() {{
        try {{
          const list = JSON.parse(localStorage.getItem(recentKey) || '[]') || [];
          // Migration: remove any old "(示例)" markers from cached titles
          const cleaned = (Array.isArray(list) ? list : []).map(x => {{
            if (!x) return x;
            const name = sanitizeName(x.name || '');
            return {{ ...x, name }};
          }});
          // Persist if changed
          try {{ localStorage.setItem(recentKey, JSON.stringify(cleaned)); }} catch (_) {{}}
          return cleaned;
        }} catch (_) {{
          return [];
        }}
      }}
      function saveRecent(list) {{
        try {{
          localStorage.setItem(recentKey, JSON.stringify(list));
        }} catch (_) {{}}
      }}
      function addRecent(item) {{
        const list = loadRecent().filter(x => x && x.id !== item.id);
        const safe = {{ ...item, name: sanitizeName(item.name || '') }};
        list.unshift(safe);
        while (list.length > 8) list.pop();
        saveRecent(list);
        renderRecent();
      }}
      function removeRecentById(id) {{
        const list = loadRecent().filter(x => x && x.id !== id);
        saveRecent(list);
        renderRecent();
      }}
      function sanitizeName(name) {{
        return (name || '')
          .replaceAll('（示例）', '')
          .replaceAll('(示例)', '')
          .replaceAll('示例', '')
          .replace(/\\s{2,}/g, ' ')
          .trim();
      }}
      function fmtTime(ts) {{
        try {{
          return new Date(ts).toLocaleString();
        }} catch (_) {{
          return '';
        }}
      }}
      function renderRecent() {{
        const list = loadRecent();
        if (!list.length) {{
          recentListEl.innerHTML = `<div class="hint">还没有记录。你可以先打开内置文章，或上传一份 PDF。</div>`;
          return;
        }}
        recentListEl.innerHTML = list.map(x => `
          <div class="recent-item" data-id="${{escapeHtml(x.id)}}">
            <div class="recent-left">
              <div class="doc-ico" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"/><path d="M14 2v5h5"/></svg>
              </div>
              <div class="name">${{escapeHtml(x.name || '未命名文档')}}</div>
            </div>
            <div class="recent-right">
              <p class="meta">${{escapeHtml(fmtTime(x.ts))}}</p>
              <button class="recent-del" type="button" title="删除" aria-label="删除这条记录" data-del-id="${{escapeHtml(x.id)}}">×</button>
            </div>
          </div>
        `).join('');
        Array.from(recentListEl.querySelectorAll('.recent-del')).forEach(btn => {{
          btn.addEventListener('click', (e) => {{
            e.preventDefault();
            e.stopPropagation();
            const id = btn.getAttribute('data-del-id');
            if (!id) return;
            removeRecentById(id);
          }});
        }});
        Array.from(recentListEl.querySelectorAll('.recent-item')).forEach(el => {{
          el.addEventListener('click', () => {{
            const id = el.getAttribute('data-id');
            const it = loadRecent().find(x => x.id === id);
            if (!it) return;
            makeTxtDownload(it.text || '');
            setDownloadMode('txt', (it.name || 'document'));
            renderText(it.text || '', it.name || 'document.pdf');
            navigateReader({{ recentId: it.id, name: it.name || '' }}, false);
          }});
        }});
      }}

      // Entry actions
      btnHeroSample.addEventListener('click', () => {{
        makeTxtDownload(initialText);
        setDownloadMode('sample');
        renderText(initialText, 'Scars_to_Your_Beautiful.pdf');
        navigateReader({{ recentId: 'builtin-scars', name: 'Scars_to_Your_Beautiful' }}, false);
        addRecent({{
          id: 'builtin-scars',
          name: 'Scars_to_Your_Beautiful',
          text: initialText,
          ts: Date.now(),
        }});
      }});
      btnHeroUpload.addEventListener('click', () => filePdf.click());
      btnHeroStealth.addEventListener('click', () => {{
        if (!state.stealth) toggleStealth();
      }});

      // Default view
      ensureInitialRoute();
      // On refresh: if there's a reader state, keep reader visible; otherwise show home.
      try {{
        const st = history.state || null;
        if (st && st.view === 'reader') showReader();
        else showLibrary();
      }} catch (_) {{
        showLibrary();
      }}
      renderRecent();

      // ---------- PDF upload -> extract -> t2s -> render ----------
      function escapeHtml(s) {{
        return (s || '')
          .replaceAll('&','&amp;')
          .replaceAll('<','&lt;')
          .replaceAll('>','&gt;')
          .replaceAll('"','&quot;')
          .replaceAll("'",'&#39;');
      }}
      function findStartIndex(lines) {{
        for (let i = 0; i < lines.length; i++) {{
          if ((lines[i] || '').trim() === 'Summary') return i;
        }}
        return 0;
      }}

      function normalizeExtractedText(raw) {{
        let t = (raw || '').replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n');
        // Drop page markers like "-- 1 of 304 --"
        t = t.replace(/^--\\s*\\d+\\s+of\\s+\\d+\\s*--\\s*$/gmi, '');
        // Normalize whitespace lines
        t = t.replace(/[ \\t]+\\n/g, '\\n');
        t = t.replace(/\\n{4,}/g, '\\n\\n\\n');
        return t.trim() + '\\n';
      }}

      function smartMergeLines(lines) {{
        // Merge hard line-breaks inside paragraphs (common in exported PDFs)
        const merged = [];
        const isHeading = (s) => /^Chapter\\s+\\d+\\b/i.test(s) || s === 'Summary' || s === '現在' || s === '過去';
        const endsSentence = (s) => /[。！？!?…」』）》\\)]\\s*$/.test(s);
        for (let i = 0; i < lines.length; i++) {{
          let cur = (lines[i] || '').trimEnd();
          if (!cur) {{
            merged.push('');
            continue;
          }}
          cur = cur.trim();
          if (isHeading(cur)) {{
            merged.push(cur);
            continue;
          }}
          if (merged.length && merged[merged.length - 1] && !isHeading(merged[merged.length - 1])) {{
            const prev = merged[merged.length - 1];
            if (!endsSentence(prev)) {{
              merged[merged.length - 1] = prev + cur;
              continue;
            }}
          }}
          merged.push(cur);
        }}
        return merged;
      }}
      function buildTocAndBody(textSc) {{
        const linesAll = smartMergeLines(normalizeExtractedText(textSc).split(/\\n/));
        const start = findStartIndex(linesAll);
        const lines = linesAll.slice(start);

        const toc = [{{ name: start > 0 ? 'Summary' : '开始', id: 'start' }}];
        const body = [`<h2 id="start" class="h2">${{escapeHtml(start > 0 ? 'Summary' : '开始')}}</h2>`];

        const chapterRe = /^Chapter\\s+(\\d+)\\b/i;
        let para = [];
        function flushPara() {{
          if (!para.length) return;
          const txt = para.join('\\n').trim();
          if (txt) body.push(`<div class="block" tabindex="-1"><p>${{escapeHtml(txt)}}</p></div>`);
          para = [];
        }}
        for (let i = 0; i < lines.length; i++) {{
          const raw = lines[i];
          const s = (raw || '').trim();
          if (!s) {{
            flushPara();
            body.push('<div class="spacer"></div>');
            continue;
          }}
          const m = s.match(chapterRe);
          if (m) {{
            flushPara();
            const ch = m[1];
            const anchor = `chapter-${{ch}}`;
            toc.push({{ name: `Chapter ${{ch}}`, id: anchor }});
            body.push(`<h2 id="${{anchor}}" class="h2">Chapter ${{escapeHtml(ch)}}</h2>`);
            continue;
          }}
          if (s === 'Summary' || s === '現在' || s === '过往' || s === '過去') {{
            flushPara();
            if (s === 'Summary') continue;
            body.push(`<h3 class="label">${{escapeHtml(s)}}</h3>`);
            continue;
          }}
          para.push(s);
        }}
        flushPara();
        return {{ toc, bodyHtml: body.join('\\n') }};
      }}
      function renderText(textSc, filename) {{
        showReader();
        const r = buildTocAndBody(textSc);
        // TOC
        tocListEl.innerHTML = r.toc.map(x => `<li><a href="#${{x.id}}">${{escapeHtml(x.name)}}</a></li>`).join('\\n');
        // Body
        docBodyEl.innerHTML = r.bodyHtml;
        docTitleEl.textContent = filename ? filename.replace(/\\.pdf$/i, '') : '文档预览';
        docMetaEl.textContent = '已自动繁转简并重新排版，支持护眼/一键切换。';
        hideBanner();

        // refresh nav bindings after DOM update
        try {{ refreshNav(); }} catch (_) {{}}
      }}

      function countChineseChars(t) {{
        const s = t || '';
        const m = s.match(/[\\u3400-\\u9FFF]/g);
        return m ? m.length : 0;
      }}
      function isProbablyUsefulText(t) {{
        const s = normalizeExtractedText(t);
        const letters = (s.match(/[A-Za-z]/g) || []).length;
        const digits = (s.match(/\\d/g) || []).length;
        const cjk = countChineseChars(s);
        const len = s.replace(/\\s+/g, '').length;
        // Heuristic: scanned PDFs often yield almost nothing useful
        if (len < 120) return false;
        // Latin-heavy PDFs (fanfics / AO3 exports in English): don't force OCR path
        if (cjk < 20 && letters >= 120) return true;
        if (cjk < 40 && letters < 80 && digits < 40) return false;
        return true;
      }}

      const OCR_PAGE_WARN = 80;

      async function loadPdfDocument(file) {{
        const pdfjsLib = getPdfJs();
        if (!pdfjsLib) throw new Error('pdf.js not loaded');
        const ab = await file.arrayBuffer();
        return pdfjsLib.getDocument({{ data: ab }}).promise;
      }}

      async function extractPdfTextFromDoc(pdf, opts) {{
        const maxPages = opts && opts.maxPages ? opts.maxPages : null;
        const end = maxPages ? Math.min(maxPages, pdf.numPages) : pdf.numPages;
        // Layout-aware extraction: rebuild lines by Y coordinate and spacing by X gaps.
        // This improves paragraph structure vs naive item concatenation.
        function isCjk(ch) {{
          if (!ch) return false;
          const code = ch.charCodeAt(0);
          return (
            (code >= 0x3400 && code <= 0x9FFF) || // CJK Unified + Ext A
            (code >= 0xF900 && code <= 0xFAFF)    // CJK Compatibility Ideographs
          );
        }}
        function isAsciiWord(ch) {{
          return /[A-Za-z0-9]/.test(ch || '');
        }}
        function needsSpace(prevChar, nextChar) {{
          if (!prevChar || !nextChar) return false;
          if (isCjk(prevChar) || isCjk(nextChar)) return false;
          return isAsciiWord(prevChar) && isAsciiWord(nextChar);
        }}

        let out = [];
        for (let i = 1; i <= end; i++) {{
          const page = await pdf.getPage(i);
          const content = await page.getTextContent({{
            normalizeWhitespace: true,
            disableCombineTextItems: false,
          }});

          const items = (content && content.items) ? content.items : [];
          const rows = [];
          for (let j = 0; j < items.length; j++) {{
            const it = items[j];
            if (!it || typeof it.str !== 'string') continue;
            const s = it.str;
            if (!s || !s.trim()) continue;
            const tr = it.transform || [];
            const x = typeof tr[4] === 'number' ? tr[4] : 0;
            const y = typeof tr[5] === 'number' ? tr[5] : 0;
            const fontH = typeof it.height === 'number' && it.height > 0 ? it.height : Math.abs(tr[3] || 0) || 10;
            rows.push({{ s, x, y, fontH, hasEOL: !!it.hasEOL }});
          }}

          // pdf.js Y grows upwards; we sort by y desc then x asc.
          rows.sort((a, b) => (b.y - a.y) || (a.x - b.x));

          let lastY = null;
          let lastX = null;
          let lastFontH = 12;
          let line = '';
          let pageText = [];

          function flushLine(forceBlank) {{
            const t = line.trimEnd();
            if (t) pageText.push(t);
            else if (forceBlank) pageText.push('');
            line = '';
            lastX = null;
          }}

          for (let k = 0; k < rows.length; k++) {{
            const r = rows[k];
            const yThreshold = Math.max(2.2, Math.min(6.5, (r.fontH || lastFontH) * 0.55));
            const isNewLine = lastY != null && Math.abs(r.y - lastY) > yThreshold;
            if (isNewLine) {{
              flushLine(false);
            }}

            // Decide whether to insert a space based on X gap and character types.
            if (line && lastX != null) {{
              const xGap = r.x - lastX;
              const prevChar = line.slice(-1);
              const nextChar = r.s.trimStart().charAt(0);
              const gapThreshold = Math.max(6, (r.fontH || lastFontH) * 0.55);
              if (xGap > gapThreshold || needsSpace(prevChar, nextChar)) {{
                if (!line.endsWith(' ')) line += ' ';
              }}
            }}

            // Append text chunk.
            line += r.s.trim();
            lastY = r.y;
            lastFontH = r.fontH || lastFontH;
            // Approximate next expected X by current chunk length; better than nothing.
            lastX = r.x + Math.max(0, (r.s || '').length) * 3.8;

            if (r.hasEOL) {{
              flushLine(false);
            }}
          }}
          flushLine(false);

          // Add an empty line between pages to avoid accidental merges.
          out.push(pageText.join('\\n'));
          out.push('\\n\\n');
        }}
        return out.join('');
      }}

      async function extractPdfText(file, opts) {{
        const pdf = await loadPdfDocument(file);
        return extractPdfTextFromDoc(pdf, opts);
      }}

      async function ocrPdfToTextFromDoc(pdf, onProgress, opts) {{
        if (!window.Tesseract || !Tesseract.recognize) {{
          throw new Error('OCR engine not loaded (tesseract.js)');
        }}
        let maxPages = opts && opts.maxPages ? opts.maxPages : pdf.numPages;
        maxPages = Math.min(maxPages, pdf.numPages);
        const scale = opts && opts.scale ? opts.scale : 1.6;
        let full = [];
        for (let p = 1; p <= maxPages; p++) {{
          if (onProgress) onProgress(p, maxPages);
          const page = await pdf.getPage(p);
          const viewport = page.getViewport({{ scale }});
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d', {{ alpha: false }});
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          await page.render({{ canvasContext: ctx, viewport }}).promise;
          const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
          const {{ data: {{ text }} }} = await Tesseract.recognize(blob, 'chi_tra+chi_sim+eng', {{
            logger: () => {{}},
          }});
          full.push((text || '').trim());
          full.push('\\n');
        }}
        return full.join('\\n');
      }}

      async function ocrPdfToText(file, onProgress, opts) {{
        const pdf = await loadPdfDocument(file);
        return ocrPdfToTextFromDoc(pdf, onProgress, opts);
      }}
      function convertT2S(text) {{
        if (!window.OpenCC) return text;
        try {{
          const converter = OpenCC.Converter({{ from: 'tw', to: 'cn' }});
          return converter(text);
        }} catch (_) {{
          return text;
        }}
      }}
      function makeTxtDownload(textSc) {{
        if (currentTxtBlobUrl) URL.revokeObjectURL(currentTxtBlobUrl);
        const blob = new Blob([textSc], {{ type: 'text/plain;charset=utf-8' }});
        currentTxtBlobUrl = URL.createObjectURL(blob);
      }}

      const PDF_TASK_FLOW = [
        {{ id: 'read', label: '读取文件到浏览器' }},
        {{ id: 'open', label: '用 pdf.js 打开文档' }},
        {{ id: 'text', label: '抽取文本或 OCR 识别' }},
        {{ id: 't2s', label: '繁体 → 简体（OpenCC）' }},
        {{ id: 'layout', label: '排版并更新目录' }},
      ];

      function pdfTaskHide() {{
        try {{ pdfTask.setAttribute('hidden', ''); }} catch (_) {{}}
      }}

      function pdfTaskShow(filename) {{
        pdfTask.removeAttribute('hidden');
        pdfTaskFile.textContent = filename || 'document.pdf';
        pdfTaskRenderSteps('read');
        pdfTaskSetProgress(6, true, '准备解析…');
      }}

      function pdfTaskRenderSteps(activeId) {{
        const activeIndex =
          activeId === '__all_done__'
            ? PDF_TASK_FLOW.length
            : PDF_TASK_FLOW.findIndex((x) => x.id === activeId);
        pdfTaskSteps.innerHTML = PDF_TASK_FLOW.map((s, i) => {{
          let cls = 'pdf-task-step';
          if (activeIndex >= 0) {{
            if (i < activeIndex) cls += ' done';
            else if (i === activeIndex) cls += ' active';
          }}
          return `<div class="${{cls}}"><span class="dot" aria-hidden="true"></span><span>${{escapeHtml(s.label)}}</span></div>`;
        }}).join('');
      }}

      function pdfTaskSetProgress(pct, indeterminate, detail) {{
        if (!pdfTaskBarFill) return;
        pdfTaskBarFill.classList.toggle('indeterminate', !!indeterminate);
        if (indeterminate) {{
          pdfTaskBarFill.style.width = '100%';
        }} else {{
          pdfTaskBarFill.style.width = Math.max(0, Math.min(100, pct)) + '%';
        }}
        if (pdfTaskDetail && detail != null) pdfTaskDetail.textContent = detail || '';
      }}

      function pdfTaskFail(msg) {{
        pdfTaskSetProgress(0, false, '');
        const rows = PDF_TASK_FLOW.map((s) => {{
          return `<div class="pdf-task-step err"><span class="dot"></span><span>${{escapeHtml(s.label)}}</span></div>`;
        }}).join('');
        pdfTaskSteps.innerHTML = rows;
        if (pdfTaskDetail) pdfTaskDetail.textContent = msg || '未知错误';
      }}

      try {{
        pdfTaskDismiss.addEventListener('click', pdfTaskHide);
      }} catch (_) {{}}

      filePdf.addEventListener('change', async () => {{
        const f = filePdf.files && filePdf.files[0];
        if (!f) return;

        showReader();
        panel.classList.remove('show');
        setTocOpen(false);
        docMetaEl.textContent = '正在解析 PDF…';

        pdfTaskShow(f.name);
        if (getPdfJs()) hideBanner();

        const mb = (f.size / 1024 / 1024).toFixed(2);
        pdfTaskRenderSteps('read');
        pdfTaskSetProgress(10, false, `已选择文件 · 约 ${{mb}} MB`);

        try {{
          if (!getPdfJs()) {{
            throw new Error('pdf.js 未加载（CDN 可能被拦截）。请刷新页面或检查网络。');
          }}

          pdfTaskRenderSteps('open');
          pdfTaskSetProgress(22, true, '载入 pdf.js 工作线程…');
          const pdf = await loadPdfDocument(f);

          pdfTaskSetProgress(34, false, `文档共 ${{pdf.numPages}} 页 · 快速检测可复制文本…`);

          // Fast path: extract first pages to decide if this is a text PDF or a scan
          pdfTaskRenderSteps('text');
          pdfTaskSetProgress(38, true, '抽取前 5 页用于质量判断…');
          const preview = await extractPdfTextFromDoc(pdf, {{ maxPages: 5 }});
          let raw = preview;

          async function runOcrForPdf(pdfDoc) {{
            let ocrMax = pdfDoc.numPages;
            if (pdfDoc.numPages > OCR_PAGE_WARN) {{
              pdfTaskSetProgress(42, false, `共 ${{pdfDoc.numPages}} 页 · 等待你选择 OCR 范围…`);
              const ok = window.confirm(
                `该 PDF 共 ${{pdfDoc.numPages}} 页，本地 OCR 可能较慢（取决于设备）。\\n\\n` +
                  `点「确定」尝试识别全部页面；点「取消」仅识别前 ${{OCR_PAGE_WARN}} 页（更快）。`
              );
              if (!ok) ocrMax = OCR_PAGE_WARN;
            }}
            showBanner(
              '<strong>检测到扫描版/图片 PDF。</strong> 正在本地 OCR（浏览器内处理，不上传服务器）。'
            );
            docMetaEl.textContent = '正在 OCR 识别（扫描版 PDF）…';
            pdfTaskRenderSteps('text');
            raw = await ocrPdfToTextFromDoc(
              pdfDoc,
              (cur, total) => {{
                const p = 42 + Math.floor((cur / Math.max(1, total)) * 40);
                pdfTaskSetProgress(p, false, `OCR：第 ${{cur}} / ${{total}} 页`);
                docMetaEl.textContent = `正在 OCR：${{cur}} / ${{total}} 页`;
              }},
              {{ maxPages: ocrMax }}
            );
          }}

          if (!isProbablyUsefulText(preview)) {{
            await runOcrForPdf(pdf);
          }} else {{
            pdfTaskSetProgress(52, true, '抽取全文（可复制文本 PDF）…');
            docMetaEl.textContent = '正在抽取全文…';
            raw = await extractPdfTextFromDoc(pdf);
            const norm = normalizeExtractedText(raw);
            if (!isProbablyUsefulText(norm)) {{
              await runOcrForPdf(pdf);
            }}
          }}

          pdfTaskRenderSteps('t2s');
          pdfTaskSetProgress(84, true, 'OpenCC：繁体 → 简体…');
          const sc = convertT2S(normalizeExtractedText(raw));
          if (!isProbablyUsefulText(sc)) {{
            throw new Error(
              '抽取到的文本过少：可能是加密 PDF、扫描质量过低，或刚才选择了部分页 OCR。'
            );
          }}

          pdfTaskRenderSteps('layout');
          pdfTaskSetProgress(93, false, '写入正文、目录与下载缓存…');
          makeTxtDownload(sc);
          setDownloadMode('txt', f.name.replace(/\\.pdf$/i, ''));
          renderText(sc, f.name);
          const recentId = 'pdf-' + Date.now();
          navigateReader({{ recentId, name: f.name || '' }}, false);

          pdfTaskRenderSteps('__all_done__');
          pdfTaskSetProgress(100, false, '完成 · 可在左侧目录跳转，或使用下载 TXT');
          docMetaEl.textContent = '解析完成 · 已自动繁转简并重新排版。';

          addRecent({{
            id: recentId,
            name: f.name,
            text: sc,
            ts: Date.now(),
          }});
        }} catch (err) {{
          const msg = (err && err.message) ? err.message : String(err || '');
          docMetaEl.textContent = '解析失败：请换一份可复制文本的 PDF。' + (msg ? ('（' + msg + '）') : '');
          showBanner('<strong>上传 PDF 失败。</strong> ' + escapeHtml(msg || '未知错误') + '。');
          pdfTaskFail(msg || '未知错误');
        }} finally {{
          try {{ filePdf.value = ''; }} catch (_) {{}}
        }}
      }});

      // Simple highlight + active TOC (supports re-render)
      const q = document.getElementById('q');
      const doc = document.getElementById('doc');
      let io = null;
      function refreshNav() {{
        if (io) io.disconnect();
        const tocLinks = Array.from(document.querySelectorAll('.toc a'));
        const headings = Array.from(doc.querySelectorAll('h2[id]'));

        io = new IntersectionObserver((entries) => {{
          const visible = entries
            .filter(e => e.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
          if (!visible) return;
          const id = visible.target.id;
          let activeLink = null;
          tocLinks.forEach(a => {{
            const isActive = a.getAttribute('href') === '#' + id;
            a.classList.toggle('active', isActive);
            if (isActive) activeLink = a;
          }});
          if (activeLink && !layout.classList.contains('collapsed') && !window.matchMedia('(max-width: 900px)').matches) {{
            try {{ activeLink.scrollIntoView({{ block: 'nearest' }}); }} catch (_) {{}}
          }}
        }}, {{ rootMargin: '-20% 0px -72% 0px', threshold: [0.15, 0.35, 0.55] }});
        headings.forEach(h => io.observe(h));

        // On mobile: tapping a TOC item closes drawer
        tocLinks.forEach(a => {{
          a.addEventListener('click', () => {{
            if (window.matchMedia('(max-width: 900px)').matches) setTocOpen(false);
          }});
        }});
      }}
      refreshNav();

      function clearMarks() {{
        doc.querySelectorAll('mark').forEach(m => {{
          const t = document.createTextNode(m.textContent);
          m.replaceWith(t);
        }});
      }}
      function highlight(term) {{
        if (!term) return;
        const walker = document.createTreeWalker(doc, NodeFilter.SHOW_TEXT, null);
        const texts = [];
        while (walker.nextNode()) texts.push(walker.currentNode);
        for (const node of texts) {{
          const v = node.nodeValue;
          let idx = v.indexOf(term);
          if (idx === -1) continue;
          const frag = document.createDocumentFragment();
          let last = 0;
          while (idx !== -1) {{
            frag.appendChild(document.createTextNode(v.slice(last, idx)));
            const mark = document.createElement('mark');
            mark.textContent = v.slice(idx, idx + term.length);
            frag.appendChild(mark);
            last = idx + term.length;
            idx = v.indexOf(term, last);
          }}
          frag.appendChild(document.createTextNode(v.slice(last)));
          node.parentNode.replaceChild(frag, node);
        }}
      }}
      q.addEventListener('keydown', (e) => {{
        if (e.key !== 'Enter') return;
        clearMarks();
        highlight(q.value.trim());
      }});
    </script>
  </body>
</html>
"""


def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def build_pdf(title: str, full_text_sc: str, out_path: Path) -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "BaseCN",
        parent=styles["Normal"],
        fontName="STSong-Light",
        fontSize=11.2,
        leading=18,
        spaceAfter=8,
    )
    h1 = ParagraphStyle(
        "H1CN",
        parent=base,
        fontSize=20,
        leading=28,
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2CN",
        parent=base,
        fontSize=14,
        leading=20,
        spaceBefore=10,
        spaceAfter=10,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=48,
        bottomMargin=48,
        title=title,
        author="Converted by script",
    )

    story = [Paragraph(escape_html(title), h1)]
    story.append(Paragraph("（繁体已转换为简体；内容为重新排版文本版）", base))
    story.append(Spacer(1, 12))

    chapter_re = re.compile(r"^Chapter\s+(\d+)\b", re.IGNORECASE)
    page_marker_re = re.compile(r"^--\s*\d+\s+of\s+\d+\s*--\s*$")

    lines_all = full_text_sc.splitlines()
    start_idx = 0
    for i, ln in enumerate(lines_all):
        if ln.strip() == "Summary":
            start_idx = i
            break
    for raw_line in lines_all[start_idx:]:
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 8))
            continue
        if page_marker_re.match(line):
            continue
        m = chapter_re.match(line)
        if m:
            story.append(PageBreak())
            story.append(Paragraph(escape_html(f"Chapter {m.group(1)}"), h2))
            continue
        if line in {"Summary", "現在", "過去"}:
            story.append(Paragraph(escape_html(line), h2))
            continue
        story.append(Paragraph(escape_html(line), base))

    doc.build(story)


def main() -> None:
    if not INPUT_PDF.exists():
        raise SystemExit(f"Input PDF not found: {INPUT_PDF}")

    pages = extract_text_pymupdf(INPUT_PDF)
    full_text = normalize_text("\n\n".join(pages))

    cc = OpenCC("t2s")
    full_text_sc = cc.convert(full_text)

    OUT_TXT.write_text(full_text_sc, encoding="utf-8")

    title = "Scars to Your Beautiful（简体）"
    OUT_HTML.write_text(build_notion_like_html(title, full_text_sc), encoding="utf-8")

    build_pdf(title, full_text_sc, OUT_PDF)

    print("Done.")
    print(f"- TXT:  {OUT_TXT}")
    print(f"- HTML: {OUT_HTML}")
    print(f"- PDF:  {OUT_PDF}")


if __name__ == "__main__":
    main()

