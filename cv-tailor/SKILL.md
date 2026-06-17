---
name: cv-tailor
description: "Tailor the user's CV to a specific job offer and output a modified resume YAML ready to render. Use this skill whenever the user provides a job offer (text, URL, screenshot, or PDF) and asks to adapt, tailor, customize, or rework their CV for it — even if they don't explicitly say \"CV\" or \"resume\". Also trigger on phrases pairing a job description with an implied application intent (e.g. \"I have this job offer\", \"look at this listing\", \"applying for...\")."
---

# CV Tailor

Adapt the user's CV to a specific job offer using the project knowledge bases as the single source of truth. The working document is a complete resume YAML conforming to the JSON Resume schema, saved as a file alongside an HTML preview that is rendered from the **same template as the final PDF** (identical layout, content, and styling). The one difference: the PDF auto-fits to one page by scaling the font down slightly if needed, while the preview always renders at full size — so an overflowing preview will still print on a single, slightly tighter page. On feedback, the saved YAML is edited surgically rather than regenerated. **Once the user is satisfied with the content, the bundled renderer builds the final one-page PDF from the YAML and that PDF is the deliverable.**

## Setup (customize before use)

This skill is a template — wire it up to your own data before relying on it:

1. **Knowledge bases**: create project knowledge files for your own background. A suggested split (adjust names/count to fit your history):
   | File | Content | Always search |
   |---|---|---|
   | `identity_knowledge_base` | Fixed identity: basics, profiles, education, references — values to copy verbatim | Yes — every run |
   | `experience_1_knowledge_base` | Your current/most recent role: dates, metrics, offer-mapping table | Yes — every run |
   | `experience_2_knowledge_base` | Your previous role: dates, metrics, offer-mapping table | Yes — every run |
   | `skills_knowledge_base` | Hard + soft skills with offer → skills mapping table | Yes — every run |
   | `optional_knowledge_base` | Side projects / internships — include only if relevant | Conditional |
   Add as many experience knowledge bases as you have roles worth covering; rename the table above to match.
2. **Photo**: replace `assets/default_photo.png` with your own headshot, or leave the bundled placeholder.
3. **Application tracker** (optional, see *Application Tracker* below): point it at your own tracking spreadsheet name instead of the placeholder used here.

## Workflow

1. **Read the job offer** carefully. Extract: role title, seniority, core stack, domain, soft-skill signals, and the offer's language (FR or EN).
2. **Search the project knowledge** with `project_knowledge_search` to gather material from the knowledge bases described in *Setup* above — search all relevant ones before adapting.
   Search by topic relevant to the offer (e.g. "frontend React", "LLM RAG", "DevOps CI/CD", "education references profiles"). Don't skip this step — these knowledge bases should contain offer-aware mapping tables (section "Mapping offres → axes / skills") designed to drive the adaptation.
   **Optional knowledge base inclusion rules** — adapt to your own optional projects, e.g.:
   - Offer mentions a specific stack used in a side project → consider including that project
   - Offer is product-oriented and values zero-to-one delivery speed → consider a relevant side project
   - Offer has a dimension (industry, function) matched by an optional experience → include it
   - Otherwise: omit optional items to keep the CV focused
3. **Detect language** of the offer. The output CV must be written in that language. If the offer is in English, translate adapted fields but keep proper nouns (company names, school names; translate generic role-type words like "Apprenticeship"/"Alternance" as appropriate).
4. **Adapt content** following the rules below.
5. **Write the YAML to a file** at `/mnt/user-data/outputs/cv_<company-or-role>.yaml` (slugify: lowercase, hyphens, e.g. `cv_acme-corp-frontend.yaml`). This file is the working document — it persists so it can be edited surgically on later feedback. Validate it: a clean run of the render script (below) confirms the YAML parses.
6. **Render the faithful preview** by running the bundled script (do **not** print the raw YAML in a code block):
   ```bash
   python3 /mnt/skills/user/cv-tailor/scripts/render_preview.py \
     /mnt/user-data/outputs/cv_<slug>.yaml --lang=fr
   ```
   It writes `cv_<slug>_preview.html` next to the YAML, rendering it with the **exact same template as the PDF** (`scripts/build_cv.py`) plus screen-only page chrome — never write or inline your own HTML. The preview only needs `pyyaml` + `jinja2`, so it is fast and weasyprint-free. Pass `--lang=fr` or `--lang=en` to match the offer's language (this also localizes the section headers); omit it to auto-detect.
7. **Present the preview + YAML** (`present_files` with the preview HTML first, then the YAML) and add a brief summary (3–5 bullets): what you changed and why, tied to specific offer requirements, plus any gaps. Do not paste the YAML contents into the chat. The PDF is **not** built yet — it is produced in step 8 once the user approves the content.
8. **Build the final PDF — only once the user is satisfied with the content.** When they signal approval ("looks good", "ship it", "generate the PDF", "finalize", or any clear go-ahead — see *Finalizing* below), run the renderer on the approved YAML and present the PDF as the deliverable:
   ```bash
   python3 /mnt/skills/user/cv-tailor/scripts/build_cv.py \
     /mnt/user-data/outputs/cv_<slug>.yaml \
     /mnt/user-data/outputs/cv_<slug>.pdf --lang=fr
   ```
   Then `present_files` the PDF. Do **not** build the PDF on every edit — only on approval (it is the slow, weasyprint-dependent step).
