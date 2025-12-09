import os
import requests
import pandas as pd
import datetime
from time import sleep
import random
# from fake_useragent import UserAgent
import re
def trans_time(v_str):
    """转换GMT时间为标准格式"""
    GMT_FORMAT = '%a %b %d %H:%M:%S +0800 %Y'
    timeArray = datetime.datetime.strptime(v_str, GMT_FORMAT)
    ret_time = timeArray.strftime("%Y-%m-%d %H:%M:%S")
    return ret_time
def tran_gender(gender_tag):
    """转换性别"""
    if gender_tag == 'm':
        return '男'
    elif gender_tag == 'f':
        return '女'
    else:  # -1
        return '未知'
def get_comments(v_weibo_ids, v_comment_file, v_max_page):
    """
    爬取微博评论
    :param v_weibo_id: 微博id组成的列表
    :param v_comment_file: 保存文件名
    :param v_max_page: 最大页数
    :return: None
    """
    for weibo_id in v_weibo_ids:
        print(f'开始爬取微博ID: {weibo_id}')
        # 初始化max_id
        max_id = '0'
        # 初始化连续失败计数器
        consecutive_failures = 0
        # 爬取前n页，可任意修改
        for page in range(1, v_max_page + 1):
            wait_seconds = random.uniform(0, 1)  # 等待时长秒
            print('开始等待{}秒'.format(wait_seconds))
            sleep(wait_seconds)  # 随机等待
            print('开始爬取第{}页'.format(page))
            if page == 1:  # 第一页，没有max_id参数
                url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id_type=0'.format(weibo_id, weibo_id)
            else:  # 非第一页，需要max_id参数
                if str(max_id) == '0':  # 如果发现max_id为0，说明没有下一页了，break结束循环
                    print('max_id is 0, break now')
                    break
                url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id_type=0&max_id={}'.format(weibo_id,
                                                                                                        weibo_id,
                                                                                                        max_id)
            # 发送请求
            # ua = UserAgent(verify_ssl=False)
            headers = {
                "user-agent": 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
                # 如果cookie失效，会返回-100响应码
                "cookie": "SCF=AoFJYrZTwGmTshIOqU4XM_wl1jJ-zz9ImSihXG7A2Mdtdtij_Pin1t-0AJmk9mKWlEZd1Z94YgKd_-EOgP9-aD4.; ALF=1764067176; SUB=_2A25F-Yo4DeRhGeFG41MS-S3LyTSIHXVndoPwrDV8PUJbkNANLXKgkW1NeNXnrwxLloLQ4PUB3LhgUZW6fFVVPlZA; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WWBScXJ4z.-UXG95R_XoX4N5JpX5KMhUgL.FoMR1h201KeNeon2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMN1hnpe0.0S0zR; SINAGLOBAL=3682539800686.303.1761475187742; ULV=1761639471464:3:3:3:43669868734.157455.1761639471462:1761585572566; PC_TOKEN=5a1feb3bf3; XSRF-TOKEN=bqxChH7-YGcvpp6oBWM0z0DY; WBPSESS=iYR8mHPW8f6JwXuDuy8Ayk7QLuWcLJbhIzjG1sNerg9R5cgnna8g1O8OeODE88_4I3LHGaqM4NJhbglwZDYoq2-b7RmPMrbn3v8_HD9EgbLkP0BDRsC4rYUEXOZLE4m8aoq0tVvb326uGuMiIyWNdg==",
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "referer": "https://m.weibo.cn/detail/{}".format(weibo_id),
                "x-requested-with": "XMLHttpRequest",
                "mweibo-pwa": '1',
            }
            r = requests.get(url, headers=headers)  # 发送请求
            print(r.status_code)  # 查看响应码
            print(r.json())  # 查看响应内容
            
            # 检查响应是否为 {'ok': 0}
            if r.json().get('ok') == 0:
                consecutive_failures += 1
                print(f'失败次数: {consecutive_failures}')
                if consecutive_failures >= 2:
                    print(f'连续 {consecutive_failures} 次失败，停止爬取当前帖子')
                    break
                continue
            else:
                # 如果成功，重置失败计数器
                consecutive_failures = 0
                
            try:
                max_id = r.json()['data']['max_id']  # 获取max_id给下页请求用
                datas = r.json()['data']['data']
            except Exception as e:
                print('excepted: ' + str(e))
                print('Response content:', r.text[:200])  # 打印部分响应内容
                continue
            page_list = []  # 评论页码
            id_list = []  # 评论id
            text_list = []  # 评论内容
            time_list = []  # 评论时间
            like_count_list = []  # 评论点赞数
            source_list = []  # 评论者IP归属地
            user_name_list = []  # 评论者姓名
            user_id_list = []  # 评论者id
            user_gender_list = []  # 评论者性别
            follow_count_list = []  # 评论者关注数
            followers_count_list = []  # 评论者粉丝数
            for data in datas:
                page_list.append(page)
                id_list.append(data['id'])
                dr = re.compile(r'<[^>]+>', re.S)  # 用正则表达式清洗评论数据
                text2 = dr.sub('', data['text'])
                text_list.append(text2)  # 评论内容
                time_list.append(trans_time(v_str=data['created_at']))  # 评论时间
                like_count_list.append(data['like_count'])  # 评论点赞数
                source_list.append(data['source'])  # 评论者IP归属地
                user_name_list.append(data['user']['screen_name'])  # 评论者姓名
                user_id_list.append(data['user']['id'])  # 评论者id
                user_gender_list.append(tran_gender(data['user']['gender']))  # 评论者性别
                follow_count_list.append(data['user']['follow_count'])  # 评论者关注数
                followers_count_list.append(data['user']['followers_count'])  # 评论者粉丝数
            df = pd.DataFrame(
                {
                    'max_id': max_id,
                    '微博id': [weibo_id] * len(time_list),
                    '评论页码': page_list,
                    '评论id': id_list,
                    '评论时间': time_list,
                    '评论点赞数': like_count_list,
                    '评论者IP归属地': source_list,
                    '评论者姓名': user_name_list,
                    '评论者id': user_id_list,
                    '评论者性别': user_gender_list,
                    '评论者关注数': follow_count_list,
                    '评论者粉丝数': followers_count_list,
                    '评论内容': text_list,
                }
            )
            if os.path.exists(v_comment_file):  # 如果文件存在，不再设置表头
                header = False
            else:  # 否则，设置csv文件表头
                header = True
            # 保存csv文件
            df.to_csv(v_comment_file, mode='a+', index=False, header=header, encoding='utf_8_sig')
            print('结果保存成功:{}'.format(v_comment_file))

