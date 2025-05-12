import json
import os
import re

# Define input and output paths
PROCESSED_DIR = r"C:\news-chatbot\backend\data\processed"
RAW_DIR = r"C:\news-chatbot\backend\data\raw"

IN_FILE = os.path.join(RAW_DIR, 'news_full.json')
OUT_FILE = os.path.join(PROCESSED_DIR, 'passages.jsonl')

# Ensure output directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Regular expression for sentence splitting
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[\.!?])\s+')

def split_into_passages():
    # Load full articles
    print(f"Loading articles from {IN_FILE}")
    try:
        with open(IN_FILE, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} articles")
    except Exception as e:
        print(f"Error loading {IN_FILE}: {e}")
        exit(1)

    # Check for duplicate URLs
    url_counts = {}
    for art in articles:
        url = art.get('url', 'unknown')
        url_counts[url] = url_counts.get(url, 0) + 1
    duplicates = {url: count for url, count in url_counts.items() if count > 1}
    if duplicates:
        print(f"Warning: Found duplicate URLs in {IN_FILE}: {duplicates}")

    total_passages = 0
    with open(OUT_FILE, 'w', encoding='utf-8') as out:
        for art_idx, art in enumerate(articles):
            text = art.get('text', '').strip()
            url = art.get('url', f'unknown_{art_idx}')
            if not text:
                print(f"Skipping article {art_idx} ({url}): empty text")
                continue

            # Split into sentences using regex
            sentences = SENTENCE_SPLIT_REGEX.split(text)
            chunk, count = [], 0
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                chunk.append(sentence)
                # Once chunk reaches ~150 words, write it out
                if len(' '.join(chunk).split()) >= 150:
                    passage_id = f"{url}#{art_idx}_{count}"
                    record = {
                        'id': passage_id,
                        'text': ' '.join(chunk),
                        'source': url,
                        'published': art.get('published', '')
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + '\n')
                    total_passages += 1
                    count += 1
                    chunk = []
            # Write any leftover text as final passage
            if chunk:
                passage_id = f"{url}#{art_idx}_{count}"
                record = {
                    'id': passage_id,
                    'text': ' '.join(chunk),
                    'source': url,
                    'published': art.get('published', '')
                }
                out.write(json.dumps(record, ensure_ascii=False) + '\n')
                total_passages += 1

    print(f"Wrote {total_passages} passages to {OUT_FILE}")

if __name__ == '__main__':
    split_into_passages()