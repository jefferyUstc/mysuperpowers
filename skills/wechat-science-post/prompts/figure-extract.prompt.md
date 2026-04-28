# Step [4.5] — Figure extract prompt (paper / combined modes only)

## Your role here

You are an **automated figure cropper**. The article references paper figures via `<!-- IMG:N -->` placeholders (where `N` is an integer). For each placeholder, you render the source PDF page, look at it, identify the figure's bounding box, and crop. The cropped PNG goes to `work/<task>_<ts>/figures/fig-N/image.png` so `[5] figures_prep` picks it up.

You are **not** writing prose, **not** making narrative decisions. This is a visual task — find the figure region in the rendered page image and call the crop tool with the right pixel bbox.

## When to run

- **Paper mode**: yes (any time `draft.md` references `<!-- IMG:N -->` with integer N)
- **Combined mode**: yes (paper-driven figures use the same pattern)
- **Repo mode**: skip (code-example-N images come from `[5a] notebook_outputs.py`; covers are user-supplied)

Skip paper-figure auto-extract entirely if the user has manually placed `figures/fig-N/image.<ext>` already. The user override always wins.

## What this step produces

For each integer-id `<!-- IMG:N -->` placeholder in `draft.md`:

| Output | Path |
|---|---|
| Cropped figure PNG | `work/<task>_<ts>/figures/fig-N/image.png` |
| (intermediate) rendered page PNG | `work/<task>_<ts>/figures/_pages/<id>-page-<NNN>.png` |

`<id>` is the paper id from ingest (default `main`). `_pages/` is intermediate scratch — `figures_prep.py` ignores it; safe to `rm -rf` after the article publishes.

## Hard rules

- **Do NOT crop `formula-N` or `code-example-*` placeholders.** Those have separate provenance.
- **Do NOT include the figure's caption text in the crop.** Caption ("Fig. N | ...") is described in prose; the crop is the visual panels only.
- **Do NOT guess bbox without first Reading the rendered PNG.** The Read step is mandatory — without seeing the actual rendered page, you cannot accurately locate panels.
- **Do NOT proceed if a crop is obviously wrong** (caption visible, panels cut off mid-row, header banner included). Retry with a refined bbox; after 2 failed retries, halt and ask the user.
- **Skip silently** if `figures/fig-N/image.<ext>` (any extension) already exists — the user has provided their own.

## Inputs

- `work/<task>_<ts>/draft.md` — scan for `<!-- IMG:N -->` placeholders (where N is an integer)
- `work/<task>_<ts>/notes.md` § Figure inventory — gives the page where each Fig N's caption starts
- `work/<task>_<ts>/ingest/raw/<id>.pdf` — source PDF (`<id>` from `paper.json.papers[*].id`; usually `main`)
- `scripts/figure_extract.py` — render + crop tool (pure pymupdf + Pillow)

## Procedure

For each Fig N referenced in `draft.md`:

### 1. Skip if user already provided

```bash
ls work/<task>_<ts>/figures/fig-N/image.* 2>/dev/null
```

If anything exists, log "fig-N: user-supplied, skipping auto-extract" and move on.

### 2. Render the page

Get the page number from `notes.md § Figure inventory`. Then:

```bash
"$PY" "$SKILL_DIR/scripts/figure_extract.py" page-image \
    --pdf  work/<task>_<ts>/ingest/raw/<id>.pdf \
    --page <page-num> \
    --dpi  300 \
    --out  work/<task>_<ts>/figures/_pages/<id>-page-<NNN>.png
```

(Use `printf "%03d" <page-num>` for the zero-padded `<NNN>` filename.)

The script prints the dimensions, e.g. `2481x3296 px (at 300 DPI)`. **Note these dimensions** — the bbox you'll specify next is in this pixel space.

### 3. Read the rendered PNG

Use the `Read` tool on the page PNG path. You'll receive the full page image visually.

If the figure spans more than half the page in either dimension, do **not** also fetch a thin reference strip — the full page already gives you enough context. Only when figures are tightly packed and you have trouble distinguishing the caption boundary should you crop a thin left-margin strip and Read that:

```bash
"$PY" "$SKILL_DIR/scripts/figure_extract.py" crop \
    --src work/<task>_<ts>/figures/_pages/<id>-page-<NNN>.png \
    --bbox 0,0,400,<page-height> \
    --out /tmp/refstrip-<id>-<NNN>.png
```

