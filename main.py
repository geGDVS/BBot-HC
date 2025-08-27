from HackChat import HackChat
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sqlite3
from sqlite3 import Error
from datetime import datetime

NICK = "BBot"
PREFIX = ":!"

def is_over_1h(dt1: datetime, dt2: datetime) -> bool:
    # 计算时间差的绝对值（总秒数）
    time_diff_seconds = abs((dt1 - dt2).total_seconds())
    # 1小时 = 3600秒，判断是否≥3600秒
    return time_diff_seconds >= 3600

class YourSQL:
    def create_connection(db_file):
        """创建数据库连接"""
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            return conn
        except Error as e:
            print(e)
        return conn
    def create_user_table(conn):
        """创建用户表"""
        try:
            sql = """CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        trip TEXT NOT NULL UNIQUE CHECK(LENGTH(trip) = 6),
                        coins REAL NOT NULL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message TEXT NOT NULL DEFAULT '',
                        last_sign_time TIMESTAMP DEFAULT '1970-01-01 00:00:00.000000',
                    );"""
            c = conn.cursor()
            c.execute(sql)
        except Error as e:
            print(e)
    def add_user(conn, name, trip, coins=0.0):
        """添加新用户"""
        # 验证识别码是否为6位
        if len(trip) != 6:
            return f"用户注册失败，==你必须拥有一个识别码==。"
        try:
            sql = ''' INSERT INTO users(name, trip, coins)
                    VALUES(?, ?, ?) '''
            cur = conn.cursor()
            cur.execute(sql, (name, trip, coins))
            conn.commit()
            ret = f"用户注册成功，ID: {cur.lastrowid}" 
        except Error as e:
            ret = f"用户注册失败: {e}"
        return ret
    def update_user_nick(conn, trip, new_nick):
        """更新用户昵称"""
        try:
            sql = ''' UPDATE users
                    SET name = ?
                    WHERE trip = ?'''
            cur = conn.cursor()
            cur.execute(sql, (new_nick, trip))
            conn.commit()
            ret = f"更新昵称成功，新昵称为`{new_nick}`。" if cur.rowcount > 0 else f"更新昵称失败。"
        except Error as e:
            ret = f"更新昵称失败: {e}"
        return ret
    def get_user_by_trip(conn, trip):
        """根据识别码查询用户"""
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE trip=?", (trip,))
        return cur.fetchone()
    def get_user_by_name(conn, name):
        """根据昵称查询用户"""
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE name=?", (name,))
        return cur.fetchone()
    def update_user_coins(conn, trip, new_coins):
        """更新用户金币"""
        try:
            sql = ''' UPDATE users
                    SET coins = ?, last_sign_time = ?
                    WHERE trip = ?'''
            cur = conn.cursor()
            cur.execute(sql, (new_coins, datetime.now(), trip))
            conn.commit()
            return cur.rowcount > 0
        except Error as e:
            print(f"更新金币失败: {e}")
            return False 
    def update_user_status(conn, trip, msg):
        try:
            sql = ''' UPDATE users
                    SET last_message = ?, last_message_time = ?
                    WHERE trip = ?'''
            cur = conn.cursor()
            cur.execute(sql, (msg, datetime.now(), trip))
            conn.commit()
            return cur.rowcount > 0
        except Error as e:
            print(f"更新状态失败: {e}")
            return False

# 忽略列表
ignore_list = [
    r'awa_ya.*',          # 以awa_ya开头的字符串
    r'BoB.*',             # 以BoB开头的字符串
    rf'{NICK}'
]

class YourWeb:
    def matches_any_regex(s, regex_patterns):
        for pattern in regex_patterns:
            # 使用re.fullmatch检查整个字符串是否完全匹配模式
            if re.fullmatch(pattern, s):
                return True
        return False
    def extract_urls(text):
        # 正则表达式模式，用于匹配各种形式的URL
        url_pattern = re.compile(
            r'(?:https?://|ftp://|www\.)'  # 协议部分或www.开头
            r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'  # 域名
            r'(?:[a-zA-Z]{2,6}\.?|[a-zA-Z0-9-]{2,}\.?)'  # 顶级域名
            r'(?:/[^\s]*)?'  # 路径部分，匹配斜杠后的所有非空白字符
        )
        
        # 查找所有匹配的URL
        urls = re.findall(url_pattern, text)
        
        # 处理可能缺少协议的URL（如www.开头的）
        processed_urls = []
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                processed_urls.append(f'http://{url}')
            else:
                processed_urls.append(url)
        
        return processed_urls
    def get_page_info(url):
        try:
            # 设置请求头，模拟浏览器访问
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 发送GET请求
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
            
            # 解析HTML内容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取基础信息
            result = {
                'url': response.url,
                'status_code': response.status_code,
                'encoding': response.encoding,
                'title': soup.title.string.strip() if soup.title and soup.title.string else "无标题"
            }
            
            # 提取meta标签信息
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                # 描述
                if tag.get('name') == 'description' and tag.get('content'):
                    result['description'] = tag.get('content').strip()
                # 关键词
                if tag.get('name') == 'keywords' and tag.get('content'):
                    result['keywords'] = tag.get('content').strip()
                # 页面语言
                if tag.get('http-equiv') == 'Content-Language' and tag.get('content'):
                    result['language'] = tag.get('content').strip()
            
            # 如果没有找到则设置默认值
            result.setdefault('description', '无描述')
            result.setdefault('keywords', '无关键词')
            result.setdefault('language', '未指定')
            
            # 提取网站图标
            favicon = soup.find('link', rel=['icon', 'shortcut icon'])
            if favicon and favicon.get('href'):
                # 处理相对路径
                result['favicon'] = urljoin(url, favicon.get('href'))
            else:
                result['favicon'] = '无图标'
            
            # 提取所有链接
            links = soup.find_all('a', href=True)
            unique_links = []
            for link in links:
                full_url = urljoin(url, link['href'])
                # 只保留有效的http/https链接
                if urlparse(full_url).scheme in ['http', 'https'] and full_url not in unique_links:
                    unique_links.append(full_url)
            result['links_count'] = len(unique_links)
            result['sample_links'] = unique_links[:5]  # 只保留前5个链接作为样本
            
            # 提取图像数量
            images = soup.find_all('img')
            result['images_count'] = len(images)
            
            # 提取h1标题
            h1_tags = soup.find_all('h1')
            result['h1_headings'] = [h1.get_text(strip=True) for h1 in h1_tags] if h1_tags else ['无H1标题']
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {
                'url': url,
                'error': f"==请求错误:== `{str(e)}`"
            }
        except Exception as e:
            return {
                'url': url,
                'error': f"==解析错误:== `{str(e)}`"
            }

