%pip install pandas matplotlib wordcloud openpyxl pillow
import pandas as pd
import matplotlib.pyplot as plt
import wordcloud
import os
import warnings
warnings.filterwarnings('ignore')

# ========================
# 1. 字体配置（按您要求强制设置）
# ========================
def setup_font():
    """强制使用Arial Unicode.ttf，不进行路径检查"""
    font_path = 'Arial Unicode.ttf'  # 按您的要求直接设置
    # 配置中文字体参数
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    print(f"✅ 已按要求设置字体路径：{font_path}")
    return font_path

# 强制设置字体路径
FONT_PATH = setup_font()

# ========================
# 2. 数据读取（桌面文件）
# ========================
def load_data():
    file_path = "/Users/syx/Desktop/副本微博词频_三大类别分类结果.xlsx"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")
    
    df = pd.read_excel(file_path)
    print(f"\n✅ 读取数据成功：{file_path}")
    print(f"类别分布：{df['类别'].unique().tolist()}")
    return df

# ========================
# 3. 词云生成（核心功能）
# ========================
def generate_wordcloud(df, category, params):
    # 筛选数据
    data = df[df['类别'] == category]
    valid_data = data[data['frequency'] > 0].sort_values('frequency', ascending=False)
    if len(valid_data) < 3:
        print(f"⚠️ {category}类数据不足，跳过")
        return
    
    # 词频字典
    word_freq = dict(zip(valid_data['word'], valid_data['frequency']))
    
    # 生成词云（强制使用指定字体）
    try:
        wc = wordcloud.WordCloud(
            font_path=FONT_PATH,  # 强制使用您指定的字体路径
            background_color='white',
            width=params['width'],
            height=params['height'],
            max_words=params['max_words'],
            colormap=params['colormap'],
            min_font_size=14,
            margin=2
        ).generate_from_frequencies(word_freq)
        
        # 保存图片
        plt.figure(figsize=(10, 7))
        plt.imshow(wc)
        plt.axis('off')
        plt.title(f'{category}类词云图', fontsize=18)
        plt.savefig(params['save_path'], dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ {category}词云已保存：{params['save_path']}")
    except Exception as e:
        print(f"❌ {category}生成失败：{str(e)}")
        if "cannot open resource" in str(e):
            print(f"💡 提示：请确保'{FONT_PATH}'字体已安装在系统字体库中")

# ========================
# 4. 主程序
# ========================
def main():
    print("="*60)
    print("  强制使用Arial Unicode.ttf - 词云生成程序  ")
    print("="*60)
    
    try:
        # 读取数据
        df = load_data()
        
        # 类别参数
        categories = {
            '用户体验': {
                'save_path': '/Users/syx/Desktop/用户体验类词云.png',
                'colormap': 'Blues',
                'width': 1000,
                'height': 700,
                'max_words': 80
            },
            '价格': {
                'save_path': '/Users/syx/Desktop/价格类词云.png',
                'colormap': 'Oranges',
                'width': 900,
                'height': 600,
                'max_words': 15
            },
            '门店环境': {
                'save_path': '/Users/syx/Desktop/门店环境类词云.png',
                'colormap': 'Greens',
                'width': 800,
                'height': 500,
                'max_words': 10
            }
        }
        
        # 生成词云
        for cat, params in categories.items():
            generate_wordcloud(df, cat, params)
        
        print("\n🎉 所有词云生成任务已尝试执行（结果取决于字体是否可用）")
        print("生成路径：您的桌面（/Users/syx/Desktop/）")
        
    except Exception as e:
        print(f"\n❌ 程序错误：{str(e)}")

if __name__ == "__main__":
    main()