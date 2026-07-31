# Personal Website — Julian Dörner

Static personal academic website. Plain HTML, minimal CSS, no JavaScript in the deployed site.

## Project structure

```
src/
  template.html     shared layout (header, nav, footer)
  style.css         all styling
  pages/            one file per page, content only
    index.html
    publications.html
    conferences.html
    teaching.html
    contact.html

config.toml         site-wide settings (name, position, nav)
build.py            assembles template + pages → docs/
watch.py            rebuilds on file changes and serves docs/ locally
docs/               generated output (git-ignored)
```

## Editing content

Each file in `src/pages/` starts with a front matter block followed by plain HTML:

```html
---
title: Page Title
---

<p>Your content here.</p>
```

| What to change | Where |
|---|---|
| Name, position, nav items | `config.toml` |
| Page content | `src/pages/<page>.html` |
| Layout (header, footer) | `src/template.html` |
| Styles | `src/style.css` |
| Profile photo | drop `photo.jpg` into `src/` |

## Local development

**First time setup** — create a virtual environment and install the dependency:

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Next time, just activate the environment before starting:

```bash
source .venv/bin/activate
```

Start the dev server:

```bash
python watch.py
```

Or press `Ctrl+Shift+B` in VS Code.

Then open `http://localhost:8000`. The browser refreshes automatically on every save.

## Adding a page

1. Create `src/pages/newpage.html` with front matter and content.
2. Add an entry to `[[nav]]` in `config.toml`.

## Deployment

The workflow in `.github/workflows/build.yml` deploys to **GitHub Pages** on every push to `main`.

One-time setup:
1. Push the repository to GitHub.
2. Go to **Settings → Pages → Source** and select **GitHub Actions**.
