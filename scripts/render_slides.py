import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "slide.html"
CALENDAR_PATH = ROOT / "content" / "calendar.json"
EXPORT_DIR = ROOT / "exports"

COLOR_VARS = {
    "green": "#12E068",
    "mint": "#2CF982",
    "mintlight": "#5CFFA1",
}


def wordmark_html():
    return (
        '<div class="wordmark">'
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
    if body_type == "rows":
        rows = "\n".join(
            f'<div class="row"><div class="label">{r["label"]}'
            + (f'<span class="meta">{r["meta"]}</span>' if r.get("meta") else "")
            + f'</div><div class="value">{r["value"]}</div></div>'
            for r in slide["rows"]
        )
        body = f'<div class="rows">{rows}</div>'
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


def side_label_html(slide):
    return f'<div class="side-label">MYTH <b>vs</b> FACT &nbsp;&middot;&nbsp; {slide["pager"]}</div>'


def render_myth_cover(slide):
    return f"""
    {side_label_html(slide)}
    {wordmark_html()}
    <div class="cover-bottom">
      <div class="headline" style="font-size:92px;">{slide['headline']}</div>
      <div class="sub">{slide.get('sub', '')}</div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">swipe &#8594;</div>
    </div>
    """


def render_myth(slide):
    return f"""
    {side_label_html(slide)}
    {wordmark_html()}
    <div class="split">
      <div class="half myth-half">
        <div class="tag myth">MYTH</div>
        <div class="myth-text">{slide['myth']}</div>
      </div>
      <div class="half fact-half">
        <div class="tag fact">FACT</div>
        <div class="fact-text">{slide['fact']}</div>
        <div class="fact-detail">{slide.get('detail', '')}</div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


def render_step_cover(slide):
    return f"""
    <div class="giant-num step-cover-num">{slide['big_number']}</div>
    {wordmark_html()}
    <div class="cover-bottom">
      <div class="headline" style="font-size:88px;">{slide['headline']}</div>
      <div class="sub">{slide.get('sub', '')}</div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">swipe &#8594;</div>
    </div>
    """


def render_step(slide):
    return f"""
    <div class="topbar">{wordmark_html()}<div class="pager">{slide['pager']}</div></div>
    <div class="step-row">
      <div class="giant-num">{slide['number']}</div>
      <div class="step-body">
        <div class="step-kicker">STEP {slide['number']}</div>
        <div class="step-title">{slide['title']}</div>
        <div class="step-desc">{slide['desc']}</div>
        <div class="pill">{slide['pill']}</div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


def render_plan_cover(slide):
    return f"""
    {wordmark_html()}
    <div class="price-sticker">
      <div class="from">FROM</div>
      <div class="amt">{slide['sticker_amount']}</div>
      <div class="note">{slide['sticker_note']}</div>
    </div>
    <div class="center-title">
      <div class="headline">{slide['headline']}</div>
      <div class="sub" style="max-width:80%;">{slide.get('sub', '')}</div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">swipe &#8594;</div>
    </div>
    """


def render_plan(slide):
    specs = "".join(
        f'<div class="spec"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in slide["specs"]
    )
    flag = f'<div class="plan-flag">{slide["flag"]}</div>' if slide.get("flag") else ""
    featured = " featured" if slide.get("flag") else ""
    return f"""
    <div class="topbar">{wordmark_html()}<div class="pager">{slide['pager']}</div></div>
    <div class="grow" style="gap:34px;">
      <div class="plan-accounts"><span class="n">{slide['accounts']}</span><span class="t">trading<br>accounts</span></div>
      <div class="plan-card{featured}">
        <div class="plan-head"><div class="plan-name">{slide['plan_name']}</div>{flag}</div>
        <div class="spec-grid">{specs}</div>
        <div class="plan-price"><span class="amt">{slide['price']}</span><span class="per">/mo</span></div>
        <div class="plan-fine">{slide['fine_print']}</div>
      </div>
    </div>
    <div class="footer-row">
      <div class="footer-url">marginvps.com</div>
      <div class="footer-url">{slide['pager']}</div>
    </div>
    """


RENDERERS = {
    "cover": render_cover,
    "content": render_content,
    "stat": render_stat,
    "testimonial": render_testimonial,
    "cta": render_cta,
    "myth_cover": render_myth_cover,
    "myth": render_myth,
    "step_cover": render_step_cover,
    "step": render_step,
    "plan_cover": render_plan_cover,
    "plan": render_plan,
}
SIDE_LABEL_KINDS = {"myth_cover", "myth"}


def badge_color_hex(slide):
    key = slide.get("badge_color", "mintlight")
    return COLOR_VARS.get(key, COLOR_VARS["mintlight"])


def build_slide_html(template_src, slide):
    inner = RENDERERS[slide["kind"]](slide)
    color = badge_color_hex(slide)
    frame_class = "frame side" if slide["kind"] in SIDE_LABEL_KINDS else "frame"
    html = template_src.replace(
        '<div class="frame" id="frame"></div>',
        f'<div class="{frame_class}" id="frame" style="--badge-color:{color};">{inner}</div>',
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
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(250)
        jpg_path = EXPORT_DIR / f"{day_id}_slide{idx}.jpg"
        page.screenshot(path=str(jpg_path), type="jpeg", quality=92)
        out_paths.append(jpg_path)
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
