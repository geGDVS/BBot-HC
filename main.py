from HackChat import HackChat
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

NICK = "BBot"

def extract_urls(text):
    """
    从文本中提取所有网址
    
    参数:
        text: 包含可能网址的文本字符串
        
    返回:
        提取到的网址列表，如果没有找到则返回空列表
    """
    # 正则表达式模式，用于匹配各种形式的URL
    url_pattern = re.compile(
        r'(?:https?://|www\.)'  # 匹配http://, https://或www.
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'  # 匹配域名
        r'(?:[a-zA-Z]{2,6}\.?|[a-zA-Z0-9-]{2,}\.?)'  # 匹配顶级域名
        r'(?:/?|[/?]\S+)'  # 匹配路径和参数
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
    """
    获取指定URL的网页详细信息
    
    参数:
        url (str): 要爬取的网页URL
        
    返回:
        dict: 包含多种网页信息的字典
    """
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
        if sender == NICK or sender.startswith("awa_ya") or sender.startswith("BoB"):
            return
        # 判断msg是否为网址
        urls = extract_urls(msg)
        if urls:
            print("{}发送了网址: {}".format(sender, urls))
            ret = ""
            for url in urls:
                # 爬虫获取网页信息
                page_info = get_page_info(url)
                if 'error' in page_info:
                    self.sendMsg(page_info.get('error'))
                    return
                if ret != "": ret += "\n---\n"
                ret += f"""![](https://camo.hach.chat/?proxyUrl={page_info.get('favicon')})[{page_info.get('title')}]({page_info.get('url')})
{page_info.get('description')}
关键词：{page_info.get('keywords')}
语言：{page_info.get('language')}
标题：{page_info.get('h1_headings')}
图片数量：{page_info.get('images_count')}
包含{page_info.get('links_count')}个链接：{'，'.join(page_info.get('sample_links'))} 等
"""
            self.sendMsg(ret)
            return

if __name__ == "__main__":
    chat = YourChat("lounge", f"{NICK}#password")
    chat.run()
