import requests
from bs4 import BeautifulSoup

url = "https://bntnews.bg/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# We target the main news containers found in your HTML
# This covers the 'Top News' and the 'Regular' news boxes
articles = soup.select(".top-news, .news-box-regular")

feed_data = []

for article in articles:
    # 1. Try to find the title link (BNT uses specific classes for different sizes)
    title_tag = article.select_one(".big-title a, .medium-title, .small-title")

    if not title_tag:
        continue

    title = title_tag.get_text(strip=True)

    # 2. Get the URL (it might be the title_tag itself or a parent <a>)
    link = (
        title_tag.get("href")
        if title_tag.name == "a"
        else title_tag.find("a").get("href")
    )

    # 3. Get the Summary (sub-title)
    summary_tag = article.select_one(".sub-title")
    summary = summary_tag.get_text(strip=True) if summary_tag else ""

    # 4. Get the Time
    time_tag = article.select_one("time.news-time")
    timestamp = time_tag.get_text(strip=True) if time_tag else ""

    # Clean up absolute vs relative URLs
    if link and not link.startswith("http"):
        link = f"https://bntnews.bg{link}"

    # Avoid adding duplicates (common in BNT's sidebars)
    if link and not any(item["link"] == link for item in feed_data):
        feed_data.append(
            {"title": title, "link": link, "summary": summary, "time": timestamp}
        )

# Display Results
for item in feed_data:
    print(f"[{item['time']}] {item['title']}")
    print(f"URL: {item['link']}\n")
