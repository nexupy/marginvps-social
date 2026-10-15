import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "slide.html"
CALENDAR_PATH = ROOT / "content" / "calendar.json"
EXPORT_DIR = ROOT / "exports"

COLOR_VARS = {
    "cyan": "#38BDF8",
    "amber": "#FB923C",
    "green": "#4ADE80",
}


def wordmark_html():
    return (
        '<div class="wordmark">'
        '<span class="prompt">&gt;_</span>'
        '<span class="margin">Margin</span><span class="vps">VPS</span>'
        "</div>"
    )


def badge_html(label):
    return (
        '<div class="badge"><span class="dot"></span>' + label + "</div>"
    )


def topbar_html(label, pager):
    return (
        '<div class="topbar">'
        + badge_html(label)
        + '<div class="pager">' + pager + "</div>"
        + "</div>"
    )


def render_cover(slide):
    return f"""
    {wordmark_html()}
    <div class="grow">
      {topbar_html(slide['pillar_label'], slide['pager'])}
      <div class="stack">
        <div class="headline">{slide['headline']}</div>
        <div class="sub">{slide.get('sub', '')}</div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">swipe &#8594;</div>
    </div>
    """


def render_content(slide):
    body_type = slide.get("body_type", "list")
    if body_type == "terminal":
        lines = "\n".join(
            f'<div>{line}</div>' if line else "<div>&nbsp;</div>"
            for line in slide["terminal_lines"]
        )
        body = f"""
        <div class="terminal">
          <div class="bar"><span></span><span></span><span></span></div>
          <div class="body">{lines}</div>
        </div>
        """
    else:
        items = "\n".join(
            f'<div class="list-item"><span class="num">{i+1:02d}</span><span>{item}</span></div>'
            for i, item in enumerate(slide["list_items"])
        )
        body = f'<div class="list">{items}</div>'

    return f"""
    {topbar_html(slide['pillar_label'], slide['pager'])}
    <div class="grow">
      <div class="headline" style="font-size:60px;">{slide['headline']}</div>
      {body}
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


def render_stat(slide):
    return f"""
    {topbar_html(slide['pillar_label'], slide['pager'])}
    <div class="grow">
      <div class="stat-wrap">
        <div class="stat-number">{slide['stat_number']}</div>
        <div class="stat-label">{slide['stat_label']}</div>
        <div class="stat-context">{slide.get('stat_context', '')}</div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


def render_testimonial(slide):
    initials = slide.get("initials", "C")
    return f"""
    {topbar_html('CUSTOMER STORY', slide['pager'])}
    <div class="grow">
      <div class="quote-mark">&ldquo;</div>
      <div class="quote-text">{slide['quote_text']}</div>
      <div class="attribution">
        <div class="avatar">{initials}</div>
        <div>
          <div class="name">{slide['name']}</div>
          <div class="role">{slide['role']}</div>
        </div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


def render_cta(slide):
    return f"""
    <div class="cta-wrap">
      {wordmark_html()}
      <div class="cta-tagline">{slide['tagline']}</div>
      <div class="cta-button">{slide['button_text']}</div>
      <div class="cta-url">{slide['url']}</div>
    </div>
    """


RENDERERS = {
    "cover": render_cover,
    "content": render_content,
    "stat": render_stat,
    "testimonial": render_testimonial,
    "cta": render_cta,
}


def badge_color_hex(slide):
    key = slide.get("badge_color", "cyan")
    return COLOR_VARS.get(key, COLOR_VARS["cyan"])


def build_slide_html(template_src, slide):
    inner = RENDERERS[slide["kind"]](slide)
    color = badge_color_hex(slide)
    html = template_src.replace(
        '<div class="frame" id="frame"></div>',
        f'<div class="frame" id="frame" style="--badge-color:{color};">{inner}</div>',
    )
    return html


def render_day(day, template_src, browser):
    day_id = day["id"]
    out_paths = []
    page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
    for idx, slide in enumerate(day["slides"], start=1):
        html = build_slide_html(template_src, slide)
        html_path = EXPORT_DIR / f"{day_id}_slide{idx}.html"
        html_path.write_text(html, encoding="utf-8")
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(250)
        png_path = EXPORT_DIR / f"{day_id}_slide{idx}.png"
        page.screenshot(path=str(png_path))
        out_paths.append(png_path)
    page.close()
    return out_paths


def main():
    only_days = sys.argv[1:] if len(sys.argv) > 1 else None
    template_src = TEMPLATE_PATH.read_text(encoding="utf-8")
    calendar = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    EXPORT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for day in calendar["days"]:
            if not day.get("render"):
                continue
            if only_days and day["id"] not in only_days:
                continue
            print(f"Rendering {day['id']} ({day['topic']})...")
            paths = render_day(day, template_src, browser)
            for path in paths:
                print("  ->", path)
        browser.close()


if __name__ == "__main__":
    main()
