import requests
import time
import os
import csv
from datetime import datetime
import re
import random

headers = {
    'sec-ch-ua-platform': '"Android"',
    'X-XSRF-TOKEN': '3a3e98',
    'Referer': 'https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D%E5%AF%B9%E4%B8%8D%E8%B5%B7',
    'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'MWeibo-Pwa': '1',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36 Edg/136.0.0.0',
    'Accept': 'application/json, text/plain, */*',
}

def get_weibo_posts(keyword, pages=3, max_retries=2):
    """爬取微博关键词搜索结果"""
    all_posts = []
    
    for page in range(1, pages+1):
        params = {
            'containerid': f'100103type=60&q={keyword}&t=',
            'page_type': 'searchall',
            'page': str(page),
        }
        
        # 重试机制
        success = False
        for retry in range(max_retries + 1):
            try:
                response = requests.get('https://m.weibo.cn/api/container/getIndex', params=params, headers=headers)
                
                # 检查响应状态
                if response.status_code != 200:
                    if retry < max_retries:
                        print(f"第{page}页HTTP状态错误: {response.status_code}，第{retry+1}次重试")
                        time.sleep(2)
                        continue
                    else:
                        print(f"第{page}页HTTP状态错误: {response.status_code}，跳过")
                        break
                    
                # 检查响应内容是否为空
                if not response.text.strip():
                    if retry < max_retries:
                        print(f"第{page}页返回空响应，第{retry+1}次重试")
                        time.sleep(2)
                        continue
                    else:
                        print(f"第{page}页返回空响应，跳过")
                        break
                    
                # 尝试解析JSON
                try:
                    data = response.json()
                except ValueError as json_error:
                    if retry < max_retries:
                        print(f"第{page}页JSON解析失败: {json_error}，第{retry+1}次重试")
                        time.sleep(2)
                        continue
                    else:
                        print(f"第{page}页JSON解析失败: {json_error}")
                        print(f"响应内容前200字符: {response.text[:200]}")
                        break
                
                if data.get('ok') == 1 and 'data' in data:
                    cards = data['data'].get('cards', [])
                    
                    for card in cards:
                        if card.get('card_type') == 9 and 'mblog' in card:
                            mblog = card['mblog']
                            
                            # 提取帖子数据
                            post = {
                                'id': mblog.get('id'),
                                'mid': mblog.get('mid'),
                                'created_at': mblog.get('created_at'),
                                'text': clean_text(mblog.get('text', '')),
                                'attitudes_count': mblog.get('attitudes_count', 0),  # 点赞数
                                'comments_count': mblog.get('comments_count', 0),    # 评论数
                                'reposts_count': mblog.get('reposts_count', 0),      # 转发数
                                'user_id': mblog['user'].get('id'),
                                'user_name': mblog['user'].get('screen_name'),
                                'followers_count': mblog['user'].get('followers_count'),
                                'verified': mblog['user'].get('verified', False),
                                'verified_reason': mblog['user'].get('verified_reason', '')
                            }
                            
                            all_posts.append(post)
                
                print(f"第{page}页爬取完成，获取{len(cards) if 'cards' in locals() else 0}条数据")
                success = True
                break  # 成功获取数据，跳出重试循环
                
            except Exception as e:
                if retry < max_retries:
                    print(f"爬取第{page}页时出错: {e}，第{retry+1}次重试")
                    time.sleep(2)
                else:
                    print(f"爬取第{page}页时出错: {e}，已达到最大重试次数")
        
        # 随机延迟，防止请求过于频繁
        if success:
            delay = random.uniform(1, 3)
            time.sleep(delay)
    
    return all_posts

def save_posts_to_csv(posts, keyword):
    """保存帖子数据到CSV文件"""
    if not os.path.exists('results'):
        os.makedirs('results')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/weibo_{keyword}_{timestamp}.csv"
    
    # 确定CSV文件的字段
    fieldnames = ['id', 'mid', 'created_at', 'text', 'attitudes_count', 
                  'comments_count', 'reposts_count', 'user_id', 'user_name', 
                  'followers_count', 'verified', 'verified_reason']
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(posts)
    
    print(f"CSV数据已保存到 {filename}，共{len(posts)}条帖子")

def clean_text(text):
    """清理微博文本内容，去除HTML标签和特殊字符"""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除URL
    text = re.sub(r'https?://\S+', '', text)
    # 去除表情符号代码
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()

if __name__ == "__main__":
    keyword = input("请输入要搜索的关键词: ")
    pages = int(input("请输入要爬取的页数: "))
    
    print(f"开始爬取关键词 '{keyword}' 的微博数据...")
    posts = get_weibo_posts(keyword, pages)
    
    if posts:
        # 保存为CSV格式
        save_posts_to_csv(posts, keyword)
        print(f"爬取完成，共获取{len(posts)}条微博")
    else:
        print("未获取到数据")