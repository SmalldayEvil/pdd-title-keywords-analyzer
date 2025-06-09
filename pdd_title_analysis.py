import pandas as pd
import jieba
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import re
import matplotlib.font_manager as fm
import warnings
from datetime import datetime
import base64
from io import BytesIO

# 抑制字体缺失警告
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

def get_available_chinese_fonts():
    """获取系统中可用的中文字体"""
    chinese_fonts = []
    for font in fm.findSystemFonts():
        try:
            font_name = fm.FontProperties(fname=font).get_name()
            # 简单判断是否为中文字体
            if any('\u4e00' <= char <= '\u9fff' for char in font_name) or \
                    any(keyword in font_name.lower() for keyword in ['hei', 'song', 'kai', 'fangsong', 'microsoft yahei']):
                chinese_fonts.append(font_name)
        except Exception:
            continue
    return chinese_fonts

def set_matplotlib_font(font_name):
    """设置matplotlib的默认字体"""
    plt.rcParams["font.family"] = font_name
    # 同时设置matplotlib的sans-serif字体族
    plt.rcParams["font.sans-serif"] = [font_name] + plt.rcParams["font.sans-serif"]

def read_excel_file(file_path):
    """读取Excel文件中的标题数据"""
    try:
        df = pd.read_excel(file_path)
        # 尝试多种可能的标题列名
        possible_columns = ['标题', '商品标题', 'product_title', 'title']
        title_column = None
        
        for col in possible_columns:
            if col in df.columns:
                title_column = col
                break
                
        if title_column is None:
            raise ValueError("Excel文件中未找到标题列，请确保包含以下列名之一: " + ", ".join(possible_columns))
            
        titles = df[title_column].tolist()
        return titles
    except Exception as e:
        raise ValueError(f"读取Excel文件失败: {str(e)}")

def preprocess_text(titles):
    """对标题进行预处理"""
    # 加载停用词
    stopwords = set()
    try:
        with open("stopwords.txt", "r", encoding="utf-8") as f:
            stopwords = set([line.strip() for line in f])
    except FileNotFoundError:
        # 如果没有停用词文件，使用一些常见的中文停用词
        stopwords = {"的", "了", "和", "是", "在", "我", "有", "就", "不", "人", "都", "一", "一个", "上", "也", "很",
                     "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}

    # 分词并过滤停用词
    all_words = []
    for title in titles:
        # 处理非字符串类型
        if not isinstance(title, str):
            title = str(title)
            
        # 去除非中文字符
        title = re.sub(r'[^\u4e00-\u9fa5]', ' ', title)
        # 分词
        words = jieba.cut(title)
        # 过滤停用词和单个字符
        filtered_words = [word for word in words if len(word) > 1 and word.strip() and word not in stopwords]
        all_words.extend(filtered_words)

    return all_words

def analyze_keywords(words, top_n=100):
    """分析关键词频次"""
    if not words:
        raise ValueError("处理后的文本为空，请检查数据和预处理逻辑")
        
    # 统计词频
    word_counts = Counter(words)

    # 获取前N个高频词
    top_words = word_counts.most_common(top_n)

    return top_words, dict(word_counts)

def color_function(word, random_state=None, word_dict=None):
    """词云颜色函数，高频词用红色"""
    if word_dict:
        # 获取频次最高的前三个词
        top_three = [word for word, _ in sorted(word_dict.items(), key=lambda item: item[1], reverse=True)[:3]]
        if word in top_three:
            return "red"
    return "black"

def generate_wordcloud(word_dict):
    """生成词云图并返回Base64编码字符串"""
    if not word_dict:
        raise ValueError("没有足够的关键词数据生成词云")
        
    # 获取可用的中文字体
    chinese_fonts = get_available_chinese_fonts()

    if not chinese_fonts:
        print("警告：未找到系统中可用的中文字体！")
        print("请安装中文字体(如SimHei、Microsoft YaHei等)后重试")
        return None

    # 使用第一个找到的中文字体
    font_name = chinese_fonts[0]
    font_path = None

    for font in fm.findSystemFonts():
        try:
            prop = fm.FontProperties(fname=font)
            if prop.get_name() == font_name:
                font_path = font
                break
        except:
            continue

    if not font_path:
        print("警告：无法确定中文字体的路径！")
        print("请确保已安装中文字体，并指定正确的字体路径。")
        return None

    # 设置matplotlib的默认字体
    set_matplotlib_font(font_name)

    # 创建词云对象
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=600,
        background_color="white",
        max_words=200,
        contour_width=3,
        contour_color='steelblue',
        color_func=lambda *args, **kwargs: color_function(*args, word_dict=word_dict)
    )

    # 生成词云
    wc.generate_from_frequencies(word_dict)

    # 将词云图保存为字节流
    img = BytesIO()
    wc.to_image().save(img, format='PNG')
    img.seek(0)

    # 将字节流转换为Base64编码字符串
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

    return img_base64

def display_top_keywords(top_words):
    """格式化显示前N个高频词"""
    return [f"{i}. {word}: {count}次" for i, (word, count) in enumerate(top_words[:20], 1)]

def analyze_file(file_path):
    """分析文件并返回结果"""
    # 读取标题数据
    titles = read_excel_file(file_path)
    print(f"共读取 {len(titles)} 个标题")

    if not titles:
        raise ValueError("Excel文件中没有找到有效的标题数据")

    # 预处理文本
    words = preprocess_text(titles)

    # 分析关键词
    top_words, word_dict = analyze_keywords(words)

    # 显示高频词
    top_20 = display_top_keywords(top_words)

    # 生成词云
    wordcloud_base64 = generate_wordcloud(word_dict)

    if wordcloud_base64 is None:
        raise ValueError("生成词云图失败，请检查字体设置和文件保存路径。")

    return top_20, wordcloud_base64