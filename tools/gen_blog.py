#!/usr/bin/env python3
"""Build the blog: blog/<slug>.html for each post, blog/index.html and blog/feed.xml.

Usage: python3 tools/gen_blog.py [SITE_DIR]
Posts are Markdown files in posts/, named <slug>.md, starting with a header block:

    title: Run Containers as systemd Services with Podman Quadlets
    date: 2026-10-19
    description: One sentence for the blog index, search results and link previews.
    ---

The header, footer, colors and fonts come from index.html, so the blog keeps the
homepage's look when that changes. Needs python3-markdown. After running, copy blog/
to /var/www/html/blog/.
"""
import datetime
import html
import os
import re
import sys

import markdown

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://cropseyit.com'
AUTHOR = 'Mike Cropsey'
POSTS = f'{SITE}/posts'
OUT = f'{SITE}/blog'

e = html.escape
home = open(f'{SITE}/index.html', encoding='utf-8').read()


def rooted(markup):
    """Make the homepage's relative links work from /blog/: page.html -> /page.html, #x -> /#x."""
    markup = re.sub(r'(href|src)="#', r'\1="/#', markup)
    return re.sub(r'(href|src)="(?![a-z]+:|/)', r'\1="/', markup)


css = re.search(r'<style>(.*?)</style>', home, re.S).group(1)
TOKENS = css[:css.index('* {')]                                    # :root colors, light and dark
CHROME = css[css.index('* {'):css.index('/* Hero */')]             # reset, body, header, nav
FOOTER_CSS = '\n' + css[css.index('    footer {'):]
HEADER = rooted(re.search(r'<header>.*?</header>', home, re.S).group(0))
FOOTER = rooted(re.search(r'<footer>.*?</footer>', home, re.S).group(0))

STYLE = TOKENS + CHROME + FOOTER_CSS + '''
    main { padding: 3rem 0 4rem; }
    .narrow { max-width: 46rem; }
    .kicker { font-family: var(--mono); font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--cyan); margin-bottom: 0.5rem; }
    .kicker a { color: inherit; }
    h1 { font-size: clamp(1.7rem, 4vw, 2.4rem); font-weight: 750; line-height: 1.15; letter-spacing: -0.025em; text-wrap: balance; }
    .meta { color: var(--text-muted); font-size: 0.92rem; margin: 0.75rem 0 2.25rem; }
    article h2 { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.015em; margin: 2.5rem 0 0.75rem; line-height: 1.25; }
    article h3 { font-size: 1.12rem; font-weight: 650; margin: 1.75rem 0 0.5rem; }
    article p, article ul, article ol, article table, article blockquote { margin-bottom: 1rem; }
    article ul, article ol { padding-left: 1.4rem; }
    article li { margin-top: 0.3rem; }
    article code { font-family: var(--mono); font-size: 0.88em; background: var(--surface-2); border: 1px solid var(--border); border-radius: 4px; padding: 0.05em 0.3em; overflow-wrap: anywhere; }
    article pre { position: relative; background: #0a1430; color: #e8eefc; border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 1.1rem; overflow-x: auto; font-size: 0.86rem; line-height: 1.55; }
    article pre code { background: none; border: 0; padding: 0; font-size: inherit; color: inherit; overflow-wrap: normal; }
    article pre .copy { position: absolute; top: 0.5rem; right: 0.5rem; font: 600 0.72rem system-ui, sans-serif; color: #a9b6d6; background: #16213a; border: 1px solid #23304d; border-radius: 6px; padding: 0.2rem 0.55rem; cursor: pointer; }
    article pre .copy:hover { color: #fff; }
    article blockquote { border-left: 3px solid var(--cyan); background: var(--surface); padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; color: var(--text-muted); }
    article blockquote p:last-child { margin-bottom: 0; }
    .tablewrap { overflow-x: auto; margin-bottom: 1.1rem; }
    article table { border-collapse: collapse; width: 100%; font-size: 0.93rem; margin: 0; }
    article th, article td { text-align: left; vertical-align: top; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--border); }
    article th { background: var(--surface); font-weight: 650; }
    article td:first-child code { white-space: nowrap; }
    .posts { list-style: none; }
    .posts li { padding: 1.4rem 0; border-bottom: 1px solid var(--border); }
    .posts li:first-child { padding-top: 0; }
    .posts h2 { font-size: 1.25rem; font-weight: 680; letter-spacing: -0.01em; margin: 0.2rem 0 0.35rem; }
    .posts time { color: var(--text-muted); font-size: 0.88rem; font-family: var(--mono); }
    .posts p { color: var(--text-muted); }
    .back { margin-top: 3rem; font-size: 0.95rem; }
'''

