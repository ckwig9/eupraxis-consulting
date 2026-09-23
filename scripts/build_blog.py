"""Build the blog from posts/*.md.

Usage (from the project root):
    python scripts/build_blog.py

What it does:
  1. Reads every posts/<slug>.md (front matter + Markdown or HTML body).
  2. Writes blog/<slug>.html from templates/post.html, wrapped in the site's
     shared header/footer (taken from blog.html so there is one source of truth).
  3. Rewrites the post list in blog.html between <!-- entries:start --> and
     <!-- entries:end -->, and the category filter buttons between
     <!-- filters:start --> and <!-- filters:end -->.
  4. Rewrites the latest three posts on index.html between
     <!-- posts:start --> and <!-- posts:end -->.
  5. Writes feed.xml (RSS) and the redirect rules in _redirects and .htaccess
     so old WordPress URLs land on the new pages.

Front matter keys:
  title        required
  date         required, YYYY-MM-DD
  category     required, one of CATEGORIES below
  description  recommended, one or two sentences (used for the list and SEO)
  series       optional, e.g. "CEO series, part 5"
  image        optional, path under assets/blog/ (featured image, 4:3 works best)
  image_alt    optional
  aliases      optional, comma-separated old URL paths to redirect from
  format       optional, "html" to skip Markdown conversion (migrated posts)
  draft        optional, "true" to keep the post out of the build

Requires: pip install markdown
"""
import html
import os
import re
import sys
from datetime import datetime

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.exit("The 'markdown' package is required: pip install markdown")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")
OUT_DIR = os.path.join(ROOT, "blog")
TEMPLATE = os.path.join(ROOT, "templates", "post.html")
SITE_URL = "https://eupraxisconsulting.com"
AUTHOR = "Craig Wigginton"

# Category key -> label. Order here is the order of the filter buttons.
CATEGORIES = {
    "run-outgrow": "Run Outgrow",
    "culture": "Culture & Mindset",
    "proactive": "Proactive Communications",
    "outgrow-system": "Outgrow Selling System",
}

ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 8h10M9 4l4 4-4 4"/></svg>'


def esc(s):
    return html.escape(s or "", quote=True)


