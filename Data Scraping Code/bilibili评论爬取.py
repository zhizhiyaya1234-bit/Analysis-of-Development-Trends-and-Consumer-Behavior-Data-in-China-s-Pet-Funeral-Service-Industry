import requests
import json
import time
import pandas as pd
import re
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import random

class BilibiliCompleteCrawler:
    def __init__(self, use_cookie=False, cookie_str=None):
        self.session = requests.Session()
        
        # 完整的浏览器请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.bilibili.com',
            'Origin': 'https://www.bilibili.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'DNT': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        self.session.headers.update(self.headers)
        
        if use_cookie and cookie_str:
            self.set_cookies(cookie_str)
        
        self.total_comments_fetched = 0
    
    def set_cookies(self, cookie_str):
        """设置Cookie"""
        cookies = {}
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
        
        self.session.cookies.update(cookies)
        print(f"已设置 {len(cookies)} 个Cookie")
    
    def extract_bvid(self, url):
        """提取BV号"""
        patterns = [
            r'BV[0-9A-Za-z]{10}',
            r'video/(BV[0-9A-Za-z]{10})',
            r'bvid=(BV[0-9A-Za-z]{10})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                bvid = match.group(1) if 'video/' in pattern or 'bvid=' in pattern else match.group()
                return bvid
        
        raise ValueError("无法提取BV号，请确保URL格式正确")
    
    def get_video_info(self, bvid):
        """获取视频信息"""
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data['code'] == 0:
                return data['data']
            else:
                print(f"获取视频信息失败: {data.get('message')}")
                return None
        except Exception as e:
            print(f"获取视频信息出错: {e}")
            return None
    
    def try_multiple_apis(self, aid, page, page_size=20):
        """尝试多个API接口获取评论"""
        apis = [
            # 新版API
            f"https://api.bilibili.com/x/v2/reply/main?jsonp=jsonp&next={page}&type=1&oid={aid}&mode=3&plat=1",
            # 旧版API
            f"https://api.bilibili.com/x/v2/reply?pn={page}&type=1&oid={aid}&ps={page_size}&sort=2",
            # 备用API
            f"https://api.bilibili.com/x/v2/reply/main?next={page}&type=1&oid={aid}&mode=2",
            # 另一个备用API
            f"https://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn={page}&type=1&oid={aid}&sort=2"
        ]
        
        for api_url in apis:
            try:
                # 添加随机延迟避免请求过快
                time.sleep(random.uniform(0.3, 0.8))
                
                response = self.session.get(api_url, timeout=15)
                data = response.json()
                
                if data.get('code') == 0:
                    return data
                else:
                    continue
                    
            except Exception as e:
                continue
        
        return None
    
    def get_comments_page(self, aid, page, page_size=20):
        """获取指定页的评论"""
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                data = self.try_multiple_apis(aid, page, page_size)
                
                if not data or data.get('code') != 0:
                    print(f"第{page}页第{retry+1}次重试...")
                    time.sleep(1)
                    continue
                
                # 解析评论
                comments = self.parse_comments(data)
                return comments
                
            except Exception as e:
                print(f"第{page}页第{retry+1}次重试失败: {e}")
                time.sleep(2)
        
        return []
    
    def parse_comments(self, data):
        """解析评论数据"""
        comments = []
        
        try:
            # 尝试多种数据结构
            replies = None
            
            # 新版API结构
            if 'replies' in data.get('data', {}):
                replies = data['data']['replies']
            # 旧版API结构
            elif 'data' in data and 'replies' in data['data']:
                replies = data['data']['replies']
            # 其他结构
            elif 'data' in data and isinstance(data['data'], list):
                replies = data['data']
            
            if not replies or not isinstance(replies, list):
                return []
            
            for reply in replies:
                try:
                    # 安全获取字段
                    member = reply.get('member', {})
                    content = reply.get('content', {})
                    
                    comment = {
                        '用户名': member.get('uname', '未知用户'),
                        '用户ID': member.get('mid', ''),
                        '评论ID': reply.get('rpid', ''),
                        '评论内容': content.get('message', ''),
                        '点赞数': reply.get('like', 0),
                        '回复数': reply.get('rcount', 0),
                        '发布时间': time.strftime("%Y-%m-%d %H:%M:%S", 
                                            time.localtime(reply.get('ctime', time.time()))),
                        '楼层': reply.get('floor', 0),
                    }
                    
                    # 判断是否是UP主
                    official_verify = member.get('official_verify', {})
                    comment['是否UP主'] = 1 if official_verify.get('type') == 0 else 0
                    
                    comments.append(comment)
                    
                except Exception as e:
                    continue
            
            return comments
            
        except Exception as e:
            print(f"解析评论数据出错: {e}")
            return []
    
    def get_total_pages(self, aid, page_size=20):
        """获取总页数"""
        try:
            # 先获取第一页数据来得到总评论数
            data = self.try_multiple_apis(aid, 1, page_size)
            
            if not data or data.get('code') != 0:
                return 0
            
            total_comments = 0
            
            # 尝试不同的数据结构获取总评论数
            if 'page' in data.get('data', {}):
                total_comments = data['data']['page'].get('count', 0)
            elif 'cursor' in data.get('data', {}):
                total_comments = data['data']['cursor'].get('all_count', 0)
            
            # 计算总页数
            if total_comments > 0:
                total_pages = (total_comments + page_size - 1) // page_size
                # 限制最大页数，避免无限爬取
                return min(total_pages, 500)  # 最多500页
            else:
                return 0
                
        except Exception as e:
            print(f"获取总页数失败: {e}")
            return 0
    
    def crawl_all_comments(self, video_url, max_pages=100):
        """爬取所有评论"""
        print("=" * 60)
        print("B站评论爬虫 - 完整版")
        print("=" * 60)
        
        # 提取BV号
        try:
            bvid = self.extract_bvid(video_url)
            print(f"✓ 提取到BV号: {bvid}")
        except ValueError as e:
            print(e)
            return []
        
        # 获取视频信息
        print("正在获取视频信息...")
        video_info = self.get_video_info(bvid)
        
        if not video_info:
            print("✗ 获取视频信息失败")
            return []
        
        aid = video_info['aid']
        title = video_info['title']
        print(f"✓ 视频标题: {title[:50]}..." if len(title) > 50 else f"✓ 视频标题: {title}")
        print(f"✓ 视频AID: {aid}")
        
        # 获取总页数
        print("正在获取评论总数...")
        total_pages = self.get_total_pages(aid)
        
        if total_pages == 0:
            print("该视频暂无评论")
            return []
        
        # 限制最大页数
        actual_pages = min(total_pages, max_pages)
        print(f"✓ 总评论页数: {total_pages}")
        print(f"✓ 实际爬取页数: {actual_pages}")
        
        all_comments = []
        failed_pages = []
        
        print("\n开始爬取评论...")
        print("-" * 60)
        
        # 进度显示
        for page in range(1, actual_pages + 1):
            try:
                print(f"正在爬取第 {page}/{actual_pages} 页...", end="\r")
                
                comments = self.get_comments_page(aid, page)
                
                if comments:
                    all_comments.extend(comments)
                    self.total_comments_fetched = len(all_comments)
                    
                    # 每10页显示一次进度
                    if page % 10 == 0 or page == actual_pages:
                        print(f"✓ 第 {page}/{actual_pages} 页: 获取到 {len(comments)} 条评论，总计 {len(all_comments)} 条")
                else:
                    failed_pages.append(page)
                    print(f"✗ 第{page}页没有评论数据")
                
                # 随机延迟，模拟真实用户
                delay = random.uniform(0.5, 1.2)
                time.sleep(delay)
                
            except Exception as e:
                failed_pages.append(page)
                print(f"✗ 第{page}页爬取出错: {e}")
                continue
        
        print("-" * 60)
        
        if failed_pages:
            print(f"警告: 有 {len(failed_pages)} 页爬取失败: {failed_pages[:10]}...")
        
        print(f"✓ 爬取完成！共获取 {len(all_comments)} 条评论")
        
        return all_comments
    
    def save_to_file(self, comments, filename=None, format='csv'):
        """
        保存评论到文件
        format: 'csv', 'excel', 'json', 'txt'
        """
        if not comments:
            print("没有评论数据可保存")
            return None
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(comments)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if not filename:
                if format == 'csv':
                    filename = f"B站评论_{timestamp}.csv"
                elif format == 'excel':
                    filename = f"B站评论_{timestamp}.xlsx"
                elif format == 'json':
                    filename = f"B站评论_{timestamp}.json"
                else:
                    filename = f"B站评论_{timestamp}.txt"
            
            # 确保目录存在
            file_dir = os.path.dirname(filename)
            if file_dir and not os.path.exists(file_dir):
                os.makedirs(file_dir)
            
            # 根据格式保存
            if format == 'csv':
                # CSV格式（最可靠）
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            elif format == 'excel':
                # Excel格式
                try:
                    df.to_excel(filename, index=False)
                except:
                    # 如果失败，尝试使用openpyxl引擎
                    df.to_excel(filename, index=False, engine='openpyxl')
            elif format == 'json':
                # JSON格式
                df.to_json(filename, orient='records', force_ascii=False, indent=2)
            elif format == 'txt':
                # 文本格式
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"B站评论数据 - 共 {len(comments)} 条\n")
                    f.write("=" * 80 + "\n\n")
                    for i, comment in enumerate(comments, 1):
                        f.write(f"【{i}】{comment.get('用户名', '未知')}\n")
                        f.write(f"评论: {comment.get('评论内容', '')}\n")
                        f.write(f"点赞: {comment.get('点赞数', 0)} | 回复: {comment.get('回复数', 0)} | 时间: {comment.get('发布时间', '')}\n")
                        f.write("-" * 80 + "\n\n")
            
            # 验证文件是否创建
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                file_path = os.path.abspath(filename)
                
                print(f"✓ {format.upper()}文件保存成功！")
                print(f"  文件名: {filename}")
                print(f"  完整路径: {file_path}")
                print(f"  文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
                print(f"  数据条数: {len(comments)}")
                
                return filename
            else:
                print(f"✗ 文件创建失败: {filename}")
                return None
                
        except Exception as e:
            print(f"✗ 保存文件失败: {e}")
            return None
    
    def save_multiple_formats(self, comments):
        """用多种格式保存数据"""
        if not comments:
            print("没有评论数据可保存")
            return []
        
        saved_files = []
        
        # 首先尝试CSV（最可靠）
        print("\n尝试保存数据...")
        csv_file = self.save_to_file(comments, format='csv')
        if csv_file:
            saved_files.append(csv_file)
        
        # 然后尝试Excel
        excel_file = self.save_to_file(comments, format='excel')
        if excel_file:
            saved_files.append(excel_file)
        
        # 最后保存为文本备份
        txt_file = self.save_to_file(comments, format='txt')
        if txt_file:
            saved_files.append(txt_file)
        
        return saved_files

def check_file_permissions():
    """检查文件权限"""
    print("=" * 60)
    print("文件权限检查")
    print("=" * 60)
    
    test_files = []
    
    # 测试在当前目录创建文件
    test_dir = os.getcwd()
    print(f"当前目录: {test_dir}")
    
    # 测试不同格式
    formats = [
        ('test.csv', 'w'),
        ('test.xlsx', 'wb'),
        ('test.txt', 'w'),
    ]
    
    for filename, mode in formats:
        try:
            if 'b' in mode:
                with open(filename, mode) as f:
                    f.write(b'test')
            else:
                with open(filename, mode, encoding='utf-8') as f:
                    f.write('test')
            
            file_size = os.path.getsize(filename)
            print(f"✓ 可以创建 {filename} (大小: {file_size} 字节)")
            test_files.append(filename)
            
        except Exception as e:
            print(f"✗ 无法创建 {filename}: {e}")
    
    # 清理测试文件
    for file in test_files:
        try:
            os.remove(file)
        except:
            pass
    
    print("-" * 60)
    return len(test_files) > 0

def get_cookie_interactive():
    """交互式获取Cookie"""
    print("\n" + "=" * 60)
    print("Cookie获取说明:")
    print("1. 打开Chrome浏览器，访问B站 (https://www.bilibili.com)")
    print("2. 按F12打开开发者工具")
    print("3. 切换到 Network (网络) 标签")
    print("4. 刷新页面")
    print("5. 点击任意一个请求")
    print("6. 在 Headers (请求头) 中找到 Cookie")
    print("7. 复制整个Cookie字符串")
    print("=" * 60)
    
    use_cookie = input("\n是否使用Cookie？(y/n, 默认n): ").strip().lower()
    
    if use_cookie == 'y':
        cookie = input("请粘贴Cookie字符串: ").strip()
        return cookie if cookie else None
    else:
        return None

def main():
    print("=" * 60)
    print("B站评论爬虫 - 解决半截数据和保存问题")
    print("=" * 60)
    
    # 检查文件权限
    if not check_file_permissions():
        print("警告: 文件权限可能有问题，建议以管理员身份运行程序")
        choice = input("是否继续？(y/n): ").strip().lower()
        if choice != 'y':
            return
    
    # 获取Cookie
    cookie = get_cookie_interactive()
    
    # 输入视频URL
    video_url = input("\n请输入B站视频URL: ").strip()
    
    if not video_url:
        print("URL不能为空")
        return
    
    # 输入最大爬取页数
    try:
        max_pages = int(input("请输入最大爬取页数 (默认100, 每页20条): ") or "100")
    except:
        max_pages = 100
    
    # 创建爬虫实例
    use_cookie = cookie is not None
    crawler = BilibiliCompleteCrawler(use_cookie=use_cookie, cookie_str=cookie)
    
    # 开始爬取
    print("\n" + "=" * 60)
    print("开始爬取评论...")
    start_time = time.time()
    
    comments = crawler.crawl_all_comments(video_url, max_pages)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"爬取耗时: {elapsed:.2f} 秒")
    
    if comments:
        # 显示统计信息
        print("\n" + "=" * 60)
        print("爬取结果统计:")
        print(f"总评论数: {len(comments)}")
        
        if comments:
            avg_likes = sum(c.get('点赞数', 0) for c in comments) / len(comments)
            print(f"平均点赞数: {avg_likes:.1f}")
            
            max_likes = max(c.get('点赞数', 0) for c in comments)
            print(f"最高点赞数: {max_likes}")
            
            up_comments = sum(1 for c in comments if c.get('是否UP主') == 1)
            if up_comments > 0:
                print(f"UP主评论数: {up_comments}")
            
            # 显示前几条评论
            print("\n前5条评论预览:")
            print("-" * 60)
            for i, comment in enumerate(comments[:5]):
                content = comment['评论内容']
                if len(content) > 50:
                    content = content[:50] + "..."
                print(f"{i+1}. [{comment['用户名']}]")
                print(f"   {content}")
                print(f"   点赞: {comment['点赞数']}, 时间: {comment['发布时间']}")
                print()
        
        # 保存数据
        print("\n" + "=" * 60)
        print("正在保存数据...")
        
        saved_files = crawler.save_multiple_formats(comments)
        
        if saved_files:
            print(f"\n✓ 成功保存 {len(saved_files)} 个文件:")
            for file in saved_files:
                full_path = os.path.abspath(file)
                size = os.path.getsize(file)
                print(f"  - {file}")
                print(f"    路径: {full_path}")
                print(f"    大小: {size} 字节 ({size/1024:.2f} KB)")
        else:
            print("✗ 所有保存方式都失败了！")
            
            # 尝试最后的保存方法
            try:
                # 强制保存到桌面
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop):
                    csv_path = os.path.join(desktop, f"B站评论_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                    df = pd.DataFrame(comments)
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    
                    if os.path.exists(csv_path):
                        print(f"✓ 已强制保存到桌面: {csv_path}")
            except Exception as e:
                print(f"✗ 强制保存也失败: {e}")
    else:
        print("未获取到评论数据")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断程序")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按Enter键退出...")