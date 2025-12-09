import requests
import pandas as pd
import time
import random
from datetime import datetime
import json

class BilibiliCommentCrawler:
   
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.bilibili.com'
        })
        
    def get_video_info(self, aid: int = 371839463) -> dict:
        """获取视频信息"""
        try:
            url = "https://api.bilibili.com/x/web-interface/view"
            params = {'aid': aid}
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                video_info = data['data']
                print(f"视频标题: {video_info.get('title')}")
                print(f"UP主: {video_info.get('owner', {}).get('name')}")
                print(f"播放量: {video_info.get('stat', {}).get('view')}")
                print(f"弹幕数: {video_info.get('stat', {}).get('danmaku')}")
                return video_info
            else:
                print(f"获取视频信息失败: {data.get('message')}")
                return {}
                
        except Exception as e:
            print(f"获取视频信息出错: {e}")
            return {}
    
    def get_comments_page(self, oid: int = 371839463, page: int = 1) -> dict:
        """获取单页评论数据"""
        try:
            url = "https://api.bilibili.com/x/v2/reply"
            params = {
                'pn': page,          # 页码
                'type': 1,           # 1表示视频
                'oid': oid,          # 视频aid
                'sort': 2,           # 2按热度排序，1按时间排序
                'ps': 20,            # 每页条数
                'nohot': 0           # 是否隐藏热评，0为不隐藏
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                return data
            else:
                print(f"第{page}页评论获取失败: {data.get('message')}")
                return {}
                
        except Exception as e:
            print(f"获取第{page}页评论出错: {e}")
            return {}
    
    def get_sub_comments(self, root_id: int, oid: int = 371839463, page: int = 1) -> dict:
        """获取子评论（楼中楼）"""
        try:
            url = "https://api.bilibili.com/x/v2/reply/detail"
            params = {
                'pn': page,
                'type': 1,
                'oid': oid,
                'root': root_id,  # 父评论ID
                'ps': 10          # 子评论每页条数
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                return data
            else:
                print(f"获取子评论失败: {data.get('message')}")
                return {}
                
        except Exception as e:
            print(f"获取子评论出错: {e}")
            return {}
    
    def parse_comment(self, comment_data: dict, video_id: int = 371839463) -> dict:
        
        try:
            # 基本信息
            rpid = comment_data.get('rpid', 0)
            parent = comment_data.get('parent', 0)
            
            # 时间处理
            ctime = comment_data.get('ctime', 0)
            mtime = comment_data.get('mtime', ctime)
            
            # 用户信息
            member = comment_data.get('member', {})
            
            # 评论内容
            content = comment_data.get('content', {})
            message = content.get('message', '')
            
            # 表情处理（如果有）
            if 'emote' in content and content['emote']:
                # 将表情代码替换为描述
                for key, emote in content['emote'].items():
                    if key in message:
                        message = message.replace(key, f"[{emote.get('text', '表情')}]")
            
            comment = {
                'comment_id': str(rpid),
                'parent_comment_id': str(parent),
                'create_time': ctime,
                'video_id': str(video_id),
                'content': message,
                'user_id': str(member.get('mid', '')),
                'nickname': member.get('uname', ''),
                'avatar': member.get('avatar', ''),
                'sub_comment_count': comment_data.get('rcount', 0),
                'last_modify_ts': mtime,
                'like_count': comment_data.get('like', 0),
                'user_level': member.get('level_info', {}).get('current_level', 0),
                'vip_status': 1 if member.get('vip', {}).get('status') == 1 else 0,
                'official_verify': member.get('official_verify', {}).get('desc', '')
            }
            
            return comment
            
        except Exception as e:
            print(f"解析评论数据出错: {e}")
            return {}
    
    def crawl_comments(self, 
                      max_pages: int = 100, 
                      max_sub_pages: int = 3,
                      delay_base: float = 1.0) -> list:
        """
        爬取评论主函数
        
        参数:
            max_pages: 最大爬取页数（每页约20条主评论）
            max_sub_pages: 每个评论最大子评论页数
            delay_base: 基础请求延迟（秒）
        """
        all_comments = []
        oid = 371839463  # 视频aid
        
        print("=" * 60)
        print(f"开始爬取B站视频 371839463 的评论")
        print("=" * 60)
        
        # 先获取视频信息
        video_info = self.get_video_info(oid)
        if video_info:
            print(f"视频信息获取成功，开始爬取评论...\n")
        
        current_page = 1
        
        while current_page <= max_pages:
            print(f"📄 正在爬取第 {current_page} 页主评论...")
            
            # 获取当前页评论
            page_data = self.get_comments_page(oid, current_page)
            
            if not page_data:
                print(f"第 {current_page} 页无数据，停止爬取")
                break
            
            replies = page_data.get('data', {}).get('replies', [])
            
            if not replies:
                print(f"第 {current_page} 页没有评论，停止爬取")
                break
            
            print(f"  获取到 {len(replies)} 条主评论")
            
            # 处理当前页的所有评论
            for reply in replies:
                # 解析主评论
                main_comment = self.parse_comment(reply)
                if main_comment:
                    all_comments.append(main_comment)
                    # print(f"    ✓ 主评论: {main_comment['nickname']}: {main_comment['content'][:30]}...")
                
                # 检查是否有子评论
                rcount = reply.get('rcount', 0)
                if rcount > 0:
                    print(f"    评论 {reply.get('rpid')} 有 {rcount} 条回复，开始爬取子评论...")
                    
                    # 爬取子评论
                    sub_comments_list = self.crawl_sub_comments(
                        root_id=reply['rpid'],
                        total_count=rcount,
                        max_sub_pages=max_sub_pages
                    )
                    
                    # 添加子评论到总列表
                    for sub_comment in sub_comments_list:
                        all_comments.append(sub_comment)
            
            # 检查是否还有下一页
            cursor = page_data.get('data', {}).get('cursor', {})
            if cursor.get('is_end', True):
                print("\n✅ 已到达最后一页，爬取完成！")
                break
            
            current_page += 1
            
            # 随机延迟，避免被封
            delay = delay_base + random.uniform(0.5, 1.5)
            print(f"⏳ 等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)
        
        print(f"\n🎉 爬取完成！共获取 {len(all_comments)} 条评论")
        return all_comments
    
    def crawl_sub_comments(self, root_id: int, total_count: int, max_sub_pages: int = 3) -> list:
        """爬取特定评论的所有子评论"""
        sub_comments = []
        oid = 371839463
        page = 1
        
        while page <= max_sub_pages:
            sub_data = self.get_sub_comments(root_id, oid, page)
            
            if not sub_data:
                break
            
            replies = sub_data.get('data', {}).get('replies', [])
            
            if not replies:
                break
            
            for reply in replies:
                sub_comment = self.parse_comment(reply)
                if sub_comment:
                    sub_comments.append(sub_comment)
            
            # 如果获取的回复数少于10条，通常表示没有更多了
            if len(replies) < 10:
                break
            
            page += 1
            time.sleep(0.5 + random.uniform(0, 0.3))
        
        print(f"      已获取 {len(sub_comments)} 条子评论")
        return sub_comments
    
    def save_to_excel(self, comments: list, filename: str = None):
        """保存评论数据到Excel"""
        if not comments:
            print("⚠️ 没有数据可保存")
            return
        
        if filename is None:
            filename = f"B站评论数据_video_371839463_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # 转换为DataFrame
        df = pd.DataFrame(comments)
        
        # 添加可读时间列
        df['create_time_str'] = df['create_time'].apply(
            lambda x: datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S') if x else ''
        )
        
        df['last_modify_str'] = df['last_modify_ts'].apply(
            lambda x: datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S') if x else ''
        )
        
        # 排序：先按主评论时间，再按评论ID（确保父子关系）
        df['comment_id_num'] = df['comment_id'].astype(int)
        df['parent_id_num'] = df['parent_comment_id'].astype(int)
        df = df.sort_values(['create_time', 'comment_id_num']).reset_index(drop=True)
        
        # 删除临时列
        df = df.drop(['comment_id_num', 'parent_id_num'], axis=1)
        
        # 保存到Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='video_371839463', index=False)
            
            # 添加一个统计信息sheet
            stats_df = self.create_statistics(df)
            stats_df.to_excel(writer, sheet_name='统计数据', index=False)
        
        print(f"💾 数据已保存到: {filename}")
        
        # 同时保存为CSV（便于查看）
        csv_filename = filename.replace('.xlsx', '.csv')
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"📄 CSV备份已保存到: {csv_filename}")
        
        return filename
    
    def create_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建统计数据"""
        stats = []
        
        # 基础统计
        total_comments = len(df)
        main_comments = len(df[df['parent_comment_id'] == '0'])
        sub_comments = total_comments - main_comments
        
        stats.append({'指标': '总评论数', '数值': total_comments})
        stats.append({'指标': '主评论数', '数值': main_comments})
        stats.append({'指标': '子评论数', '数值': sub_comments})
        stats.append({'指标': '回复率', '数值': f"{sub_comments/max(main_comments,1):.1%}"})
        
        # 点赞统计
        max_like = df['like_count'].max()
        avg_like = df['like_count'].mean()
        total_like = df['like_count'].sum()
        
        stats.append({'指标': '最高点赞数', '数值': int(max_like)})
        stats.append({'指标': '平均点赞数', '数值': f"{avg_like:.1f}"})
        stats.append({'指标': '总点赞数', '数值': int(total_like)})
        
        # 用户等级统计
        if 'user_level' in df.columns:
            level_counts = df['user_level'].value_counts().sort_index()
            for level, count in level_counts.items():
                stats.append({'指标': f'Lv{level}用户数', '数值': int(count)})
        
        # VIP用户统计
        if 'vip_status' in df.columns:
            vip_count = df['vip_status'].sum()
            stats.append({'指标': 'VIP用户数', '数值': int(vip_count)})
            stats.append({'指标': 'VIP比例', '数值': f"{vip_count/total_comments:.1%}"})
        
        # 时间范围
        if 'create_time' in df.columns:
            min_time = df['create_time'].min()
            max_time = df['create_time'].max()
            if min_time and max_time:
                time_range = datetime.fromtimestamp(max_time) - datetime.fromtimestamp(min_time)
                stats.append({'指标': '最早评论时间', '数值': datetime.fromtimestamp(min_time).strftime('%Y-%m-%d %H:%M:%S')})
                stats.append({'指标': '最晚评论时间', '数值': datetime.fromtimestamp(max_time).strftime('%Y-%m-%d %H:%M:%S')})
                stats.append({'指标': '评论时间跨度', '数值': f"{time_range.days}天{time_range.seconds//3600}小时"})
        
        return pd.DataFrame(stats)
    
    def print_summary(self, comments: list):
        """打印爬取结果摘要"""
        if not comments:
            return
        
        df = pd.DataFrame(comments)
        
        print("\n" + "=" * 60)
        print("📊 爬取结果摘要")
        print("=" * 60)
        
        # 基本统计
        total = len(df)
        main_comments = len(df[df['parent_comment_id'] == '0'])
        sub_comments = total - main_comments
        
        print(f"总评论数: {total}")
        print(f"主评论数: {main_comments}")
        print(f"子评论数: {sub_comments}")
        print(f"回复率: {sub_comments/max(main_comments,1):.1%}")
        
        # 点赞分析
        max_like = df['like_count'].max()
        avg_like = df['like_count'].mean()
        
        # 找出点赞最高的评论
        top_like = df.loc[df['like_count'].idxmax()] if max_like > 0 else None
        if top_like is not None and not pd.isna(top_like['nickname']):
            print(f"\n🏆 最高点赞评论:")
            print(f"   用户: {top_like['nickname']}")
            print(f"   点赞: {int(top_like['like_count'])}")
            print(f"   内容: {top_like['content'][:50]}...")
        
        print(f"\n📈 点赞统计:")
        print(f"   最高点赞: {int(max_like)}")
        print(f"   平均点赞: {avg_like:.1f}")
        
        # 用户分析
        unique_users = df['user_id'].nunique()
        print(f"\n👥 用户统计:")
        print(f"   参与用户数: {unique_users}")
        print(f"   人均评论数: {total/max(unique_users,1):.1f}")
        
        # 热门用户（评论最多的用户）
        top_users = df['nickname'].value_counts().head(5)
        if not top_users.empty:
            print(f"   评论最多用户TOP5:")
            for i, (user, count) in enumerate(top_users.items(), 1):
                print(f"     {i}. {user}: {count}条")
        
        print("=" * 60)


def main():
    """主函数 - 运行爬虫"""
    print("🚀 B站视频评论爬虫启动")
    print("目标视频ID: 371839463\n")
    
    # 创建爬虫实例
    crawler = BilibiliCommentCrawler()
    
    # 设置爬取参数
    max_pages = 200        # 最大爬取页数（每页约20条主评论）
    max_sub_pages = 10     # 每个评论最大子评论页数
    delay = 2.5          # 基础延迟（秒）
    
    try:
        # 开始爬取
        comments = crawler.crawl_comments(
            max_pages=max_pages,
            max_sub_pages=max_sub_pages,
            delay_base=delay
        )
        
        if comments:
            # 显示摘要
            crawler.print_summary(comments)
            
            # 保存数据
            filename = crawler.save_to_excel(comments)
            
            print(f"\n✅ 任务完成！")
            print(f"📁 数据文件: {filename}")
        else:
            print("\n❌ 未能获取到评论数据")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 爬取过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
