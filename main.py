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
    print(f"取得した記事ブロック総数: {len(articles)}")

    # 取得した記事ブロックのうち、上から10件だけをループ処理する
    for article in articles[:10]:
        title_tag = article.find('h2')
        date_tag = article.find('p')
        link_tag = article.find('a')
        
        # 👇 画像タグ（img）を取得
        img_tag = article.find('img')

        if title_tag and link_tag and date_tag:
            title_text = title_tag.get_text(strip=True)
            link_url = link_tag['href']
            date_text = date_tag.get_text(strip=True)
            
            if link_url.startswith('/'):
                link_url = BASE_URL + link_url

            # 👇 画像URLの抽出
            image_url = ""
            if img_tag and img_tag.has_attr('src'):
                image_url = img_tag['src']

            # ログ確認用の出力
            print("--------------------------------------------------")
            print(f"【日付】: {date_text}")
            print(f"【タイトル】: {title_text}")
            print(f"【URL】: {link_url}")
            print(f"【画像】: {image_url}")
            print("--------------------------------------------------\n")

            fe = fg.add_entry()
            fe.id(link_url)
            fe.title(title_text)
            fe.link(href=link_url)
            
            # 👇 画像URLがある場合、RSSの仕様に合わせて画像を添付する
            if image_url:
                # 1. RSS標準のEnclosure（添付要素）として画像を追加
                fe.enclosure(image_url, 0, 'image/jpeg')
                # 2. RSSリーダーの画面で直接画像が見えるように、description（概要）にHTMLタグで画像を埋め込む
                fe.description(f'<img src="{image_url}" style="max-width:100%;" /><br/><br/>{title_text}')
            else:
                fe.description(title_text)
            
            try:
                first_date = date_text.split('~')[0].split('〜')[0].strip()
                dt = datetime.strptime(first_date.replace('.', '/').replace('-', '/'), '%Y/%m/%d')
                jst = pytz.timezone('Asia/Tokyo')
                fe.pubDate(jst.localize(dt))
            except ValueError:
                pass

    os.makedirs('public', exist_ok=True)
    fg.rss_file('public/rss.xml')
    print("RSSフィード（public/rss.xml）の生成が完了しました！")
    
if __name__ == "__main__":
    html = scrape_dynamic_site()
    generate_rss(html)
