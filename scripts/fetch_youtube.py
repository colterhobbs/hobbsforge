#!/usr/bin/env python3
"""
Fetch latest videos from the Hobbs Forgeworks YouTube channel RSS feed
and generate the Hugo content/videos/_index.md page.

This script is designed to run in GitHub Actions on a schedule.
It uses the free YouTube RSS feed (no API key required).
"""

import xml.etree.ElementTree as ET
import urllib.request
import html
import os
from datetime import datetime

# Configuration
CHANNEL_ID = "UCn9RMAIKs1goL9TMpqHNg8A"
CHANNEL_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
MAX_VIDEOS = 12  # Maximum number of videos to display
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "videos", "_index.md")

# XML namespaces used in the YouTube RSS feed
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_feed():
    """Fetch and parse the YouTube RSS feed."""
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return ET.parse(response)


def parse_videos(tree):
    """Extract video data from the parsed RSS feed."""
    root = tree.getroot()
    videos = []

    for entry in root.findall("atom:entry", NAMESPACES):
        video_id = entry.find("yt:videoId", NAMESPACES).text
        title = entry.find("atom:title", NAMESPACES).text
        published = entry.find("atom:published", NAMESPACES).text
        link = entry.find("atom:link[@rel='alternate']", NAMESPACES).attrib["href"]

        # Get thumbnail and description from media:group
        media_group = entry.find("media:group", NAMESPACES)
        thumbnail = media_group.find("media:thumbnail", NAMESPACES).attrib["url"]
        description_el = media_group.find("media:description", NAMESPACES)
        description = description_el.text if description_el is not None and description_el.text else ""

        # Get view count
        stats = media_group.find("media:community/media:statistics", NAMESPACES)
        views = stats.attrib.get("views", "0") if stats is not None else "0"

        # Determine if it's a short or regular video
        is_short = "/shorts/" in link

        # Parse the published date
        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))

        videos.append({
            "id": video_id,
            "title": title,
            "published": pub_date,
            "published_str": pub_date.strftime("%B %d, %Y"),
            "link": link,
            "thumbnail": thumbnail,
            "description": description,
            "views": views,
            "is_short": is_short,
        })

    return videos[:MAX_VIDEOS]


def clean_title(title):
    """Remove hashtags from title for cleaner display."""
    # Remove hashtag words from the end of the title
    parts = title.split()
    cleaned = []
    for part in parts:
        if part.startswith("#"):
            continue
        cleaned.append(part)
    result = " ".join(cleaned).strip()
    # Remove trailing punctuation artifacts
    while result and result[-1] in (",", " "):
        result = result[:-1]
    return result if result else title


def escape_md(text):
    """Escape special characters for Markdown/Hugo."""
    return text.replace('"', '\\"').replace("`", "\\`")


def generate_markdown(videos):
    """Generate the Hugo Markdown content for the videos page."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("---")
    lines.append('title: "Videos"')
    lines.append('description: "Forging sessions and build videos from Hobbs Forgeworks."')
    lines.append("toc: false")
    lines.append("---")
    lines.append("")
    lines.append("New videos go up regularly — forge schedule and Alaska weather permitting.")
    lines.append("")
    lines.append(f'{{{{< hextra/hero-button text="Subscribe on YouTube" link="{CHANNEL_URL}" >}}}}')
    lines.append("")

    if not videos:
        lines.append("No videos found. Check back soon!")
        lines.append("")
        return "\n".join(lines)

    # Latest video as featured embed
    latest = videos[0]
    lines.append("---")
    lines.append("")
    lines.append("## Latest Video")
    lines.append("")
    lines.append(f'{{{{< youtube "{latest["id"]}" >}}}}')
    lines.append("")
    clean = clean_title(latest["title"])
    lines.append(f'**{clean}**')
    if latest["description"]:
        lines.append(f'— {latest["description"]}')
    lines.append(f'  ')
    lines.append(f'*Published {latest["published_str"]} · {int(latest["views"]):,} views*')
    lines.append("")

    # Remaining videos as a grid
    remaining = videos[1:]
    if remaining:
        lines.append("---")
        lines.append("")
        lines.append("## More Videos")
        lines.append("")

        # Use an HTML grid for SEO-rich video cards with thumbnails
        lines.append('<div class="hx:grid hx:grid-cols-1 sm:hx:grid-cols-2 lg:hx:grid-cols-3 hx:gap-6 hx:mt-4">')
        for video in remaining:
            clean = clean_title(video["title"])
            escaped_title = html.escape(clean)
            escaped_desc = html.escape(video["description"])
            vid_link = video["link"]
            thumb = f"https://i.ytimg.com/vi/{video['id']}/mqdefault.jpg"

            lines.append(f'<a href="{vid_link}" target="_blank" rel="noopener noreferrer" class="hx:group hx:block hx:rounded-lg hx:border hx:border-gray-200 hx:dark:border-neutral-800 hx:overflow-hidden hx:hover:shadow-md hx:hover:border-gray-300 hx:dark:hover:border-neutral-700 hx:transition-all hx:duration-200 hx:no-underline">')
            lines.append(f'  <img src="{thumb}" alt="{escaped_title}" class="hx:w-full hx:aspect-video hx:object-cover" loading="lazy" />')
            lines.append(f'  <div class="hx:p-3">')
            lines.append(f'    <p class="hx:font-semibold hx:text-sm hx:text-gray-800 hx:dark:text-gray-200 hx:line-clamp-2 hx:m-0">{escaped_title}</p>')
            lines.append(f'    <p class="hx:text-xs hx:text-gray-500 hx:dark:text-gray-400 hx:mt-1 hx:m-0">{video["published_str"]} · {int(video["views"]):,} views</p>')
            lines.append(f'  </div>')
            lines.append(f'</a>')

        lines.append('</div>')
        lines.append("")

    # Channel link at the bottom
    lines.append("---")
    lines.append("")
    lines.append(f'See all videos on the [Hobbs Forgeworks YouTube channel]({CHANNEL_URL}).')
    lines.append("")
    lines.append(f'<!-- Auto-generated by fetch_youtube.py on {now} -->')
    lines.append("")

    return "\n".join(lines)


def main():
    print(f"Fetching YouTube feed for channel {CHANNEL_ID}...")
    tree = fetch_feed()

    print("Parsing video entries...")
    videos = parse_videos(tree)
    print(f"Found {len(videos)} videos")

    for v in videos:
        short_tag = " [SHORT]" if v["is_short"] else ""
        print(f"  - {v['title'][:60]}{short_tag} ({v['published_str']})")

    print(f"\nGenerating Markdown content...")
    content = generate_markdown(videos)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done!")


if __name__ == "__main__":
    main()
