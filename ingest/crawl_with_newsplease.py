import os, json
import feedparser
from newsplease import NewsPlease

# Paths
BASE_DIR     = os.path.dirname(__file__)
FEEDS_FILE   = os.path.join(BASE_DIR, "../data/raw/rss_feeds.txt")
OUTPUT_JSON  = os.path.join(BASE_DIR, "../data/raw/news_full.json")

def load_feed_urls():
    with open(FEEDS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def fetch_article_urls(feed_urls, max_per_feed=50):
    urls = set()
    for feed in feed_urls:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries[:max_per_feed]:
            urls.add(entry.link)
    return list(urls)

def crawl_and_save(article_urls, batch_size=100):
    # NewsPlease.from_urls can take hundreds, but let's batch in case of timeouts
    all_articles = []
    for i in range(0, len(article_urls), batch_size):
        batch = article_urls[i : i + batch_size]
        print(f"🕸️  Crawling batch {i // batch_size + 1} ({len(batch)} URLs)…")
        articles = NewsPlease.from_urls(batch, request_args={"timeout": 10})
        for url, art in articles.items():
            if art and art.maintext:
                all_articles.append({
                    "title":     art.title,
                    "text":      art.maintext,
                    "url":       art.url,
                    "published": art.date_publish.isoformat() if art.date_publish else ""
                })
    # Deduplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen:
            unique.append(a)
            seen.add(a["url"])
    # Write out
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved {len(unique)} articles to {OUTPUT_JSON}")

if __name__ == "__main__":
    feeds = load_feed_urls()
    urls  = fetch_article_urls(feeds, max_per_feed=50)  # adjust per-feed cap
    print(f"Found {len(urls)} unique article URLs")
    crawl_and_save(urls, batch_size=50)