def read_weibo_ids_from_csv(csv_file):
    """
    从CSV文件中读取微博ID
    :param csv_file: CSV文件路径
    :return: 微博ID列表
    """
    try:
        df = pd.read_csv(csv_file)
        if 'id' in df.columns:
            # 确保ID是字符串类型
            weibo_ids = df['id'].astype(str).tolist()
            print(f'从CSV文件中读取了 {len(weibo_ids)} 个微博ID')
            return weibo_ids
        else:
            print('CSV文件中没有找到"id"列')
            return []
    except Exception as e:
        print(f'读取CSV文件出错: {str(e)}')
        return []

if __name__ == '__main__':
    # 从CSV文件读取微博ID
    csv_input_file = r'results\weibo_宠物殡葬_20251102_163536.csv'  # 输入CSV文件路径
    weibo_id_list = read_weibo_ids_from_csv(csv_input_file)
    
    if not weibo_id_list:
        print('没有找到微博ID，使用默认ID')
        weibo_id_list = ['5169109194771664']  # 如果没有读取到ID，使用默认ID
    
    max_page = 10  # 爬取最大页数
    comment_file = '数据评论.csv'
    # 如果结果文件存在，先删除
    if os.path.exists(comment_file):
        os.remove(comment_file)
    # 爬取评论
    get_comments(v_weibo_ids=weibo_id_list, v_comment_file=comment_file, v_max_page=max_page)
