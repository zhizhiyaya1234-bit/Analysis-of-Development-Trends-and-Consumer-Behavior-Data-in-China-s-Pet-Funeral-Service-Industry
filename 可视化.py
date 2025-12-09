import pandas as pd
import re
from snownlp import SnowNLP
import numpy as np
df = pd.read_excel("/Users/wangziyi/Desktop/数据评论.xlsx")
print("数据形状（行数, 列数）:", df.shape)
print("\n数据列名:")
print(df.columns.tolist())
print("\n前3条数据预览:")
print(df.head(3))
def clean_weibo_comment(text):
    # 处理空值/非字符串类型
    if pd.isna(text) or not isinstance(text, str):
        return ""
    # 去除URL链接
    text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text)
    # 去除HTML标签（若有）
    text = re.sub(r"<.*?>", "", text)
    # 去除特殊符号、表情符号（保留中文、英文、数字）
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", text)
    # 去除多余空格
    text = re.sub(r"\s+", " ", text).strip()
    return text
comment_column = "comment"  
df["cleaned_comment"] = df[comment_column].apply(clean_weibo_comment)
def analyze_sentiment(text):
    if not text:
        return np.nan, "未知"  # 空文本标记为"未知"
    s = SnowNLP(text)
    sentiment_score = round(s.sentiments, 4)  # 保留4位小数
    if sentiment_score >= 0.6:
        sentiment_label = "积极"
    elif sentiment_score <= 0.4:
        sentiment_label = "消极"
    else:
        sentiment_label = "中性"
    return sentiment_score, sentiment_label
print("\n正在执行情感分析...")
sentiment_results = df["cleaned_comment"].apply(analyze_sentiment)
df[["sentiment_score", "sentiment_label"]] = pd.DataFrame(
    sentiment_results.tolist(),
    index=df.index
)
df_cleaned = df.dropna(subset=["sentiment_score"])
print(f"\n情感分析完成！有效分析数据行数：{len(df_cleaned)}")
print("\n情感标签分布统计:")
sentiment_count = df_cleaned["sentiment_label"].value_counts()
print(sentiment_count)
print(f"\n积极评论占比：{round(sentiment_count.get('积极', 0)/len(df_cleaned)*100, 2)}%")
print(f"消极评论占比：{round(sentiment_count.get('消极', 0)/len(df_cleaned)*100, 2)}%")
print(f"中性评论占比：{round(sentiment_count.get('中性', 0)/len(df_cleaned)*100, 2)}%")
output_path = "/Users/wangziyi/Desktop/工作簿4.xlsx"
df_cleaned.to_excel(output_path, index=False)
print(f"\n结果已保存至：{output_path}")
print("\n前5条完整结果预览:")
print(df_cleaned[[comment_column, "cleaned_comment", "sentiment_score", "sentiment_label"]].head())
conda install -c conda-forge wordcloud
conda install -c conda-forge jieba
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import jieba
from collections import Counter
import numpy as np
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题
def plot_sentiment_distribution(df):
    # 统计各情感标签数量
    sentiment_counts = df["sentiment_label"].value_counts()
    
    # 创建画布
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values, palette="Set2")
    
    # 添加数值标签
    for i, v in enumerate(sentiment_counts.values):
        ax.text(i, v + 5, f"{v}条\n({v/len(df):.1%})", ha="center", fontsize=12)
plt.title("微博评论情感分布", fontsize=15)
plt.xlabel("情感标签", fontsize=12)
plt.ylabel("评论数量", fontsize=12)
plt.tight_layout()  # 调整布局
plt.savefig("情感分布柱状图.png", dpi=300)  # 保存图片
plt.show()
def plot_sentiment_pie(df):
    sentiment_counts = df["sentiment_label"].value_counts()
    
    plt.figure(figsize=(8, 8))
    wedges, texts, autotexts = plt.pie(
        sentiment_counts.values,
        labels=sentiment_counts.index,
        autopct="%1.1f%%",  # 显示百分比
        startangle=90,
        colors=["#52c41a", "#faad14", "#f5222d"],  # 积极/中性/消极颜色
        textprops={"fontsize": 12}
    )
    
    # 突出显示占比最大的部分
    wedges[np.argmax(sentiment_counts.values)].set_edgecolor("white")
    wedges[np.argmax(sentiment_counts.values)].set_linewidth(2)
    
    plt.title("微博评论情感占比", fontsize=15)
    plt.tight_layout()
    plt.savefig("情感占比饼图.png", dpi=300)
    plt.show()
def load_stopwords():
    # 基础停用词表（可根据需求扩展）
    stopwords = set([
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也",
        "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "微博", "转发"
    ])
    # 可选：从文件读取更多停用词（若有stopwords.txt文件）
    try:
        with open("stopwords.txt", "r", encoding="utf-8") as f:
            stopwords.update([line.strip() for line in f.readlines()])
    except FileNotFoundError:
        pass  # 无文件则使用默认停用词
    return stopwords
