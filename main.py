from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import os

TARGET_URL = 'https://sdd.tamabi.ac.jp/info'
BASE_URL = 'https://sdd.tamabi.ac.jp'

def scrape_dynamic_site():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print("ページにアクセスしています...")
        page.goto(TARGET_URL)
        page.wait_for_timeout(5000)
        
        html_content = page.content()
        browser.close()
        return html_content

def generate_rss(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    fg = FeedGenerator()
    fg.id(TARGET_URL)
    fg.title('多摩美術大学 SDD お知らせ')
    fg.link(href=TARGET_URL, rel='alternate')
    fg.description('演劇舞踊デザイン学科の最新情報')
    fg.language('ja')

    articles = soup.select('.wixui-repeater__item')
    print(f"取得した記事ブロック総数: {len(articles)}")

    # 1. 抽出した記事データを一時的に保存するリスト
    extracted_items = []

    for article in articles:
        title_tag = article.find('h2')
        date_tag = article.find('p')
        link_tag = article.find('a')
        
        # Wixの様々な画像タグに対応するための強化抽出ロジック
        image_url = ""
        img_tag = article.find('img')
        
        if img_tag:
            # 属性を複数チェックして最も可能性の高いURLを取得
            if img_tag.has_attr('src') and "http" in img_tag['src']:
                image_url = img_tag['src']
            elif img_tag.has_attr('data-src') and "http" in img_tag['data-src']:
                image_url = img_tag['data-src']
            elif img_tag.has_attr('srcset'):
                # srcsetの場合は最初のURLを取得
                image_url = img_tag['srcset'].split(' ')[0]

        if title_tag and link_tag and date_tag:
            title_text = title_tag.get_text(strip=True)
            link_url = link_tag['href']
            date_text = date_tag.get_text(strip=True)
            
            if link_url.startswith('/'):
                link_url = BASE_URL + link_url

            # 日付のパース
            parsed_date = None
            try:
                first_date = date_text.split('~')[0].split('〜')[0].strip()
                dt = datetime.strptime(first_date.replace('.', '/').replace('-', '/'), '%Y/%m/%d')
                jst = pytz.timezone('Asia/Tokyo')
                parsed_date = jst.localize(dt)
            except ValueError:
                pass
                
            # 日付が正しく取得できたものだけをリストに追加
            if parsed_date:
                extracted_items.append({
                    'title': title_text,
                    'link': link_url,
                    'date_text': date_text,
                    'date_obj': parsed_date,
                    'image_url': image_url
                })

    # 2. 記事リストを「日付の新しい順（降順）」に並び替える
    extracted_items.sort(key=lambda x: x['date_obj'], reverse=True)

    # 3. 並び替えた上位10件だけをRSSフィードに追加する
    for item in extracted_items[:10]:
        print("--------------------------------------------------")
        print(f"【日付】: {item['date_text']}")
        print(f"【タイトル】: {item['title']}")
        print(f"【URL】: {item['link']}")
        print(f"【画像】: {item['image_url']}")
        print("--------------------------------------------------\n")

        fe = fg.add_entry()
        fe.id(item['link'])
        fe.title(item['title'])
        fe.link(href=item['link'])
        fe.pubDate(item['date_obj'])
        
        if item['image_url']:
            fe.enclosure(item['image_url'], 0, 'image/jpeg')
            fe.description(f'<img src="{item["image_url"]}" style="max-width:100%;" /><br/><br/>{item["title"]}')
        else:
            fe.description(item['title'])

    os.makedirs('public', exist_ok=True)
    fg.rss_file('public/rss.xml')
    print("RSSフィード（public/rss.xml）の生成が完了しました！")

if __name__ == "__main__":
    html = scrape_dynamic_site()
    generate_rss(html)
