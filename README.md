# Eupraxis Consulting website

Static site: `index.html` (landing page, 9 sections per scope), `blog.html` (blog index), `privacy.html`, `terms.html`.
No build step. Open `index.html` or serve the folder.

## Structure
- `css/style.css` – all styles. Brand tokens at the top (`:root`). Swap colors/fonts here when Craig's brand spec arrives.
- `js/main.js` – nav, reveal animations, whiteboard draw-on, contact modal, GHL submission, blog filters.
- `assets/brand/` – headshot, logo (white PNG from old site, SVG favicon; the nav logo is an inline SVG mark + wordmark).
- `assets/clients/` – client logos from the old site (credibility strip).

## GoHighLevel
Set `GHL_WEBHOOK_URL` in `js/main.js` to an Inbound Webhook trigger URL. The workflow should:
create/update contact, add tag `website-inbound`, add to the **Inbound** pipeline, notify Craig.
Fields posted as JSON: `name, email, phone, message, topic, page, submitted_at`.

## Blog publishing (so Craig can post without a developer)
Option A (recommended, keeps everything in GHL): host the blog in GHL Sites > Blogs. Point `blog.html` at it,
or embed the GHL blog list. Latest-three on the landing page can use GHL's blog RSS.
Option B: keep WordPress for authoring only and render `blog.html` from its RSS feed (`/feed/`) with a small fetch.

## Redirects
Two legacy WordPress URLs need 301s. Templates in `_redirects` (Netlify/Cloudflare) and `.htaccess` (Apache).

## Placeholders Craig needs to fill
- Case study metrics (hatched green highlights in Success Stories)
- Origin story text (About > "Where this comes from")
- Named speaking appearances
- LinkedIn URL, privacy and terms text
