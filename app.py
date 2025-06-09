# app.py
from flask import Flask, render_template, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from pdd_title_analysis import analyze_file
import logging
import socket

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """渲染上传页面"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """处理文件上传和分析"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        
        # 检查用户是否选择了文件
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        # 检查文件类型是否允许
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件类型，仅支持.xlsx和.xls'}), 400
        
        # 生成安全的文件名
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 保存文件
        file.save(file_path)
        logger.info(f"文件已保存: {file_path}")
        
        # 分析文件
        top_20, wordcloud_base64 = analyze_file(file_path)
        
        # 准备返回数据
        result = {
            'top_keywords': top_20,
            'wordcloud_base64': wordcloud_base64
        }
        
        return render_template('result.html', **result)
    
    except Exception as e:
        logger.error(f"分析过程中出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'分析失败: {str(e)}'}), 500
    
    finally:
        # 无论成功或失败都删除上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"临时文件已删除: {file_path}")

@app.errorhandler(413)
def request_entity_too_large(error):
    """处理文件大小超出限制的错误"""
    return jsonify({'error': '文件大小超出限制 (最大16MB)'}), 413

if __name__ == '__main__':
    try:
        # 获取本地 IP 地址
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # 尝试查找可用端口
        port = 5000
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                if result != 0:
                    break
                logger.warning(f"端口 {port} 已被占用，尝试使用 {port + 1}")
                port += 1
        
        logger.info(f"应用将在 http://{local_ip}:{port} 上运行")
        logger.info(f"也可以通过 http://localhost:{port} 访问")
        
        # 设置监听所有可用的网络接口
        app.run(host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.critical(f"应用启动失败: {str(e)}", exc_info=True)
        print(f"应用启动失败: {str(e)}")
        print("请确保没有其他应用占用端口，并且已安装所有依赖。")