ef get_top_words(texts, stopwords, top_n=50):
    # 分词
    words = []
    for text in texts:
        if isinstance(text, str) and text.strip():
            # 使用jieba精确分词
            seg_list = jieba.cut(text.strip(), cut_all=False)
            # 过滤停用词和单字
            words.extend([word for word in seg_list if word not in stopwords and len(word) > 1])
    # 统计高频词
    word_counts = Counter(words).most_common(top_n)
    return dict(word_counts)
def plot_sentiment_wordcloud(df, stopwords):
    # 按情感标签分组
    sentiment_groups = df.groupby("sentiment_label")
    
    # 为每个情感类别绘制词云
    for label, group in sentiment_groups:
        # 获取该情感类别的所有清洗后评论
        texts = group["cleaned_comment"].tolist()
        # 提取高频词
        top_words = get_top_words(texts, stopwords)
        
        # 创建词云
        wc = WordCloud(
            font_path="PingFang.ttc",  # 确保有中文字体（若无，可删除此参数用默认）
            background_color="white",
            width=800,
            height=600,
            max_words=50
        ).generate_from_frequencies(top_words)
from wordcloud import WordCloud
import matplotlib.pyplot as plt
def generate_wordcloud(label, top_words, save_path):
    if not top_words:
        return
color_map = {
        "积极": "Pastel1",    # 清新暖色调（适合积极评论）
        "中性": "Set2",       # 柔和多色（适合中性评论）
        "消极": "cool_r"      # 冷色调反转（适合消极评论）
    }
    df_sentiment['sentiment_category'] = df_sentiment['sentiment_score'].apply(classify_sentiment)
    
    # 统计情感分布
sentiment_counts = df_sentiment['sentiment_category'].value_counts()
print("\n情感分析结果统计：")
for category, count in sentiment_counts.items():
    percentage = count / len(df_sentiment) * 100
    print(f"{category}评论：{count}条 ({percentage:.1f}%)")
    
return df_sentiment, sentiment_counts

# 执行情感分析
df_sentiment, sentiment_counts = sentiment_analysis(df_clean)

# 查看情感分析结果示例
print("\n情感分析结果示例（前5条）：")
sample_cols = ['clean_comment', 'sentiment_score', 'sentiment_category']
print(df_sentiment[sample_cols].head())

# 保存情感分析结果到Excel
output_file = '/mnt/微博评论情感分析结果.xlsx'
df_sentiment.to_excel(output_file, index=False)
print(f"\n情感分析结果已保存到：{output_file}")
def create_sentiment_visualization(sentiment_counts):
    """创建情感分析可视化图表"""
    # 设置清新淡雅的颜色方案
    colors = ['#A8DADC', '#F1FAEE', '#FFB703', '#FB8500']  # 淡蓝、淡白、淡黄、淡橙
    sentiment_colors = {'积极': '#A8DADC', '中性': '#F1FAEE', '消极': '#FFB703'}
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('微博评论情感分析结果', fontsize=20, fontweight='bold', y=0.95, color='#264653')
    
    # 3.1 饼图 - 情感分布
    wedges, texts, autotexts = ax1.pie(sentiment_counts.values, 
                                       labels=sentiment_counts.index,
                                       colors=[sentiment_colors[cat] for cat in sentiment_counts.index],
                                       autopct='%1.1f%%',
                                       startangle=90,
                                       textprops={'fontsize': 12, 'color': '#264653'})
    
    # 美化饼图文字
    for autotext in autotexts:
        autotext.set_color('#264653')
        autotext.set_fontweight('bold')
    
    ax1.set_title('情感分布占比', fontsize=16, fontweight='bold', pad=20, color='#264653')
    
    # 3.2 柱状图 - 情感数量
    bars = ax2.bar(sentiment_counts.index, sentiment_counts.values,
                   color=[sentiment_colors[cat] for cat in sentiment_counts.index],
                   edgecolor='#264653', linewidth=1.5, alpha=0.8)
    # 在柱子上添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 5,
                 f'{int(height)}条', ha='center', va='bottom',
                 fontsize=12, fontweight='bold', color='#264653')
    
    # 设置柱状图样式
    ax2.set_title('各情感类别评论数量', fontsize=16, fontweight='bold', pad=20, color='#264653')
    ax2.set_ylabel('评论数量（条）', fontsize=12, color='#264653')
    ax2.set_xlabel('情感类别', fontsize=12, color='#264653')
    
    # 设置网格
    ax2.grid(axis='y', alpha=0.3, color='#264653', linestyle='--')
    ax2.set_axisbelow(True)
    
    # 美化坐标轴
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#264653')
    ax2.spines['bottom'].set_color('#264653')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig('/mnt/微博评论情感分析可视化.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    
    print("情感分析可视化图表已保存为：微博评论情感分析可视化.png")

# 执行情感可视化
create_sentiment_visualization(sentiment_counts)
if __name__ == "__main__":
    print("开始生成情感分布图表...")
    plot_sentiment_distribution(df)  # 情感分布柱状图
    
    print("开始生成情感占比饼图...")
    plot_sentiment_pie(df)  # 情感占比饼图
    
    print("加载停用词并生成词云...")
    stopwords = load_stopwords()
    plot_sentiment_wordcloud(df, stopwords)  # 分情感词云

    print("所有可视化结果已保存为PNG图片！")