### 4. Identify the figure's bounding box

Visual rules of thumb for academic publisher PDFs:

- **Top edge**: just below the page header banner ("Article" / journal name / DOI). At 300 DPI, the banner is ~80-180 px tall; start the bbox at roughly y = 180.
- **Bottom edge**: just above the line where the caption text "Fig. N |" begins. The caption is usually denser body text in italic / serif; the figure above it ends at the last panel's bottom edge.
- **Left/right edges**: full content width minus white margins. Most academic pages render content from x ≈ 80 to x ≈ 2400 at 300 DPI; you can use these as defaults for full-width figures.
- **Multi-row figures**: many Nature/Cell figures have 2–3 rows of panels (a-e in row 1, f-i in row 2, j-l in row 3). The figure ends at the last row, NOT at the end of the first row — common mistake; check carefully.

The rendered PNG is in pixel space `(0, 0)` (top-left) to `(width, height)` (bottom-right). Specify bbox as `x1,y1,x2,y2` where `(x1, y1)` is top-left of the crop region.

### 5. Crop

```bash
"$PY" "$SKILL_DIR/scripts/figure_extract.py" crop \
    --src  work/<task>_<ts>/figures/_pages/<id>-page-<NNN>.png \
    --bbox <x1,y1,x2,y2> \
    --out  work/<task>_<ts>/figures/fig-N/image.png
```

The script clamps to image bounds and rejects regions smaller than 50×50 px.

### 6. Verify

`Read` the cropped output. Check:

- ✅ All panels visible (a, b, c, ... — count panel labels match the caption's panel list)
- ✅ Caption text NOT included in crop
- ✅ Page header NOT included in crop
- ✅ No abrupt cut through a panel mid-content

If any fails, repeat steps 4–6 with adjusted bbox. After 2 retries on the same figure, halt and tell the user:

```
fig-N: failed to auto-extract after 2 retries. Manual screenshot needed.
  Source PDF: work/<task>_<ts>/ingest/raw/<id>.pdf, page <page-num>
  Place the screenshot at: work/<task>_<ts>/figures/fig-N/image.{png,jpg}
  Then re-run [5] figures_prep.
```

## Cover image (all modes — paper / repo / combined)

Skip entirely if `figures/cover.{png,jpg}` already exists — user has supplied their own; do NOT overwrite, do NOT generate a prompt.

Otherwise, produce **two outputs**:

1. `figures/cover-prompt.txt` — a creative **English** image-generation prompt the user can paste into DALL-E / ChatGPT image / MidJourney / Stable Diffusion / 文心一格 / 通义万相 etc. to make a real cover.

2. `figures/cover.png` — a deterministic light-gray placeholder so `[5] figures_prep` and `[6] lint` pass. Generated by:

```bash
"$PY" "$SKILL_DIR/scripts/figure_extract.py" placeholder-cover \
    --out work/<task>_<ts>/figures/cover.png
```

The placeholder is 1280×545 px (exact WeChat 2.35:1 cover ratio), light gray, with small hint text inside so the user immediately recognizes it as not-the-final cover.

### Crafting the cover prompt

The cover prompt is **English only**. Image-generation models respond best to English regardless of the article's audience language (the user's tool of choice may be Chinese-trained, in which case they translate before pasting).

The image itself must use **no text**. AI image models render text poorly; readers see the article title in WeChat metadata anyway. Communicate the article's central thesis purely through visual metaphor.

**Structure** (single paragraph, ~120-250 chars):

> `<Subject sentence>`: a visual metaphor for what the work does, tied to the article's central thesis from `notes.md`. Avoid literal scenes (the lab, the screen, the researcher); metaphor is what makes a cover memorable.
>
> `<Style + composition + palette sentence>`: pick a style (editorial illustration / minimalist abstract / technical diagram / watercolor / isometric / etc.), describe composition (centered / layered / grid / asymmetric / etc.), and name 2–3 specific colors.
>
> `Aspect ratio 2.35:1 (1280x545 px, WeChat cover standard).`
>
> `No text, no watermarks, no logos, no faces, no UI elements.`

### Example for a paper article (spatial DNA methylation):

