#!/usr/bin/env python3
"""Render a tailored CV YAML into an on-screen HTML preview.

The preview uses the EXACT SAME template as the PDF renderer (build_cv.render_html),
so what you see here is what the final PDF will look like — there is no separate
preview template to drift. This script only adds screen-only chrome (an A4 page
card) and embeds the photo as a data URI so the file is self-contained.

Usage: python3 render_preview.py <input.yaml> [output.html] [--lang fr|en]
If output.html is omitted, it is written next to the input as <stem>_preview.html.
"""
import base64
import mimetypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_cv  # noqa: E402  (shared template / renderer)

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required. Install with: pip install pyyaml --break-system-packages")

# Screen-only chrome: the PDF gets its margins from @page, which browsers ignore,
# so on screen we render the body as a centered A4 card with matching inner padding.
SCREEN_CSS = """
  @media screen {
    html { background: #eef1f5; }
    body {
      width: 210mm;
      min-height: 296mm;
      margin: 24px auto;
      padding: 11mm 14mm;
      background: #fff;
      box-shadow: 0 6px 30px rgba(15, 23, 42, 0.14);
      border-radius: 2px;
    }
  }
"""


def data_uri(path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime or 'image/png'};base64,{b64}"


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else True)
            for a in argv if a.startswith("--")}
    if not args:
        sys.exit("Usage: render_preview.py <input.yaml> [output.html] [--lang=fr|en]")

    in_path = args[0]
    if not os.path.isfile(in_path):
        sys.exit(f"Input YAML not found: {in_path}")

    stem = os.path.splitext(os.path.basename(in_path))[0]
    out_path = args[1] if len(args) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(in_path)), f"{stem}_preview.html")

    with open(in_path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            sys.exit(f"The YAML is invalid and could not be parsed:\n{e}")
    if not isinstance(data, dict):
        sys.exit("Top-level YAML must be a mapping (basics, work, ...).")

    lang = opts.get("--lang")
    lang = lang if lang in ("fr", "en") else None

    basics = data.get("basics") or {}
    img = build_cv.find_image(basics.get("image"), [os.path.dirname(os.path.abspath(in_path))])
    image_url = data_uri(img) if img else ""

    html = build_cv.render_html(data, image_url, font_scale=1.0, lang=lang)
    html = html.replace("</style>", SCREEN_CSS + "</style>", 1)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(out_path)


if __name__ == "__main__":
    main(sys.argv[1:])