def read_file(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write_file(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def parse_post(path):
    raw = read_file(path)
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not m:
        sys.exit("%s: missing front matter" % path)
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for k in ("title", "date", "category"):
        if k not in meta:
            sys.exit("%s: front matter needs '%s'" % (path, k))
    if meta["category"] not in CATEGORIES:
        sys.exit("%s: unknown category '%s' (use one of %s)" % (path, meta["category"], ", ".join(CATEGORIES)))
    meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    meta["date_obj"] = datetime.strptime(meta["date"], "%Y-%m-%d")
    meta["aliases"] = [a.strip().strip("/") for a in meta.get("aliases", "").split(",") if a.strip()]
    body = m.group(2).strip()
    if meta.get("format", "").lower() == "html":
        meta["body"] = body
    else:
        meta["body"] = markdown.markdown(body, extensions=["extra", "sane_lists"])
    words = len(re.sub(r"<[^>]+>", " ", meta["body"]).split())
    meta["read_time"] = max(1, round(words / 220))
    if not meta.get("description"):
        first = re.search(r"<p>(.*?)</p>", meta["body"], re.S)
        meta["description"] = re.sub(r"<[^>]+>", "", first.group(1))[:200] if first else ""
    return meta


def date_human(d):
    return d.strftime("%b %d, %Y").replace(" 0", " ")


def cat_line(p):
    label = CATEGORIES[p["category"]]
    return label + (" &middot; " + esc(p["series"]) if p.get("series") else "")


# ---------- shared chrome (header/footer) from blog.html ----------
def chrome_from_blog_index(prefix):
    src = read_file(os.path.join(ROOT, "blog.html"))
    top = re.search(r"(<svg width=\"0\".*?)<main>", src, re.S).group(1)
    bottom = re.search(r"(<footer.*?)</body>", src, re.S).group(1)

    def relink(s):
        s = re.sub(r'(href|src)="(?!https?:|mailto:|tel:|#|\.\./)([^"]+)"', lambda m: '%s="%s%s"' % (m.group(1), prefix, m.group(2)), s)
        return s
    top, bottom = relink(top), relink(bottom)
    # Blog is the active section on post pages.
    top = top.replace('href="%sblog.html"' % prefix, 'href="%sblog.html" class="is-active"' % prefix, 1)
    top = top.replace('class="is-active" class="is-active"', 'class="is-active"')
    return top, bottom


# ---------- card / entry markup ----------
def post_card(p, prefix):
    return (
        '      <article class="post" data-reveal>\n'
        '        <div class="meta"><span class="cat">%s</span><time datetime="%s">%s</time></div>\n'
        '        <h3>%s</h3>\n'
        '        <p>%s</p>\n'
        '        <span class="more">Read %s</span>\n'
        '        <a class="cover" href="%sblog/%s.html" aria-label="Read: %s"></a>\n'
        '      </article>\n'
    ) % (CATEGORIES[p["category"]], p["date"], date_human(p["date_obj"]), esc(p["title"]), esc(p["description"]), ARROW, prefix, p["slug"], esc(p["title"]))


def blog_entry(p):
    return (
        '      <article class="entry" data-cat="%s" data-reveal>\n'
        '        <time class="date" datetime="%s">%s</time>\n'
        '        <div><span class="cat">%s</span>\n'
        '          <h2>%s</h2>\n'
        '          <p>%s</p></div>\n'
        '        <span class="arrow">%s</span>\n'
        '        <a class="cover" href="blog/%s.html" aria-label="Read post"></a>\n'
        '      </article>\n\n'
    ) % (p["category"], p["date"], date_human(p["date_obj"]), cat_line(p), esc(p["title"]), esc(p["description"]), ARROW, p["slug"])


def replace_between(src, start, end, new, path):
    if start not in src or end not in src:
        sys.exit("%s: markers %s / %s not found" % (path, start, end))
    a = src.index(start) + len(start)
    b = src.index(end)
    return src[:a] + "\n" + new + src[b:]


# ---------- post pages ----------
def render_post(p, posts, tpl, top, bottom):
    body = re.sub(r'(src|href)="assets/', r'\1="../assets/', p["body"])
    others = [o for o in posts if o["slug"] != p["slug"]]
    related = [o for o in others if o["category"] == p["category"]][:3]
    for o in others:
        if len(related) >= 3:
            break
        if o not in related:
            related.append(o)
    related_html = "".join(post_card(o, "../") for o in related)

    hero_img = ""
    og_image = "../assets/brand/craig-headshot.jpeg"
    if p.get("image"):
        og_image = "../" + p["image"]
        hero_img = '<figure class="post-figure" data-reveal="fade"><img src="../%s" alt="%s" width="1200" height="900" fetchpriority="high"></figure>' % (esc(p["image"]), esc(p.get("image_alt") or p["title"]))

    out = tpl
    for k, v in {
        "TITLE": esc(p["title"]),
        "DESCRIPTION": esc(p["description"]),
        "OG_IMAGE": og_image,
        "CANONICAL": "%s/blog/%s.html" % (SITE_URL, p["slug"]),
        "CAT_LINE": cat_line(p),
        "CAT_KEY": p["category"],
        "DATE_ISO": p["date"],
        "DATE_HUMAN": date_human(p["date_obj"]),
        "READ_TIME": str(p["read_time"]),
        "HERO_IMAGE": hero_img,
        "BODY": body,
        "RELATED": related_html,
        "CHROME_TOP": top,
        "CHROME_BOTTOM": bottom,
    }.items():
        out = out.replace("{{%s}}" % k, v)
    return out


# ---------- feed + redirects ----------
def rss(posts):
    items = []
    for p in posts[:20]:
        url = "%s/blog/%s.html" % (SITE_URL, p["slug"])
        items.append(
            "  <item>\n    <title>%s</title>\n    <link>%s</link>\n    <guid>%s</guid>\n    <pubDate>%s</pubDate>\n    <description>%s</description>\n  </item>"
            % (esc(p["title"]), url, url, p["date_obj"].strftime("%a, %d %b %Y 08:00:00 +0000"), esc(p["description"]))
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
        "  <title>Eupraxis Consulting blog</title>\n  <link>%s/blog.html</link>\n"
        "  <description>Craig Wigginton on organic growth, sales culture, and the habits that make leadership teams grow.</description>\n%s\n</channel></rss>\n"
        % (SITE_URL, "\n".join(items))
    )


def redirects(posts):
    rows = []
    for p in posts:
        for old in [p["slug"]] + p["aliases"]:
            rows.append((old, p["slug"]))
    netlify = ["# Generated by scripts/build_blog.py. Old WordPress URLs -> new post pages.", "/feed/  /feed.xml  301"]
    apache = ["# Generated by scripts/build_blog.py. Old WordPress URLs -> new post pages.", "Redirect 301 /feed/ /feed.xml"]
    for old, new in rows:
        netlify.append("/%s/  /blog/%s.html  301" % (old, new))
        netlify.append("/%s  /blog/%s.html  301" % (old, new))
        apache.append("Redirect 301 /%s/ /blog/%s.html" % (old, new))
    return "\n".join(netlify) + "\n", "\n".join(apache) + "\n"


def main():
    files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    posts = [parse_post(os.path.join(POSTS_DIR, f)) for f in files]
    posts = [p for p in posts if p.get("draft", "").lower() != "true"]
    posts.sort(key=lambda p: (p["date_obj"], p["slug"]), reverse=True)
    if not posts:
        sys.exit("No posts found in posts/")

    tpl = read_file(TEMPLATE)
    top, bottom = chrome_from_blog_index("../")

    # Remove pages for posts that no longer exist.
    if os.path.isdir(OUT_DIR):
        keep = {p["slug"] + ".html" for p in posts}
        for f in os.listdir(OUT_DIR):
            if f.endswith(".html") and f not in keep:
                os.remove(os.path.join(OUT_DIR, f))
    for p in posts:
        write_file(os.path.join(OUT_DIR, p["slug"] + ".html"), render_post(p, posts, tpl, top, bottom))

    # blog.html list + filters
    bp = os.path.join(ROOT, "blog.html")
    src = read_file(bp)
    used = [k for k in CATEGORIES if any(p["category"] == k for p in posts)]
    filters = '      <button class="is-active" data-cat="all" type="button">All posts</button>\n' + "".join(
        '      <button data-cat="%s" type="button">%s</button>\n' % (k, CATEGORIES[k].replace("&", "&amp;")) for k in used
    )
    src = replace_between(src, "<!-- filters:start -->", "<!-- filters:end -->", filters + "      ", bp)
    src = replace_between(src, "<!-- entries:start -->", "<!-- entries:end -->", "".join(blog_entry(p) for p in posts) + "      ", bp)
    write_file(bp, src)

    # index.html latest three
    ip = os.path.join(ROOT, "index.html")
    src = read_file(ip)
    src = replace_between(src, "<!-- posts:start -->", "<!-- posts:end -->", "".join(post_card(p, "") for p in posts[:3]) + "      ", ip)
    write_file(ip, src)

    write_file(os.path.join(ROOT, "feed.xml"), rss(posts))
    n, a = redirects(posts)
    write_file(os.path.join(ROOT, "_redirects"), n)
    write_file(os.path.join(ROOT, ".htaccess"), a)
    vercel_redirects(posts)
    print("built %d posts -> blog/, blog.html, index.html, feed.xml, _redirects, .htaccess, vercel.json" % len(posts))


def vercel_redirects(posts):
    """Vercel ignores _redirects; it reads a 'redirects' list in vercel.json.
    Other keys in vercel.json (cleanUrls, trailingSlash, ...) are preserved."""
    import json
    vp = os.path.join(ROOT, "vercel.json")
    conf = json.loads(read_file(vp)) if os.path.exists(vp) else {"cleanUrls": True, "trailingSlash": False}
    rules = [{"source": "/feed", "destination": "/feed.xml", "permanent": True}]
    for p in posts:
        for old in [p["slug"]] + p["aliases"]:
            rules.append({"source": "/" + old, "destination": "/blog/" + p["slug"], "permanent": True})
    conf["redirects"] = rules
    write_file(vp, json.dumps(conf, indent=2) + "\n")


if __name__ == "__main__":
    main()
