from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home_page():
    # Initially, we fetch the first set of articles (starting from archive/2)
    articles = await fetch_titles(counter=2)
    list_items = ''.join(
        f'<li><a href="{article["url"]}" target="_blank">{article["title"]}</a> — {article["datetime"]}</li>'
        for article in articles
    )
    
    if not articles:
        load_more_button = ''
    else:
        load_more_button = '<div class="load-more-button"><button id="load-more" onclick="loadMore()" class="load-more-button">Load More</button></div>'

    content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>The Verge Title Aggregator</title>
        <link rel="stylesheet" type="text/css" href="/static/style.css" />
        <script>
            let currentCounter = 2;

            async function loadMore() {{
                currentCounter += 1;
                const response = await fetch(`/fetch-titles?counter=${{currentCounter}}`);
                const data = await response.json();

                if (data.length === 0) {{
                    document.getElementById('load-more').style.display = 'none';
                    return;
                }}

                const ul = document.querySelector('ul');
                let listItems = '';
                data.forEach(article => {{
                    listItems += `<li><a href="${{article.url}}" target="_blank">${{article.title}}</a> — ${{article.datetime}}</li>`;
                }});

                // Append new articles to the list
                ul.innerHTML += listItems;

                // Move the "Load More" button below the last article
                const loadMoreButton = document.getElementById('load-more');
                ul.appendChild(loadMoreButton);
            }}
        </script>
    </head>
    <body>
        <h1>The Verge Feature Articles</h1>
        <ul class="article-list">
            {list_items}
        </ul>
        {load_more_button}
    </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.get("/fetch-titles")
async def fetch_titles(counter: int):
    base_url = "https://www.theverge.com/archives/"
    results = []

    # Date threshold: January 1, 2022 (make it timezone-aware)
    date_threshold = datetime(2022, 1, 1, tzinfo=pytz.UTC)

    url = f"{base_url}{counter}"
    print(f"Fetching articles from: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    articles_on_page = False

    # Targeting the <a> tags with the relevant class and extracting title and datetime
    for article_div in soup.select('a._1lkmsmo1'):
        href = article_div.get('href')
        title = article_div.get_text(strip=True)

        # Find the closest time tag
        time_tag = article_div.find_parent().find_next('time')

        if href and title and time_tag:
            datetime_str = time_tag.get('datetime', '')
            article_datetime = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))

            # Check if the article is newer than January 2022
            if article_datetime < date_threshold:
                print(f"Found an article older than Jan 2022: {title}")
                return results  # Stop fetching as soon as we find an article older than Jan 2022
            
            # Store the article if it meets the criteria
            full_url = f"https://www.theverge.com{href}" if href.startswith('/') else href
            results.append({
                "title": title,
                "url": full_url,
                "datetime": article_datetime.strftime('%Y-%m-%d')
            })
            articles_on_page = True

    # If no articles found on the page, stop fetching
    if not articles_on_page:
        return []

    return results