```
Editorial illustration of a glowing tissue cross-section seen from above, with
a faint translucent grid overlay revealing spatial coordinates layered onto
biological structure; clusters of varying intensity inside the tissue suggest
hidden cellular populations becoming visible only when both signal and location
are mapped together. Soft watercolor texture with chromatography effect, deep
teal and warm amber palette on cream background. Aspect ratio 2.35:1
(1280x545 px, WeChat cover standard). No text, no labels, no microscope
frames, no human figures.
```

### Example for a repo article (ggplot2-python):

```
Minimalist abstract composition of six translucent geometric layers floating at
slight angles in 3D, each layer a different shape suggesting one component of a
layered visualization grammar (data, aes, geom, stat, scale, theme); soft
shadows between layers convey composition by stacking, not replacement. Clean
technical illustration with isometric perspective, deep slate background with
cyan, warm coral, and muted lime accents on the layers. Aspect ratio 2.35:1
(1280x545 px, WeChat cover standard). No text, no code blocks, no chart axes,
no UI panels.
```

### Procedure

1. Read `notes.md § Paper / repo understanding` to grasp the central thesis. The cover should illustrate THIS — the unifying idea — not a random visual from the article.

2. Draft the prompt as above. Save plain text (no markdown formatting, no header line, just the prompt paragraph) to:

```bash
work/<task>_<ts>/figures/cover-prompt.txt
```

3. Run the placeholder generator (one shell call):

```bash
"$PY" "$SKILL_DIR/scripts/figure_extract.py" placeholder-cover \
    --out work/<task>_<ts>/figures/cover.png
```

### Tell user (in gate output)

```
Cover handling:
  figures/cover.png         placeholder (light gray, 1280x545 px)
  figures/cover-prompt.txt  English image-gen prompt

To replace the placeholder with an AI-generated cover:
  1. Open figures/cover-prompt.txt
  2. Paste into DALL-E / ChatGPT / MidJourney / 文心一格 / 通义万相 / etc.
  3. Save the output as figures/cover.png
  4. If the output isn't 2.35:1, crop with:
       figure_extract.py crop --src <gen.png> --bbox <x1,y1,x2,y2> \
                              --out figures/cover.png
```

## Output verification (run before returning)

- [ ] For every `<!-- IMG:N -->` integer-id placeholder in draft, `figures/fig-N/image.png` exists
- [ ] For each created file, the visual content is the figure (not header, not caption, not body text)
- [ ] `figures/cover.{png,jpg}` exists (real or already-placeholder; this prompt CAN provide a real one but don't override an existing user-provided cover)

Print a summary table:

```
Figure extraction summary:
  fig-1: page 3 → bbox (x1,y1,x2,y2) → fig-1/image.png (WxH px)
  fig-2: page 4 → bbox (x1,y1,x2,y2) → fig-2/image.png (WxH px)
  ...
  cover: page 3 → bbox (x1,y1,x2,y2) → cover.png (WxH px, aspect 2.32)

Auto-extracted: <N> figures
Skipped (user-supplied): <K> figures
Failed (need manual): <M> figures
```

Then proceed to `[5] figures_prep`.

## Gate

No user gate — this step is automated. Print the summary above; user reviews implicitly when they see the rendered article in `[8] preview`. If the rendered article shows wrong figures, user can:

1. Replace `figures/fig-N/image.<ext>` manually (any extension)
2. Re-run `[5] figures_prep` → `[7] render` → `[8] preview`

## Resolution choice

Default `--dpi 300`. At 300 DPI, a US-letter page renders at ~2481×3296 px (Nature paper sizes are similar). Why 300:

- Fine details (axis labels, panel labels, color-bar ticks) survive Vision-LLM downscaling to ~1568 px input width
- A figure occupying half the page crops to ~1240×1650 px — comfortably above WeChat's 1080 px target, so figures_prep's downscale preserves anti-aliased edges
- A full-page figure crops to ~2400×3000 px — figures_prep then downscales to 1080 px wide, JPEG q=90

If you need higher fidelity (e.g., very small inset panels with critical text), bump to `--dpi 400`. Above 400 DPI is usually wasted — Claude vision input downscales anyway, and figures_prep's 1080 px target leaves anything above ~1600 px crop unused.
