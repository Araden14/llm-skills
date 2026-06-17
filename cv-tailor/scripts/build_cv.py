#!/usr/bin/env python3
"""Render a CV YAML (JSON Resume-style schema) to a clean one-page PDF.

This module is the SINGLE SOURCE OF TRUTH for the CV layout. The TEMPLATE below
is used both for the final PDF (here) and for the on-screen HTML preview
(render_preview.py imports `render_html`), so the preview can never drift from
the printed result.

Section headers are localized FR/EN: pass `--lang fr|en`, or let it auto-detect
from the content.

Usage: python3 build_cv.py [input.yaml] [output.pdf] [--lang fr|en]
Defaults: resume.yaml -> resume.pdf (next to this script).
"""
from __future__ import annotations

import json
import re
import sys
from functools import partial
from pathlib import Path
from urllib.parse import quote

import yaml
from jinja2 import Environment, BaseLoader

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"

LABELS = {
    "en": {
        "profile": "Profile", "experience": "Experience", "projects": "Projects",
        "skills": "Skills", "education": "Education", "languages": "Languages",
        "references": "References", "present": "Present",
    },
    "fr": {
        "profile": "Profil", "experience": "Expérience", "projects": "Projets",
        "skills": "Compétences", "education": "Formation", "languages": "Langues",
        "references": "Références", "present": "Aujourd'hui",
    },
}

TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ basics.name }} — CV</title>
<style>
  @page {
    size: A4;
    margin: 11mm 14mm;
  }
  * { box-sizing: border-box; }
  html, body {
    font-family: "Helvetica Neue", "Helvetica", "Arial", sans-serif;
    font-size: {{ fs(9.1) }};
    line-height: 1.32;
    color: #1f2937;
    margin: 0;
  }

  /* Header */
  .header {
    margin-bottom: 4.5mm;
    display: flex;
    align-items: center;
    gap: 6mm;
  }
  .header .photo {
    width: 24mm;
    height: 24mm;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    border: 0.5pt solid #e5e7eb;
  }
  .header-text { flex: 1; min-width: 0; }
  .name {
    font-size: {{ fs(19) }};
    font-weight: 700;
    letter-spacing: -0.3px;
    color: #0f172a;
    margin: 0 0 0.5mm 0;
  }
  .label {
    font-size: {{ fs(10) }};
    color: #475569;
    margin: 0 0 1.5mm 0;
  }
  .contact {
    font-size: {{ fs(8.6) }};
    color: #475569;
  }
  .profiles-line { margin-top: 0.8mm; }
  .contact span + span::before {
    content: "·";
    margin: 0 6px;
    color: #cbd5e1;
  }
  .contact a { color: inherit; text-decoration: none; }

  /* Section grid */
  .section {
    display: grid;
    grid-template-columns: 26mm 1fr;
    gap: 5mm;
    padding: 1.4mm 0;
    border-top: 0.4pt solid #e5e7eb;
    break-inside: avoid;
  }
  .section:first-of-type { border-top: 0; padding-top: 0; }
  .section-title {
    font-size: {{ fs(8.1) }};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.1px;
    color: #2563eb;
    padding-top: 0.5mm;
  }
  .section-body > * + * { margin-top: 2mm; }

  /* Entry (work, project, education) */
  .entry { break-inside: avoid; }
  .entry-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8mm;
    margin-bottom: 0.4mm;
  }
  .entry-title {
    font-size: {{ fs(9.6) }};
    font-weight: 700;
    color: #0f172a;
  }
  .entry-meta {
    font-size: {{ fs(8.3) }};
    color: #64748b;
    white-space: nowrap;
  }
  .entry-sub {
    font-size: {{ fs(8.8) }};
    color: #334155;
    margin-bottom: 0.8mm;
  }
  .entry-sub .dot { color: #cbd5e1; margin: 0 5px; }
  .entry ul {
    margin: 0.6mm 0 0 0;
    padding-left: 4mm;
  }
  .entry ul li {
    margin: 0.3mm 0;
  }
  .entry-link {
    font-size: {{ fs(8.1) }};
    color: #2563eb;
    text-decoration: none;
    display: inline-block;
  }

  /* Summary */
  .summary { color: #334155; }

  /* Skills */
  .skills {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 4mm;
  }
  .skill-group .skill-name {
    font-weight: 700;
    color: #0f172a;
    font-size: {{ fs(9.1) }};
    margin-bottom: 0.4mm;
  }
  .skill-group .skill-keywords {
    color: #475569;
    font-size: {{ fs(8.6) }};
  }

  /* Languages, references */
  .inline-list { color: #334155; }
  .inline-list .item { display: block; margin-bottom: 0.4mm; }
  .inline-list .item-name { font-weight: 600; color: #0f172a; }
  .inline-list .item-detail { color: #64748b; }
  .refs {
    color: #334155;
    font-size: {{ fs(8.7) }};
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 4mm;
  }
  .refs .ref { display: block; }
  .refs .item-name { font-weight: 600; color: #0f172a; }
  .refs .item-detail { color: #64748b; }
  .refs .ref-link { color: #2563eb; text-decoration: none; }
  .refs > * + * { margin-top: 0; }

  strong, b { color: #0f172a; }
</style>
</head>
<body>

<header class="header">
  {% if image_url %}<img class="photo" src="{{ image_url }}" alt="">{% endif %}
  <div class="header-text">
    <h1 class="name">{{ basics.name }}</h1>
    {% if basics.label %}<div class="label">{{ basics.label }}</div>{% endif %}
    <div class="contact">
      {% if basics.email %}<span><a href="mailto:{{ basics.email }}">{{ basics.email }}</a></span>{% endif %}
      {% if basics.phone %}<span>{{ basics.phone }}</span>{% endif %}
      {% if basics.location %}<span>{{ [basics.location.city, basics.location.countryCode] | select | join(", ") }}</span>{% endif %}
    </div>
    {% if basics.profiles %}
    <div class="contact profiles-line">
      {% for p in basics.profiles %}<span><a href="{{ p.url }}">{{ p.network }}: {{ p.username }}</a></span>{% endfor %}
    </div>
    {% endif %}
  </div>
</header>

{% if basics.summary %}
<section class="section">
  <div class="section-title">{{ labels.profile }}</div>
  <div class="section-body summary">{{ basics.summary }}</div>
</section>
{% endif %}

{% if work %}
<section class="section">
  <div class="section-title">{{ labels.experience }}</div>
  <div class="section-body">
    {% for w in work %}
    <div class="entry">
      <div class="entry-head">
        <div class="entry-title">{{ w.position }} <span style="color:#64748b;font-weight:500">— {{ w.name }}</span></div>
        <div class="entry-meta">{{ fmt_range(w.startDate, w.endDate) }}</div>
      </div>
      <div class="entry-sub">
        {% if w.location %}{{ w.location }}{% endif %}
        {% if w.url %}{% if w.location %}<span class="dot">·</span>{% endif %}<a class="entry-link" href="{{ w.url }}">{{ w.url | replace('https://', '') | replace('http://', '') }}</a>{% endif %}
      </div>
      {% if w.highlights %}
      <ul>
        {% for h in w.highlights %}<li>{{ h }}</li>{% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{% if projects %}
<section class="section">
  <div class="section-title">{{ labels.projects }}</div>
  <div class="section-body">
    {% for p in projects %}
    <div class="entry">
      <div class="entry-head">
        <div class="entry-title">{{ p.name }}{% if p.description %} <span style="color:#64748b;font-weight:500">— {{ p.description }}</span>{% endif %}</div>
        <div class="entry-meta">{{ p.startDate }}{% if p.endDate %} – {{ p.endDate }}{% endif %}</div>
      </div>
      {% if p.url %}<a class="entry-link" href="{{ p.url }}">{{ p.url | replace('https://', '') | replace('http://', '') }}</a>{% endif %}
      {% if p.highlights %}
      <ul>
        {% for h in p.highlights %}<li>{{ h }}</li>{% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{% if skills %}
<section class="section">
  <div class="section-title">{{ labels.skills }}</div>
  <div class="section-body">
    <div class="skills">
      {% for s in skills %}
      <div class="skill-group">
        <div class="skill-name">{{ s.name }}</div>
        <div class="skill-keywords">{{ s.keywords | join(", ") }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
</section>
{% endif %}

{% if education %}
<section class="section">
  <div class="section-title">{{ labels.education }}</div>
  <div class="section-body">
    {% for e in education %}
    <div class="entry">
      <div class="entry-head">
        <div class="entry-title">{{ e.institution }}</div>
        <div class="entry-meta">{{ fmt_range(e.startDate, e.endDate) }}</div>
      </div>
      <div class="entry-sub">
        {% if e.studyType %}{{ e.studyType }}{% endif %}
        {% if e.studyType and e.area %}<span class="dot">·</span>{% endif %}
        {% if e.area %}{{ e.area }}{% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{% if languages %}
<section class="section">
  <div class="section-title">{{ labels.languages }}</div>
  <div class="section-body inline-list">
    {% for l in languages %}
    <div class="item"><span class="item-name">{{ l.language }}</span> <span class="item-detail">— {{ l.fluency }}</span></div>
    {% endfor %}
  </div>
</section>
{% endif %}

{% if references %}
<section class="section">
  <div class="section-title">{{ labels.references }}</div>
  <div class="section-body refs">
    {% for r in references %}
    <div class="ref">
      <div class="item-name">{{ r.name }}</div>
      {% if r.url %}<div><a class="ref-link" href="{{ r.url }}">{{ r.label or 'lien' }}</a></div>{% endif %}
      {% if r.reference %}<div class="item-detail">{{ r.reference }}</div>{% endif %}
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

</body>
</html>
"""


def fmt_range(start, end, present="Present") -> str:
    """Format a YYYY-MM or YYYY date range as 'Sep 2024 – Sep 2026' / '2024 – Present'."""
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
        "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }

    def fmt(d) -> str:
        # An omitted endDate arrives from Jinja as Undefined (str -> ""), not None.
        s = "" if d is None else str(d)
        if not s:
            return present
        if len(s) == 7 and s[4] == "-":
            y, m = s.split("-")
            return f"{months.get(m, m)} {y}"
        return s

    a, b = fmt(start), fmt(end)
    if a == b:
        return a
    return f"{a} – {b}"


def detect_lang(data: dict, override: str | None = None) -> str:
    """Resolve output language: explicit override > data['_lang'] > content heuristic."""
    if override in ("fr", "en"):
        return override
    lang = (data or {}).get("_lang")
    if lang in ("fr", "en"):
        return lang
    blob = json.dumps(data or {}, ensure_ascii=False).lower()
    fr = len(re.findall(r"\b(et|de|des|avec|pour|les|une|chez|conçu|piloté|du|au)\b", blob))
    return "fr" if fr >= 4 else "en"


def find_image(image_field, extra_dirs=()):
    """Locate the photo across likely dirs; fall back to default_photo.png. Returns a Path or None."""
    search = list(extra_dirs) + [HERE, HERE / "assets", ASSETS]
    cands = []
    if image_field:
        p = Path(image_field)
        if p.is_absolute():
            cands.append(p)
        else:
            cands += [Path(d) / image_field for d in search]
    cands += [Path(d) / "default_photo.png" for d in search]
    for c in cands:
        if c.exists():
            return c.resolve()
    return None


FIT_SCALES = (1.0, 0.97, 0.94, 0.91, 0.88, 0.85)


def render_html(data: dict, image_url: str, font_scale: float = 1.0, lang: str | None = None) -> str:
    L = LABELS[detect_lang(data, lang)]
    env = Environment(loader=BaseLoader(), autoescape=True, trim_blocks=True, lstrip_blocks=True)
    env.globals["fmt_range"] = partial(fmt_range, present=L["present"])
    env.globals["fs"] = lambda x: f"{x * font_scale:.3f}pt"
    return env.from_string(TEMPLATE).render(
        basics=data.get("basics") or {},
        image_url=image_url,
        work=data.get("work") or [],
        projects=data.get("projects") or [],
        skills=data.get("skills") or [],
        education=data.get("education") or [],
        languages=data.get("languages") or [],
        references=data.get("references") or [],
        labels=L,
    )


def write_pdf_autofit(data: dict, image_url: str, out_path: Path,
                      base_url: str | None = None, lang: str | None = None) -> float:
    """Render with progressively smaller fonts until the CV fits on one page."""
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is required to build the PDF but could not be imported "
            f"({exc}). Install the Python package AND its system libraries — pip "
            "alone is not enough:\n"
            "  pip install weasyprint pyyaml jinja2 --break-system-packages\n"
            "  # Debian/Ubuntu system libs: apt install libpango-1.0-0 libpangoft2-1.0-0\n"
            "If those native libraries are unavailable in this environment, the PDF "
            "step cannot run here; render the HTML preview instead and build the PDF "
            "on a machine where WeasyPrint is installed."
        ) from exc

    chosen_doc = None
    chosen_scale = FIT_SCALES[-1]
    for s in FIT_SCALES:
        html_str = render_html(data, image_url, font_scale=s, lang=lang)
        doc = HTML(string=html_str, base_url=base_url).render()
        if len(doc.pages) <= 1:
            chosen_doc, chosen_scale = doc, s
            break
    if chosen_doc is None:
        html_str = render_html(data, image_url, font_scale=FIT_SCALES[-1], lang=lang)
        chosen_doc = HTML(string=html_str, base_url=base_url).render()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    chosen_doc.write_pdf(str(out_path))
    return chosen_scale


def main(argv: list[str]) -> int:
    pos = [a for a in argv[1:] if not a.startswith("--")]
    opts = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else True)
            for a in argv[1:] if a.startswith("--")}
    lang = opts.get("--lang")
    lang = lang if lang in ("fr", "en") else None

    in_path = Path(pos[0]) if pos else HERE / "resume.yaml"
    out_path = Path(pos[1]) if len(pos) > 1 else HERE / "resume.pdf"

    data = yaml.safe_load(in_path.read_text(encoding="utf-8")) or {}

    basics = data.get("basics") or {}
    img = find_image(basics.get("image"), [in_path.parent])
    image_url = "file://" + quote(str(img)) if img else ""

    try:
        scale = write_pdf_autofit(data, image_url, out_path, base_url=str(in_path.parent), lang=lang)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Wrote {out_path} (scale {scale:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
