"""
B站视频评论抓取工具
功能：根据B站视频URL抓取评论，并保存为Excel文件
支持：分页抓取、评论去重、表情符号处理、Excel导出
"""

import requests
import pandas as pd
import time
import random
from urllib.parse import urlparse, parse_qs
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class BilibiliCommentCrawler:
    def __init__(self):
        """初始化B站评论爬虫"""
        # 请求头设置，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.bilibili.com/',
            'Connection': 'keep-alive',
            'Cookie': 'buvid3=F7E50195-2708-F4F8-5D79-6290865A25EB08277infoc; b_nut=1739341126; _uuid=ED1077AFA-B241-1062D-669F-F4107EE19F13473584infoc; header_theme_version=CLOSE; enable_web_push=DISABLE; home_feed_column=5; buvid_fp=66699aac769b109c1992f3b48eb4bbd4; rpdid=|(~|)RYRm|Y0J'u~JmRl|Y)R; DedeUserID=278433342; DedeUserID__ckMd5=e42de04fc355d35f; enable_feed_channel=ENABLE; LIVE_BUVID=AUTO4317416905588586; theme-tip-show=SHOWED; buvid4=49E1D02C-98FF-12F4-F7C6-9E710B7A148D08277-025021206-9JESgZ7vuHYuslN+EUXKqw%3D%3D; theme-avatar-tip-show=SHOWED; theme-switch-show=SHOWED; CURRENT_QUALITY=80; PVID=3; browser_resolution=1603-884; bmg_af_switch=1; bmg_src_def_domain=i2.hdslb.com; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjMxODI2NDAsImlhdCI6MTc2MjkyMzM4MCwicGx0IjotMX0.ryoNnrR5gj1MwS-YAoXiO7-sRwf5WxJyQK9xFLg6wkg; bili_ticket_expires=1763182580; SESSDATA=c79384c8%2C1778475441%2Cb10ce%2Ab1CjCJ2jMp-dceOpnrU1RS2czKj2IM7vuSwn9DvMJycTVcKIygaGM2D2jur2fv-PgdmwsSVmJ2eUhkc1VjN3E1UDlDRi1SUmJmejhuVEVkUDdmeDg5TXUtQXZHeTFYeFVxLUw2VHV5WjRWY0RUbjU3SEJ0MDZ0NVg1M2VIa0F4WWdqdlFNZjIwWk13IIEC; bili_jct=d2e6e1b4b11148d29bbc39c2cc68bd1a; sid=5hs59ulx; bp_t_offset_278433342=1134238121991340032; share_source_origin=WEIXIN; bsource=share_source_weixinchat; CURRENT_FNVAL=4048; b_lsid=71017BC4A_19A7838D34C'  # 请替换为自己的Cookie
        }
        
        # 评论API接口
        self.comment_api = 'https://api.bilibili.com/x/v2/reply/wbi/main'
        
        # 延迟设置，避免被封禁
        self.min_delay = 1.5  # 最小延迟时间（秒）
        self.max_delay = 3.0  # 最大延迟时间（秒）
        
        # 存储评论数据
        self.comments_data = []
        
    def get_video_cid(self, video_url):
        """
        从视频URL获取视频的cid（评论区ID）
        :param video_url: B站视频URL（如https://www.bilibili.com/video/BV1xx4y1V7eD）
        :return: cid或None
        """
        try:
            # 解析URL获取aid或bvid
            parsed_url = urlparse(video_url)
            query_params = parse_qs(parsed_url.query)
            
            # 提取bvid（从URL路径中）
            path_parts = parsed_url.path.split('/')
            bvid = None
            for part in path_parts:
                if part.startswith('BV'):
                    bvid = part
                    break
            
            if not bvid:
                print("❌ 无法从URL中提取BV号")
                return None
            
            # 获取视频信息，包含cid
            video_info_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
            response = requests.get(video_info_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                print(f"❌ 获取视频信息失败：{data.get('message', '未知错误')}")
                return None
            
            cid = data.get('data', {}).get('cid')
            if not cid:
                print("❌ 无法获取视频的cid")
                return None
            
            print(f"✅ 成功获取视频信息：BV号={bvid}, cid={cid}")
            return cid
            
        except Exception as e:
            print(f"❌ 获取cid时出错：{str(e)}")
            return None
    
    def crawl_comments(self, cid, max_pages=100):
        """
        抓取指定cid的评论
        :param cid: 视频的cid
        :param max_pages: 最大抓取页数（每页约20条评论）
        :return: 评论数据列表
        """
        if not cid:
            print("❌ cid不能为空")
            return []
        
        print(f"\n📥 开始抓取评论，cid={cid}，最大抓取页数={max_pages}")
        self.comments_data = []
        page = 1
        total_comments = 0
        
        while page <= max_pages:
            try:
                # 构造请求参数
                params = {
                    'cid': cid,
                    'page': page,
                    'size': 20,  # 每页20条评论
                    'order': 'hot',  # 按热度排序（hot-热度，time-时间）
                    'plat': 1,
                    'type': 1,
                    'oid': cid,
                    'mode': 3
                }
                
                # 发送请求
                response = requests.get(
                    self.comment_api,
                    headers=self.headers,
                    params=params,
                    timeout=15,
                    verify=False
                )
                response.raise_for_status()
                data = response.json()
                
                # 检查响应状态
                if data.get('code') != 0:
                    print(f"❌ 第{page}页评论请求失败：{data.get('message', '未知错误')}")
                    break
                
                # 解析评论数据
                reply_data = data.get('data', {}).get('replies', [])
                if not reply_data:
                    print(f"✅ 已获取所有评论（第{page}页无数据）")
                    break
                
                # 提取评论内容
                for comment in reply_data:
                    comment_content = comment.get('content', {}).get('message', '').strip()
                    if comment_content:  # 只保留非空评论
                        self.comments_data.append({
                            'content': comment_content,
                            'user_name': comment.get('member', {}).get('uname', '未知用户'),
                            'user_id': comment.get('member', {}).get('mid', 0),
                            'like_count': comment.get('like', 0),
                            'reply_count': comment.get('rcount', 0),
                            'publish_time': datetime.fromtimestamp(comment.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                            'comment_id': comment.get('rpid', 0)
                        })
                
                # 统计进度
                page_comments = len(reply_data)
                total_comments += page_comments
                print(f"📄 第{page}页抓取完成，获取评论{page_comments}条，累计{total_comments}条")
                
                # 随机延迟，避免被封禁
                delay = random.uniform(self.min_delay, self.max_delay)
                time.sleep(delay)
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"❌ 第{page}页请求出错：{str(e)}")
                # 增加延迟后重试
                time.sleep(5)
                continue
            except Exception as e:
                print(f"❌ 第{page}页解析出错：{str(e)}")
                page += 1
                time.sleep(2)
                continue
        
        print(f"\n📊 评论抓取完成！共获取{len(self.comments_data)}条有效评论")
        return self.comments_data
    
    def remove_duplicate_comments(self):
        """去除重复评论"""
        if not self.comments_data:
            print("❌ 没有评论数据可去重")
            return
        
        # 转换为DataFrame进行去重
        df = pd.DataFrame(self.comments_data)
        original_count = len(df)
        
        # 基于评论内容去重
        df_cleaned = df.drop_duplicates(subset=['content'], keep='first')
        cleaned_count = len(df_cleaned)
        duplicate_count = original_count - cleaned_count
        
        print(f"\n🧹 评论去重完成")
        print(f"   原始评论数：{original_count}")
        print(f"   去重后评论数：{cleaned_count}")
        print(f"   去除重复评论数：{duplicate_count}")
        
        # 更新评论数据
        self.comments_data = df_cleaned.to_dict('records')
        return self.comments_data
    
    def save_to_excel(self, file_name=None, only_content=True):
        """
        保存评论数据到Excel文件
        :param file_name: 文件名（默认自动生成）
        :param only_content: 是否只保存评论内容（与用户提供的数据格式一致）
        """
        if not self.comments_data:
            print("❌ 没有评论数据可保存")
            return
        
        # 转换为DataFrame
        df = pd.DataFrame(self.comments_data)
        
        # 如果只保存评论内容
        if only_content:
            df_save = df[['content']].copy()
            print(f"📁 只保存评论内容字段")
        else:
            df_save = df.copy()
            print(f"📁 保存完整评论数据（{len(df_save.columns)}个字段）")
        
        # 生成文件名
        if not file_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f'【B站】b站评论汇总_{timestamp}.xlsx'
        
        # 保存到Excel
        try:
            df_save.to_excel(file_name, index=False, engine='openpyxl')
            print(f"✅ 评论数据已保存到：{file_name}")
            print(f"   共保存{len(df_save)}条评论")
            return file_name
        except Exception as e:
            print(f"❌ 保存Excel文件失败：{str(e)}")
            return None
    
    def run(self, video_url, max_pages=100, only_content=True, output_file=None):
        """
        完整运行流程
        :param video_url: B站视频URL
        :param max_pages: 最大抓取页数
        :param only_content: 是否只保存评论内容
        :param output_file: 输出文件名
        :return: 保存的文件名
        """
        print("=" * 60)
        print("🎯 B站评论抓取工具 v1.0")
        print("=" * 60)
        
        # 1. 获取cid
        cid = self.get_video_cid(video_url)
        if not cid:
            return None
        
        # 2. 抓取评论
        self.crawl_comments(cid, max_pages)
        
        # 3. 去重处理
        self.remove_duplicate_comments()
        
        # 4. 保存到Excel
        if self.comments_data:
            saved_file = self.save_to_excel(output_file, only_content)
            return saved_file
        else:
            print("❌ 没有有效评论可保存")
            return None


def main():
    """示例运行"""
    # 1. 配置参数
    VIDEO_URL = "https://www.bilibili.com/video/BV1xx4y1V7eD"  # 替换为目标视频URL
    MAX_PAGES = 50  # 最大抓取页数（根据需要调整）
    ONLY_CONTENT = True  # 只保存评论内容（与用户数据格式一致）
    OUTPUT_FILE = "【B站】b站评论汇总.xlsx"  # 输出文件名
    
    # 2. 创建爬虫实例
    crawler = BilibiliCommentCrawler()
    
    # 3. 注意：需要替换Cookie！
    print("\n⚠️  重要提示：")
    print("   1. 请在浏览器中登录B站后获取Cookie")
    print("   2. 将Cookie替换到BilibiliCommentCrawler类的headers中")
    print("   3. Cookie包含buvid3、bili_jct、sid等关键信息")
    print()
    
    # 4. 运行爬虫
    input("   按回车键开始抓取（确保已配置Cookie）...")
    saved_file = crawler.run(
        video_url=VIDEO_URL,
        max_pages=MAX_PAGES,
        only_content=ONLY_CONTENT,
        output_file=OUTPUT_FILE
    )
    
    if saved_file:
        print(f"\n🎉 任务完成！评论文件：{saved_file}")
    else:
        print(f"\n❌ 任务失败")


if __name__ == "__main__":
    main()
