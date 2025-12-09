import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')
df_wordfreq = pd.read_excel('/wangziyi/工作簿4.xlsx')
df_filtered = df_wordfreq[df_wordfreq['frequency'] >= 2].copy()  # 过滤低频词
print(f"有效词频数据：{len(df_filtered)}个词语")
pet_burial_df = pd.read_csv('/wangziyi/宠物殡葬.csv')

# 读取动物无害化处理数据
animal_disposal_df = pd.read_csv('/wangziyi/动物无害化处理.csv')

# 合并两个数据集中的企业名称列
combined_names = pd.concat([pet_burial_df['企业名称'], animal_disposal_df['企业名称']], ignore_index=True)

# 由于原始数据集中有省份信息，这里假设可以从企业名称中提取地域信息（如果实际不是这样，请提供更明确的方式）
# 这里简单以省份为地域信息示例，从 df 中获取省份信息
province_info = df[df['企业名称'].isin(combined_names)][['企业名称', '所属省份']]

# 对地域（省份）进行总结
region_summary = province_info['所属省份'].value_counts()

print('地域（省份）总结：')
print(region_summary)
import matplotlib.pyplot as plt

# 提取成立日期中的年份
selected_data['成立年份'] = pd.to_datetime(selected_data['成立日期']).dt.year

# 统计每年成立的企业数量
yearly_counts = selected_data['成立年份'].value_counts().sort_index().reset_index(name='企业数量')
