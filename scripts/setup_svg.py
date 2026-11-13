"""Draw the setup as an SVG: main session on top, one card per agent, infrastructure cards below.

render(main, agents, infra) -> svg text. Cards size to their content; no connector spaghetti.
"""
from xml.sax.saxutils import escape

W, M, GAP, COLS = 1200, 24, 16, 4
CARD_W = (W - 2 * M - (COLS - 1) * GAP) // COLS
LINE, HEAD = 18, 52
MODEL_COLOR = {"opus": "#7c3aed", "sonnet": "#2563eb", "haiku": "#059669"}


def wrap(text, width=36):
    out, line = [], ""
    for word in text.split(" "):
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = "  " + word
        else:
            line = f"{line} {word}".strip() if line else word
    return out + [line] if line else out


def text(x, y, s, size=13, color="#334155", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'font-family="Segoe UI, sans-serif">{escape(s)}</text>')


def card(x, y, title, badge, rows, height, accent="#64748b", dashed=False):
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    parts = [f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{height}" rx="10" fill="#ffffff" '
             f'stroke="{accent}" stroke-width="1.5"{dash}/>',
             f'<rect x="{x}" y="{y}" width="{CARD_W}" height="6" rx="3" fill="{accent}"/>',
             text(x + 14, y + 30, title, 16, "#0f172a", "600")]
    if badge:
        parts.append(f'<rect x="{x + CARD_W - 74}" y="{y + 15}" width="60" height="22" rx="11" fill="{accent}"/>')
        parts.append(f'<text x="{x + CARD_W - 44}" y="{y + 31}" font-size="12" fill="#fff" text-anchor="middle" '
                     f'font-family="Segoe UI, sans-serif">{escape(badge)}</text>')
    cy = y + HEAD
    for row, color in rows:
        for line in wrap(row):
            parts.append(text(x + 14, cy, line, 13, color))
            cy += LINE
    return parts


def rows_height(rows):
    return HEAD + sum(len(wrap(r)) for r, _ in rows) * LINE + 10


def grid(items, y):
    """items: (title, badge, rows, accent, dashed). Lays them out COLS per row; returns parts, next y."""
    parts = []
    for start in range(0, len(items), COLS):
        chunk = items[start:start + COLS]
        h = max(rows_height(rows) for _, _, rows, _, _ in chunk)
        for i, (title, badge, rows, accent, dashed) in enumerate(chunk):
            parts += card(M + i * (CARD_W + GAP), y, title, badge, rows, h, accent, dashed)
        y += h + GAP
    return parts, y


def section(y, label):
    return [text(M, y + 18, label.upper(), 12, "#64748b", "600"),
            f'<line x1="{M + 10 + len(label) * 8}" y1="{y + 14}" x2="{W - M}" y2="{y + 14}" stroke="#e2e8f0"/>'], y + 30


def render(main, agents, infra):
    parts = [f'<rect x="{M}" y="{M}" width="{W - 2 * M}" height="74" rx="12" fill="#0f172a"/>',
             text(M + 20, M + 32, f"Main session — orchestrator + planner · {main['model']}", 18, "#fff", "600"),
             text(M + 20, M + 56, main["detail"], 13, "#cbd5e1")]
    head, y = section(M + 90, "Agents — the main session delegates to")
    parts += head
    body, y = grid([(name, model, [(s, "#334155") for s in skills] + [(f"MCP: {m}", "#9333ea") for m in mcp],
                     MODEL_COLOR.get(model, "#64748b"), status == "draft")
                    for name, model, skills, status, mcp in agents], y)
    parts += body
    head, y = section(y, "Infrastructure")
    parts += head
    body, y = grid([(title, None, rows, "#64748b", any(c == "#dc2626" for _, c in rows))
                    for title, rows in infra], y)
    parts += body
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{y + M}" viewBox="0 0 {W} {y + M}">'
            f'<rect width="100%" height="100%" fill="#f8fafc"/>{"".join(parts)}</svg>')