SCRIPT = '''<script>
document.getElementById('year').textContent = new Date().getFullYear();
document.querySelectorAll('article pre').forEach(function (pre) {
  var b = document.createElement('button');
  b.className = 'copy'; b.type = 'button'; b.textContent = 'Copy';
  b.addEventListener('click', function () {
    navigator.clipboard.writeText(pre.querySelector('code').innerText).then(function () {
      b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy'; }, 1500);
    });
  });
  pre.appendChild(b);
});
</script>'''


def page(title, description, path, body, og_type='website'):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}">
  <meta name="author" content="{AUTHOR}">
  <link rel="canonical" href="{URL}{path}">
  <link rel="icon" href="/favicon.png" type="image/png">
  <link rel="alternate" type="application/rss+xml" title="Cropsey IT Blog" href="/blog/feed.xml">
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="Cropsey IT Solutions, LLC">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{URL}{path}">
  <meta property="og:image" content="{URL}/logo.png">
  <meta name="twitter:card" content="summary">
  <style>{STYLE}  </style>
</head>
<body>
  {HEADER}

  <main>
    <div class="container narrow">
{body}
    </div>
  </main>

  {FOOTER}

  {SCRIPT}
</body>
</html>
'''


def load(name):
    text = open(f'{POSTS}/{name}', encoding='utf-8').read()
    head, body = text.split('\n---\n', 1)
    meta = dict(line.split(': ', 1) for line in head.strip().split('\n'))
    for key in ('title', 'date', 'description'):
        if key not in meta:
            sys.exit(f'{name}: missing "{key}:" in the header block')
    meta['slug'] = name[:-3]
    meta['date'] = datetime.date.fromisoformat(meta['date'])
    content = markdown.markdown(body, extensions=['fenced_code', 'tables', 'toc'])
    meta['html'] = content.replace('<table>', '<div class="tablewrap"><table>').replace('</table>', '</table></div>')
    return meta


def nice(d):
    return f'{d:%B} {d.day}, {d.year}'


posts = sorted((load(n) for n in os.listdir(POSTS) if n.endswith('.md')), key=lambda p: p['date'], reverse=True)
os.makedirs(OUT, exist_ok=True)

for p in posts:
    body = f'''      <article>
        <p class="kicker"><a href="/blog/">Blog</a></p>
        <h1>{e(p['title'])}</h1>
        <p class="meta">{AUTHOR} &middot; <time datetime="{p['date']}">{nice(p['date'])}</time></p>
{p['html']}
      </article>
      <p class="back"><a href="/blog/">&larr; All posts</a> &middot; <a href="/#contact">Work with me</a></p>'''
    with open(f'{OUT}/{p["slug"]}.html', 'w', encoding='utf-8') as f:
        f.write(page(p['title'], p['description'], f'/blog/{p["slug"]}.html', body, 'article'))

items = '\n'.join(f'''        <li>
          <time datetime="{p['date']}">{nice(p['date'])}</time>
          <h2><a href="/blog/{p['slug']}.html">{e(p['title'])}</a></h2>
          <p>{e(p['description'])}</p>
        </li>''' for p in posts)
body = f'''      <p class="kicker">Blog</p>
      <h1>Notes from the lab</h1>
      <p class="meta">Linux, containers, networking and AI security, worked through on real systems. <a href="/blog/feed.xml">RSS feed</a></p>
      <ul class="posts">
{items}
      </ul>'''
with open(f'{OUT}/index.html', 'w', encoding='utf-8') as f:
    f.write(page('Blog | Cropsey IT Solutions', 'Linux, containers, networking and AI security, worked through on real systems.', '/blog/', body))

rss_items = '\n'.join(f'''    <item>
      <title>{e(p['title'])}</title>
      <link>{URL}/blog/{p['slug']}.html</link>
      <guid>{URL}/blog/{p['slug']}.html</guid>
      <pubDate>{datetime.datetime.combine(p['date'], datetime.time(12)):%a, %d %b %Y %H:%M:%S} +0000</pubDate>
      <description>{e(p['description'])}</description>
    </item>''' for p in posts)
with open(f'{OUT}/feed.xml', 'w', encoding='utf-8') as f:
    f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Cropsey IT Blog</title>
    <link>{URL}/blog/</link>
    <description>Linux, containers, networking and AI security, worked through on real systems.</description>
    <language>en-us</language>
{rss_items}
  </channel>
</rss>
''')

print(f'Wrote {len(posts)} post(s), blog/index.html and blog/feed.xml')