9. **(Optional) Log the application** — see *Application Tracker* below if you've wired one up.

## Schema

The output must be a YAML document conforming to the JSON Resume-style schema used by `build_cv.py`. Top-level keys (in order):

```yaml
basics:
  name:
  label:
  image:
  email:
  phone:
  location:
    city:
    countryCode:
  summary:
  profiles:
    - network:
      username:
      url:

work:
  - name:
    position:
    location:
    url:
    startDate:        # YYYY-MM
    endDate:          # YYYY-MM, or omit for "Present"
    highlights:
      - "..."

projects:
  - name:
    description:
    url:
    startDate:        # YYYY or YYYY-MM
    endDate:          # optional
    highlights:
      - "..."

skills:
  - name:
    keywords:
      - "..."

education:
  - institution:
    area:
    studyType:
    startDate:        # YYYY
    endDate:          # YYYY

languages:
  - language:
    fluency:

references:
  - name:
    reference:
    url:              # optional — link to a recommendation letter / page
    label:            # optional — link text (defaults to "lien")
```

**Field rules:**
- `basics.image` — set to a filename matching your own photo (e.g. `your_name.png`); the renderer falls back to the bundled `assets/default_photo.png` if missing.
- Dates — `YYYY-MM` for work entries, `YYYY` for education. Omit `endDate` (or leave blank) for ongoing roles → renders as "Present".
- `highlights` — list of strings. No HTML. Use plain text. Bold via inline emphasis is not supported; keep prose clean and direct.
- `summary` — single string. Use YAML folded scalar (`>-`) for multi-line.
- `profiles[].url` — full https URL.
- Sections without relevant content for this offer: omit the top-level key entirely (the renderer skips empty sections). Do **not** emit empty arrays.

## What to adapt

**Adapt freely:**
- `basics.label` — align to the target role title when reasonable
- `basics.summary` — rewrite to mirror the offer's priorities and vocabulary. 3 sentences max to keep one-page layout.
- `work[].highlights` — reorder, rephrase, re-emphasize bullets. Drop irrelevant ones, promote matching ones. Every claim must trace back to the knowledge bases.
- `work[].position` — only if translation requires it
- `projects[].highlights` and `projects[].description` — same rules as work
- `skills` — reorder groups, surface relevant categories first, drop irrelevant ones, regroup if the offer calls for it. Use the `skills_knowledge_base` mapping table.

**Never invent:**
- Companies, dates, schools, degrees, named projects the user hasn't done
- Metrics absent from the knowledge bases
- Tech the user hasn't actually worked with (flag the gap in the post-YAML summary instead)

**Stable identity — always copy verbatim from `identity_knowledge_base`:**
- `basics.name`, `basics.email`, `basics.phone`, `basics.location` — never modify
- `basics.image` — keep as-is
- `profiles` — copy exactly
- `education` — school names, degrees, periods — never modify
- `references` — names and reference text — copy exactly
- Company names, exact periods, locations on `work` items

## Content rules

- **Truthfulness is non-negotiable.** Rewriting ≠ inventing. If the offer wants Kubernetes and the knowledge bases only mention Docker, do not add Kubernetes. Flag the gap in the post-YAML summary.
- **Use the knowledge bases as the source of truth.** They should contain validated bullet versions, metrics, vocabulary preferences, and offer-aware mapping tables. Don't paraphrase from memory if a knowledge base bullet exists.
- **Use complementary context** from past conversations (`conversation_search`) only when an offer-specific topic might connect to prior work not covered by any knowledge base. Same truthfulness rule applies. Note in the post-YAML summary when you used something outside the knowledge bases.
- **Mirror vocabulary** from the offer where it honestly fits (e.g. if the offer says "multi-tenant SaaS platform" and the user built an internal platform, lean into "platform" — don't invent "multi-tenant").
- **Keep anchor metrics** from the knowledge bases — whatever quantified impact figures you've stored there (team size, throughput, adoption numbers, etc.).
- **Bullet count**: 3–5 highlights per experience. Don't pad. The renderer is tuned for one page.
- **Plain text only** in `highlights` — no HTML, no markdown bold. The renderer handles styling.
- **Vocabulary preferences**: adjust this list to your own voice/avoid-list as captured in your knowledge bases (e.g. words you favor, words you avoid like "expert" or em dashes).

## Output format

During tailoring and iteration the deliverable is **two files**, not a code block:
- `cv_<slug>.yaml` — the tailored resume (the working document)
- `cv_<slug>_preview.html` — the faithful preview rendered from it (same template as the PDF)

Present them with `present_files` (preview first), then a short note in chat:

```
**Changes made:**
- [bullet 1: what was tailored and why]
- [bullet 2]
...

**Gaps vs the offer** (if any): [honest note about requirements not covered by the knowledge bases]
```

Once the user approves the content, the **final deliverable is the PDF** `cv_<slug>.pdf` (see *Finalizing*), presented with `present_files`.

Do not paste the YAML, HTML, or PDF contents into the chat — the files carry them.

## Preview & iterating on feedback

The preview is rendered by `scripts/render_preview.py`, which imports `scripts/build_cv.py` and reuses its template — so the preview and the final PDF share **one** layout, content, and styling. **Never rewrite, regenerate, or inline the HTML/CSS; never restyle the preview.** All styling lives in `build_cv.py`'s `TEMPLATE`. The preview adds only screen-only page chrome and embeds the photo as a data URI. (The only rendering difference is the PDF's one-page auto-fit font scaling; the preview renders at full size, so a CV that overflows the preview will still print on one page.)