class YourChat(HackChat):
    def onMessage(self, sender, msg, trip):
        if YourWeb.matches_any_regex(sender, ignore_list):
            return
        # 判断msg是否为网址
        urls = YourWeb.extract_urls(msg)
        if urls:
            print("{}发送了网址: {}".format(sender, urls))
            ret = ""
            for url in urls:
                # 爬虫获取网页信息
                page_info = YourWeb.get_page_info(url)
                if 'error' in page_info:
                    self.sendMsg(page_info.get('error'))
                    return
                if ret != "": ret += "\n---\n"
                ret += f"![](https://camo.hach.chat/?proxyUrl={page_info.get('favicon')})[{page_info.get('title')}]({page_info.get('url')})\n"
                ret += f"{page_info.get('description')}\n"
                ret += f"关键词：{page_info.get('keywords')}\n"
                ret += f"语言：{page_info.get('language')}\n"
                ret += f"标题：{page_info.get('h1_headings')}\n"
                ret += f"图片数量：{page_info.get('images_count')}\n"
                ret += f"包含{page_info.get('links_count')}个链接：{'，'.join(page_info.get('sample_links'))} 等\n"
            self.sendMsg(ret)
        user = YourSQL.get_user_by_trip(conn, trip)
        if msg.startswith(f"{PREFIX}register "):
            _, name = msg.split(" ", 1)
            ret = YourSQL.add_user(conn, name, trip)
            self.sendMsg(f"@{sender} {ret}")
        if msg.startswith(f"{PREFIX}nick "):
            if user:
                _, new_nick = msg.split(" ", 1)
                ret = YourSQL.update_user_nick(conn, trip, new_nick)
                self.sendMsg(f"@{sender} {ret}")
            else:
                self.sendMsg(f"@{sender} 您还未注册，请使用`{PREFIX}register <昵称>`进行注册。")
        if msg.startswith(f"{PREFIX}seen "):
            _, him = msg.split(" ", 1)
            him_user = YourSQL.get_user_by_trip(conn, him)
            if not him_user:
                him_user = YourSQL.get_user_by_name(conn, him)
            if him_user:
                ret = f"上次`{him_user[1]}`出现是在=={him_user[5]}==, 说了`{him_user[6]}`。"
                self.sendMsg(f"{ret}")
            else:
                self.sendMsg(f"该用户未注册！")
        if msg == (f"{PREFIX}me"):
            if user:
                ret = f"查询结果: \n"
                ret += f"ID: {user[0]}\n"
                ret += f"昵称: {user[1]}\n"
                ret += f"识别码: {user[2]}\n"
                ret += f"Bcoin余额: {user[3]}\n"
                ret += f"注册时间: {user[4]}\n"
                ret += f"上次签到时间：{user[7]}\n"
                self.sendMsg(f"/w {sender} {ret}")
            else:
                self.sendMsg(f"@{sender} 您还未注册，请使用`{PREFIX}register <昵称>`进行注册。")
        if msg == f"{PREFIX}sign":
            if user:
                if is_over_1h(datetime.strptime(user[7], "%Y-%m-%d %H:%M:%S.%f"), datetime.now()):
                    new_coins = user[3] + 1
                    success = YourSQL.update_user_coins(conn, trip, new_coins)
                    if success:
                        self.sendMsg(f"@{sender} 您签到获得 1 BCoin，当前余额: {new_coins}")
                    else:
                        self.sendMsg(f"@{sender} 签到失败")
                else:
                    self.sendMsg(f"@{sender} 您上次签到时间({user[6]})距离现在不足1小时，请稍后再来。")
            else:
                self.sendMsg(f"@{sender} 您还未注册")
        if msg == f"{PREFIX}help":
            ret = f"可用指令：\n"
            ret += f"`{PREFIX}register <昵称>` - 注册\n"
            ret += f"`{PREFIX}nick <新昵称>` - 修改昵称\n"
            ret += f"`{PREFIX}seen <用户>` - 查询用户最后发言\n"
            ret += f"`{PREFIX}me` - 查询自己信息\n"
            ret += f"`{PREFIX}sign` - 签到\n"
            self.sendMsg(f"/w {sender} {ret}")
        if user:
            YourSQL.update_user_status(conn, trip, msg)
        conn.commit()

if __name__ == "__main__":
    database = "users.db"
    conn = YourSQL.create_connection(database)
    if conn is not None:
        YourSQL.create_user_table(conn)
    else:
        print("无法创建数据库连接")
    chat = YourChat("bot", f"{NICK}#password")
    chat.run()
    conn.close()
