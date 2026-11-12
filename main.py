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
        # ユーザーエージェントを偽装してBot検知を回避
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print("ページにアクセスしています...")
        page.goto(TARGET_URL)
        page.wait_for_timeout(5000) # Wixの描画完了を待つ
        
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

    # WixのRepeater要素（記事ブロック）を取得
    articles = soup.select('.wixui-repeater__item')
    print(f"取得した記事ブロック数: {len(articles)}")

    for article in articles:
        # aタグ（moreボタンを除く）からタイトルとリンクを取得
        title_tags = article.select('a:not(.wixui-button)')
        link_tag = None
        for tag in title_tags:
            if tag.get_text(strip=True):
                link_tag = tag
                break
                
        # pタグから日付を取得
        date_tags = article.select('p')
        date_tag = None
        for tag in date_tags:
            if tag.get_text(strip=True):
                date_tag = tag
                break

        if link_tag and date_tag:
            title_text = link_tag.get_text(strip=True)
            link_url = link_tag['href']
            date_text = date_tag.get_text(strip=True)
            
            if link_url.startswith('/'):
                link_url = BASE_URL + link_url

            fe = fg.add_entry()
            fe.id(link_url)
            fe.title(title_text)
            fe.link(href=link_url)
            
            try:
                dt = datetime.strptime(date_text.replace('.', '/').replace('-', '/'), '%Y/%m/%d')
                jst = pytz.timezone('Asia/Tokyo')
                fe.pubDate(jst.localize(dt))
            except ValueError:
                pass

    # 出力先を public ディレクトリに指定（GitHub Pages用）
    os.makedirs('public', exist_ok=True)
    fg.rss_file('public/rss.xml')
    print("RSSフィード（public/rss.xml）の生成が完了しました！")

if __name__ == "__main__":
    html = scrape_dynamic_site()
    generate_rss(html)