When the user gives feedback on an already-generated CV, **edit the existing YAML file surgically — do not rewrite it from scratch:**

1. The YAML already lives at `/mnt/user-data/outputs/cv_<slug>.yaml`. If it is not in your context, `view` it first.
2. Map the feedback to a field. The user may name a YAML path directly (`work[1].highlights[0]`) or describe it ("the second bullet of the most recent job"). Resolve it to the exact field.
3. Apply a **targeted `str_replace`** changing only that field's value, leaving every other line byte-for-byte unchanged. Change only what the feedback touches.
4. Re-run `render_preview.py` on the same file to refresh the preview, then `present_files` the updated preview and give a one-line note on what changed.

Only fall back to regenerating larger portions if the user explicitly asks for a broad redo (e.g. "rewrite the whole summary section", "start over for a different offer"). Otherwise, minimal diffs keep prior approved edits intact and make feedback fast.

## Finalizing — build the PDF

The PDF is the end product, built **only after the user is satisfied with the content** — not on every iteration. Treat as approval any clear go-ahead: "looks good", "ship it", "generate the PDF", "finalize", "send it", or an explicit yes when you offer to build it. If iteration seems to be winding down and they haven't said so, you may *offer* ("Want me to generate the PDF?") rather than building unprompted.

On approval:

1. Make sure WeasyPrint is importable. If `python3 -c "import weasyprint"` fails, install it from PyPI:
   ```bash
   pip install weasyprint pyyaml jinja2 --break-system-packages
   ```
   If the install or a later import still fails because of missing dependencies or native libraries, relay the error honestly — don't fake a PDF.
2. Run the renderer on the approved YAML, passing the offer's language:
   ```bash
   python3 /mnt/skills/user/cv-tailor/scripts/build_cv.py \
     /mnt/user-data/outputs/cv_<slug>.yaml \
     /mnt/user-data/outputs/cv_<slug>.pdf --lang=fr
   ```
   It auto-fits to one page (font scales 1.00 → 0.85) and resolves the photo from the bundled `assets/default_photo.png` (the `basics.image` name need not exist on disk). It prints `Wrote … (scale X.XX)`.
3. `present_files` the PDF — it is the deliverable. Add a one-line note (e.g. the fit scale if below 1.00, meaning the content was tightened to fit one page).

**Dependencies:** WeasyPrint is installed from PyPI (step 1). It also needs native libraries (Pango/Cairo) at runtime; if they are absent the import still fails and the script prints an actionable message — relay it honestly rather than faking a PDF. The preview step never needs WeasyPrint, so iteration is unaffected.

## Application Tracker (optional)

If you want to keep a log of applications, add a step after presenting the final PDF that appends a row to a tracking spreadsheet of your choice (e.g. via a Google Drive MCP server). This is left unconfigured in this template — wire it up to your own spreadsheet and MCP connection if you want it.

### Suggested columns to log

| Column | Content | Source |
|---|---|---|
| **Role** | Job title / role name | Offer title |
| **Employer** | Company name | Offer |
| **Date applied** | Today's date | System date |
| **Status** | e.g. `Sent` (default) | Fixed |
| **Description** | 1–2 sentence summary of the offer in the offer's language | Your reading of the offer |

Implement the actual append step with whatever MCP server / API you have connected (e.g. a Google Sheets or Drive MCP). On success, confirm with a single line; on failure (file not found, permission error), mention it briefly but don't block — the PDF delivery is the primary deliverable.

## Edge cases

- **Offer provided as URL**: fetch with `web_fetch` if accessible; otherwise ask the user to paste the text.
- **Offer is vague or very short**: do a lighter adaptation and say so.
- **Offer mismatches the user's profile badly** (e.g. senior data scientist role for a frontend background): flag it upfront, still produce a best-effort adaptation, and name the stretch.
- **User specifies extra constraints** ("emphasize the product side more", "keep it to 1 page"): honor them on top of the default rules.
- **Section without relevant items for this offer** (e.g. no awards): omit the top-level key entirely — do not emit empty lists.
