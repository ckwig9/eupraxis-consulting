"""One-time migration: WordPress REST JSON -> posts/*.md

Usage (from the project root):
    python scripts/migrate_wp.py <wp-posts-full.json> <wp-media.json> <img-map.json>

Inputs come from the WordPress REST API:
    /wp-json/wp/v2/posts?per_page=50&_fields=id,slug,date,modified,title,excerpt,content,categories,featured_media,yoast_head_json
    /wp-json/wp/v2/media?per_page=50&include=<featured ids>&_fields=id,source_url,alt_text,media_details
img-map.json maps every remote image URL to its downloaded path under assets/blog/.

Kept in the repo for reference only. After the migration, posts/*.md are the
source of truth and this script is not part of the build.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

# WordPress category id -> site category key (see scripts/build_blog.py CATEGORIES)
CAT_MAP = {45: "run-outgrow", 37: "culture", 41: "proactive", 36: "outgrow-system", 1: "culture"}

# Old WordPress slugs that redirected to the canonical slug. Kept so the
# redirect files can send old links to the right page.
ALIASES = {
    "outgrow-revenue-expansion-system": ["what-is-outgrow-revenue-growth-system", "2025/05/03/what-is-outgrow-revenue-growth-system"],
    "outgrow-revenue-growth-strategy-signs": ["5-signs-your-company-is-ready-for-outgrow"],
    "outgrow-change-sales-behaviors": ["how-outgrow-changes-sales-behaviors"],
    "outgrow-proactive-sales-culture": ["how-outgrow-creates-proactive-sales-culture"],
    "outgrow-sales-mindset-vs-training": ["outgrow-vs-traditional-sales-training"],
}

WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
SERIES_RE = re.compile(r"part\s+(\w+)\s+of\s+(?:our|the)\s+(CEO|PERMA)\s+Series", re.I)

STRIP_ATTRS = ("class", "style", "id", "aria-hidden", "srcset", "sizes", "decoding", "loading", "fetchpriority", "title")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def clean_body(h, img_map, slug_map):
    # Block-editor comments (<!-- wp:paragraph -->) and wrapper divs (Gutenberg
    # spacers, Elementor containers) carry no content.
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r"<div\b[^>]*>|</div>", "", h)
    # Drop presentational attributes.
    h = re.sub(r'\s(?:%s|data-[\w-]+)="[^"]*"' % "|".join(STRIP_ATTRS), "", h)
    h = re.sub(r"\s(?:%s)='[^']*'" % "|".join(STRIP_ATTRS), "", h)

    # Series intro: "This article is part five of our CEO Series ..."
    series = None
    m = re.search(r"<h5>\s*(?:<strong>)?\s*(?:<em>)?\s*(This article is part\s+\w+\s+of\s+(?:our|the)\s+(?:CEO|PERMA)\s+Series[^<]*)", h, re.I)
    if m:
        sm = SERIES_RE.search(m.group(1))
        if sm:
            n = WORD_NUM.get(sm.group(1).lower()) or (int(sm.group(1)) if sm.group(1).isdigit() else None)
            series = "%s series, part %s" % (sm.group(2).upper(), n)
        h = re.sub(r"<h5>.*?</h5>", "", h, count=1, flags=re.S)
    h = h.replace("<h5>", "<h4>").replace("</h5>", "</h4>")

    # Images: point at the local copy, keep alt/width/height, lazy-load.
    def fix_img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            return tag
        local = img_map.get(src.group(1), src.group(1))
        alt = re.search(r'alt="([^"]*)"', tag)
        w = re.search(r'width="(\d+)"', tag)
        hgt = re.search(r'height="(\d+)"', tag)
        out = '<img src="%s" alt="%s"' % (local, alt.group(1) if alt else "")
        if w and hgt:
            out += ' width="%s" height="%s"' % (w.group(1), hgt.group(1))
        return out + ' loading="lazy">'
    h = re.sub(r"<img\b[^>]*>", fix_img, h)

    # Internal links -> sibling post pages; site root -> landing page.
    def fix_link(m):
        url = m.group(1)
        mm = re.match(r"https?://(?:www\.)?eupraxisconsulting\.com/?(.*?)/?$", url)
        if not mm:
            return m.group(0)
        path = mm.group(1)
        if path == "":
            return 'href="../index.html"'
        if path in slug_map:
            return 'href="%s.html"' % slug_map[path]
        return m.group(0)
    h = re.sub(r'href="([^"]+)"', fix_link, h)
    # Internal links should open in the same tab; drop target/rel left over from WP.
    h = re.sub(r'(<a href="(?:\.\./)?[\w\-]+\.html")[^>]*>', r"\1>", h)
    h = re.sub(r"\n[ \t]+", "\n", h)

    # Empty paragraphs and stray breaks.
    h = re.sub(r"<p>(?:\s|&nbsp;|<br\s*/?>)*</p>", "", h)
    h = re.sub(r"<p>\s*<br\s*/?>", "<p>", h)
    h = re.sub(r"[ \t]+\n", "\n", h)
    h = re.sub(r"\n{3,}", "\n\n", h).strip()
    return h, series


def main(posts_path, media_path, map_path):
    posts = json.load(open(posts_path, encoding="utf-8"))
    media = {m["id"]: m for m in json.load(open(media_path, encoding="utf-8"))}
    img_map = json.load(open(map_path, encoding="utf-8"))

    slug_map = {}
    for p in posts:
        slug_map[p["slug"]] = p["slug"]
        for a in ALIASES.get(p["slug"], []):
            slug_map[a] = p["slug"]

    os.makedirs(POSTS_DIR, exist_ok=True)
    for p in posts:
        slug = p["slug"]
        title = html.unescape(p["title"]["rendered"]).replace("–", "–").strip()
        cats = [CAT_MAP[c] for c in p["categories"] if c in CAT_MAP]
        cat = cats[0] if cats else "culture"
        yo = p.get("yoast_head_json") or {}
        desc = (yo.get("description") or strip_tags(p["excerpt"]["rendered"]))[:220].strip()
        body, series = clean_body(p["content"]["rendered"], img_map, slug_map)

        fm = ["---", "title: " + title, "date: " + p["date"][:10], "category: " + cat]
        if series:
            fm.append("series: " + series)
        fm.append("description: " + desc.replace("\n", " "))
        fmedia = media.get(p["featured_media"])
        if fmedia:
            fm.append("image: " + img_map.get(fmedia["source_url"], ""))
            fm.append("image_alt: " + (fmedia.get("alt_text") or title))
        if ALIASES.get(slug):
            fm.append("aliases: " + ", ".join(ALIASES[slug]))
        fm += ["format: html", "---", ""]

        with open(os.path.join(POSTS_DIR, slug + ".md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(fm) + body + "\n")
        print("wrote", slug, "|", cat, "|", series or "-")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
