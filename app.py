import sqlite3
from flask import Flask, render_template, redirect, url_for, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    # Создание таблицы для новостей с Хабра
    c.execute('''CREATE TABLE IF NOT EXISTS articles
                 (id INTEGER PRIMARY KEY, title TEXT, link TEXT UNIQUE)''')
    # Создание таблицы для новостей с Tproger
    c.execute('''CREATE TABLE IF NOT EXISTS tproger_articles
                 (id INTEGER PRIMARY KEY, title TEXT, link TEXT UNIQUE)''')
    conn.commit()
    conn.close()

def update_articles():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get('https://habr.com/ru/feed/')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'tm-title__link'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit()

    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    for title_tag in soup.find_all('a', class_='tm-title__link'):
        title = title_tag.text.strip()
        link = 'https://habr.com' + title_tag['href']
        try:
            c.execute('INSERT OR IGNORE INTO articles (title, link) VALUES (?, ?)', (title, link))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

def update_tproger_articles():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get('https://tproger.ru/')
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'tp-ui-post-card__link'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit()

    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    for link_tag in soup.find_all('a', class_='tp-ui-post-card__link'):
        title = link_tag.text.strip()
        link = 'https://tproger.ru' + link_tag['href']

        # Проверка на уникальность URL в базе данных
        c.execute('SELECT COUNT(*) FROM tproger_articles WHERE link = ?', (link,))
        if c.fetchone()[0] == 0:
            try:
                c.execute('INSERT INTO tproger_articles (title, link) VALUES (?, ?)', (title, link))
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/articles')
def get_articles():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('SELECT title, link FROM articles ORDER BY id DESC LIMIT 50')
    articles = [{'title': row[0], 'link': row[1]} for row in c.fetchall()]
    conn.close()

    return render_template('articles.html', articles=articles)

@app.route('/tproger_articles')
def get_tproger_articles():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('SELECT title, link FROM tproger_articles ORDER BY id DESC LIMIT 50')
    articles = [{'title': row[0], 'link': row[1]} for row in c.fetchall()]
    conn.close()

    return render_template('tproger_articles.html', articles=articles)

@app.route('/update_articles')
def update_articles_route():
    update_articles()
    return redirect(url_for('get_articles'))

@app.route('/update_tproger_articles')
def update_tproger_articles_route():
    update_tproger_articles()
    return redirect(url_for('get_tproger_articles'))

@app.route('/download_markdown')
def download_markdown():
    conn = sqlite3.connect('articles.db')
    c = conn.cursor()
    c.execute('SELECT title, link FROM articles ORDER BY id DESC LIMIT 50')
    articles = [{'title': row[0], 'link': row[1]} for row in c.fetchall()]
    conn.close()

    markdown_content = "# Habr Articles\n\n"
    for article in articles:
        markdown_content += f"- [{article['title']}]({article['link']})\n"

    file_path = "articles.md"
    with open(file_path, "w") as file:
        file.write(markdown_content)

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
