# zachisntdead

## Blog posts
- Naming pattern: `posts/YYYY-MM-DD-post-title.html`
- Start from `posts/_template.html`, update the title, meta line, and paragraphs
- Add the new post link in `index.html` under the Journal list

## One-page sections
- Edit sections in `sections/*.html`
- Rebuild `index.html` with `python3 build.py`
- Template lives in `index.template.html`
- GitHub Actions runs `build.py` on push and commits `index.html`

## Art post templates
- Single image: `posts/art/_single-template.html`
- Gallery: `posts/art/_gallery-template.html` (uses `gallery.js`)

## Markdown posts
- Write `.md` files in `markdown/` with front matter keys: `title`, `date`, `section`, `type`
- Optional: `label` (overrides the meta subtitle), `summary`, `post-to-site`
- For galleries: add a block of standard markdown images right after the H1 (or at top if no H1)
- For inline images: use standard markdown images in the body; consecutive images form a row
- Sections opt in by placing `<!-- md-posts:start -->` and `<!-- md-posts:end -->` inside their `.post-list`
- Run `python3 build_markdown.py` to generate HTML into `posts/<section>/` and refresh section lists
