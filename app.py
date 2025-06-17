from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import db, Interpretation, CharacterDecomposition
from config import Config
import requests
import json
import random
import os
import re

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secret-key" # 添加密钥用于session
db.init_app(app)

def is_valid_chinese(text):
    """验证输入是否为4字以内的汉字"""
    if not text:
        return False
    # 检查是否只包含汉字
    if not re.match('^[\u4e00-\u9fa5]+$', text):
        return False
    # 检查长度是否在4字以内
    return len(text) <= 4

def contains_sensitive_content(content):
    """检查内容是否包含敏感信息"""
    # 定义敏感词列表
    sensitive_words = [
        # 政治相关
        '政治', '政府', '国家', '主席', '总理', '领导人', '官员', '腐败', '革命',
        '民主', '自由', '游行', '示威', '抗议', '政变', '政权', '独裁', '专制',
        '制度', '体制', '选举', '投票', '宪法', '法律', '法规', '条例',
        # 暴力相关
        '血腥', '杀戮', '自杀', '凶杀', '残害', '虐待',
        '伤害', '斗殴', '械斗', '恐怖', '威胁',
        '绑架', '勒索', '欺凌', '霸凌', '暴乱', '骚乱',
        # 色情相关
        '色情', '淫秽', '情色'
    ]
    
    if isinstance(content, dict):
        # 将字典值转换为字符串进行检查
        content_str = json.dumps(content, ensure_ascii=False)
    else:
        content_str = str(content)
    
    return any(word in content_str for word in sensitive_words)

def get_color_scheme(sentiment):
    """根据情感选择合适的色系"""
    # 这里可以根据情感分析结果选择不同的色系
    # 暂时随机返回一个色系
    return random.choice(list(Config.COLOR_SCHEMES.keys()))

def call_llm_api(keyword):
    """调用硅基API获取词语解释"""
    headers = {
        "Authorization": f"Bearer {app.config['API_KEY']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "Pro/deepseek-ai/DeepSeek-V3",  # 使用默认模型
        "messages": [
            {
                "role": "system",
                "content": "你是新汉语老师，你年轻,批判现实,思考深刻,语言风趣。你的行文风格和'Oscar Wilde' '鲁迅' '林语堂'等大师高度一致，你擅长一针见血的表达隐喻，你对现实的解释文艺幽默。但请特别注意！输出内容不能是恶意的政治隐喻！输出内容不能是恶意的政治隐喻！输出内容不能是恶意的政治隐喻！"
            },
            {
                "role": "user",
                "content": f"将一个汉语词汇进行全新角度的解释，你会用一个特殊视角来解释一个词汇：用一句话表达你的词汇解释，抓住用户输入词汇的本质，使用文艺的表达、一针见血的指出本质，使用包含隐喻的金句。例如：“死亡”： '生命向宇宙递交的, 最后一份请假条' 现在请解释词语'{keyword}'，输出格式：标准的可直接解析JSON格式，直接用花括号包裹，没有其他字符，包含：原词语、拼音、英文翻译、日文翻译、解释（按现代诗排版，尽量精简，三行内解释完毕）请特别注意：有关政治的词汇，请用正面、爱国的解释！"
            }
        ],
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "response_format": {
            "type": "text"
        }
    }
    
    try:
        # 记录API请求
        print(f"正在调用API解释词语: {keyword}")
        print(f"请求URL: {app.config['API_URL']}")
        
        response = requests.post(
            app.config['API_URL'],
            headers=headers,
            json=data,
            timeout=30  # 添加超时设置
        )
        
        # 记录API响应状态
        print(f"API响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                # 记录API返回的原始内容
                print(f"API原始响应: {result}")
                
                # 检查响应格式
                if not isinstance(result, dict) or 'choices' not in result:
                    print("API响应格式错误：缺少choices字段")
                    return None
                    
                content = result['choices'][0]['message']['content']
                # 记录解析后的内容
                print(f"解析到的content内容: {content}")
                
                try:
                    # 尝试解析JSON内容
                    parsed_content = json.loads(content)
                    # 验证必要字段
                    required_fields = ['原词语', '拼音', '英文翻译', '日文翻译', '解释']
                    for field in required_fields:
                        if field not in parsed_content:
                            print(f"解析后的内容缺少必要字段: {field}")
                            return None
                    return parsed_content
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {str(e)}")
                    print(f"无法解析的内容: {content}")
                    return None
            except KeyError as e:
                print(f"API响应格式错误: {str(e)}")
                print(f"完整响应内容: {response.text}")
                return None
        else:
            print(f"API调用失败: HTTP {response.status_code}")
            print(f"错误响应: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"API请求异常: {str(e)}")
        return None
    except Exception as e:
        print(f"未预期的错误: {str(e)}")
        print(f"错误类型: {type(e)}")
        return None

def call_decomposition_api(character):
    """调用硅基API获取汉字拆解"""
    headers = {
        "Authorization": f"Bearer {app.config['API_KEY']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "Pro/deepseek-ai/DeepSeek-V3",  # 使用默认模型
        "messages": [
            {
                "role": "system",
                "content": """
【字师角色设定】
你是一名字师，具有以下特质：
- 痴迷文字研究八十载，独创"形意解字法"
- 核心信念：字藏道、形載理、义傳神
- 表达风格：直白、深刻、有洞察力
- 核心技能：拆字、释义、联系生活

【解字流程】
1. 拆字阶段：
    1.1 按最小单元顺序拆解汉字(包括部首)
    1.2 将每个部首与日常生活情节关联
    1.3 组合成有戏剧冲突的微型故事

2. 解读阶段：
    2.1 突破常规思维框架
    2.2 采用第二人称视角
    2.3 **提炼为一句精炼的反问句(当头棒喝式)**
    2.4 最终解读要扣人心弦、引人深思

【示例参考】
- 汉字“穷”
{
    "原字": "穷",
    "拆解": ["宀(固定地方)", "八(八个小时)", "力(卖力工作)"],
    "解读": ["在一个固定地方，", "每天8个小时，", "卖力地工作。", "这就是你想要的人生吗？"]
}

【输出规范】
- 标准的可直接解析JSON格式，直接用花括号包裹，没有其他字符，有三个key：原字、拆解、解读，原字的value以字符串给出，拆解、解读的value以列表形式提供
- 保持核心思想和流程
- 使用简洁明了的中文表述
"""
            },
            {
                "role": "user",
                "content": f"请对汉字'{character}'进行拆解，输出格式：标准的可直接解析JSON格式，直接用花括号包裹，没有其他字符，有三个key：原字、拆解、解读，原字的value以字符串给出，拆解、解读的value以列表形式提供"
            }
        ],
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "frequency_penalty": 0.5,
        "response_format": {
            "type": "text"
        }
    }
    
    try:
        # 记录API请求
        print(f"正在调用API拆解汉字: {character}")
        print(f"请求URL: {app.config['API_URL']}")
        
        response = requests.post(
            app.config['API_URL'],
            headers=headers,
            json=data,
            timeout=30  # 添加超时设置
        )
        
        # 记录API响应状态
        print(f"API响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                # 记录API返回的原始内容
                print(f"API原始响应: {result}")
                
                # 检查响应格式
                if not isinstance(result, dict) or 'choices' not in result:
                    print("API响应格式错误：缺少choices字段")
                    return None
                    
                content = result['choices'][0]['message']['content']
                # 记录解析后的内容
                print(f"解析到的content内容: {content}")
                
                try:
                    # 尝试解析JSON内容
                    parsed_content = json.loads(content)
                    # 验证必要字段
                    required_fields = ['原字', '拆解', '解读']
                    for field in required_fields:
                        if field not in parsed_content:
                            print(f"解析后的内容缺少必要字段: {field}")
                            return None
                    return parsed_content
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {str(e)}")
                    print(f"无法解析的内容: {content}")
                    return None
            except KeyError as e:
                print(f"API响应格式错误: {str(e)}")
                print(f"完整响应内容: {response.text}")
                return None
        else:
            print(f"API调用失败: HTTP {response.status_code}")
            print(f"错误响应: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"API请求异常: {str(e)}")
        return None
    except Exception as e:
        print(f"未预期的错误: {str(e)}")
        print(f"错误类型: {type(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/explain', methods=['POST'])
def explain_word():
    keyword = request.form.get('keyword')
    if not keyword:
        return jsonify({'error': '请输入词语'}), 400
    
    # 验证输入是否为4字以内的汉字
    if not is_valid_chinese(keyword):
        return jsonify({'error': '请输入4字以内的汉字'}), 400
    
    print(f"处理关键词: {keyword}")
    
    # 检查数据库
    interpretation = Interpretation.query.filter_by(keyword=keyword).first()
    
    if not interpretation:
        print("数据库中未找到解释，调用API获取新解释")
        # 调用API获取新解释
        result = call_llm_api(keyword)
        if not result:
            print("API调用失败")
            return jsonify({'error': '获取解释失败，请重试'}), 500
        
        # 检查API返回的内容是否包含敏感信息
        if contains_sensitive_content(result):
            return jsonify({'redirect': url_for('content_warning')}), 200
            
        print("API调用成功，保存到数据库")
        # 保存到数据库
        interpretation = Interpretation(
            keyword=keyword,
            content=json.dumps(result, ensure_ascii=False)
        )
        db.session.add(interpretation)
        db.session.commit()
    else:
        # 检查数据库中的内容是否包含敏感信息
        if contains_sensitive_content(interpretation.content):
            return jsonify({'redirect': url_for('content_warning')}), 200
    
    # 获取色系
    color_scheme = get_color_scheme(keyword)
    colors = Config.COLOR_SCHEMES[color_scheme]
    
    try:
        # 转换数据格式
        raw_data = json.loads(interpretation.content)
        print(f"解析后的数据: {raw_data}")
        
        # 检查必要字段是否存在
        required_fields = ['原词语', '拼音', '英文翻译', '日文翻译', '解释']
        missing_fields = [field for field in required_fields if field not in raw_data]
        if missing_fields:
            print(f"数据缺少必要字段: {missing_fields}")
            return jsonify({'error': '数据格式错误，请重试'}), 500
        
        # 处理拼音首字母大写
        pinyin = raw_data['拼音']
        if isinstance(pinyin, str):
            pinyin = ' '.join(word.capitalize() for word in pinyin.split())
        
        # 处理英文首字母大写
        english = raw_data['英文翻译']
        if isinstance(english, str):
            english = english.title()
        
        # 处理解释字段的换行
        explanation = raw_data['解释']
        if isinstance(explanation, list):
            explanation = '\n'.join(explanation)
        elif isinstance(explanation, str):
            # 如果解释是字符串，尝试按标点符号分割
            explanation = explanation.replace('。', '。\n').replace('，', '，\n')
            # 移除多余的空行
            explanation = '\n'.join(line.strip() for line in explanation.split('\n') if line.strip())
            
        formatted_data = {
            'keyword': raw_data['原词语'],
            'pinyin': pinyin,
            'english': english,
            'japanese': raw_data['日文翻译'],
            'explanation': explanation
        }
        
        print(f"格式化后的数据: {formatted_data}")
        print("数据格式化成功，渲染结果页面")
        
        # 将数据存储在session中
        session['interpretation'] = formatted_data
        session['colors'] = colors
        
        # 返回重定向URL
        return jsonify({'redirect': url_for('result')})
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return jsonify({'error': '数据格式错误，请重试'}), 500
    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        return jsonify({'error': '获取解释失败，请重试'}), 500

@app.route('/result')
def result():
    if 'interpretation' not in session or 'colors' not in session:
        return redirect(url_for('index'))
    return render_template(
        'result.html',
        interpretation=session['interpretation'],
        colors=session['colors']
    )

@app.route('/content-warning')
def content_warning():
    return render_template('content_warning.html')

@app.route('/decompose', methods=['POST'])
def decompose_character():
    character = request.form.get('character')
    if not character:
        return jsonify({'error': '请输入汉字'}), 400
    
    # 验证输入是否为单个汉字
    if not re.match('^[\u4e00-\u9fa5]$', character):
        return jsonify({'error': '请输入单个汉字'}), 400
    
    print(f"处理汉字: {character}")
    
    # 检查数据库
    decomposition = CharacterDecomposition.query.filter_by(keyword=character).first()
    
    if not decomposition:
        print("数据库中未找到拆解，调用API获取新拆解")
        # 调用API获取新拆解
        result = call_decomposition_api(character)
        if not result:
            print("API调用失败")
            return jsonify({'error': '获取拆解失败，请重试'}), 500
        
        # 检查API返回的内容是否包含敏感信息
        if contains_sensitive_content(result):
            return jsonify({'redirect': url_for('content_warning')}), 200
            
        print("API调用成功，保存到数据库")
        # 保存到数据库
        decomposition = CharacterDecomposition(
            keyword=character,
            content=json.dumps(result, ensure_ascii=False)
        )
        db.session.add(decomposition)
        db.session.commit()
    else:
        # 检查数据库中的内容是否包含敏感信息
        if contains_sensitive_content(decomposition.content):
            return jsonify({'redirect': url_for('content_warning')}), 200
    
    # 获取色系
    color_scheme = get_color_scheme(character)
    colors = Config.COLOR_SCHEMES[color_scheme]
    
    try:
        # 转换数据格式
        raw_data = json.loads(decomposition.content)
        print(f"解析后的数据: {raw_data}")
        
        # 检查必要字段是否存在
        required_fields = ['原字', '拆解', '解读']
        missing_fields = [field for field in required_fields if field not in raw_data]
        if missing_fields:
            print(f"数据缺少必要字段: {missing_fields}")
            return jsonify({'error': '数据格式错误，请重试'}), 500
        
        # 处理拆解和解读字段
        decomposition_text = ""
        interpretation_text = ""
        
        # 处理拆解字段
        if isinstance(raw_data['拆解'], list):
            new_list = [" - " + item for item in raw_data['拆解']]
            decomposition_text = '\n'.join(new_list)
        else:
            decomposition_text = str(raw_data['拆解'])
            
        # 处理解读字段
        if isinstance(raw_data['解读'], list):
            new_list = [" " + item for item in raw_data['解读']]
            interpretation_text = '\n'.join(new_list)
        else:
            interpretation_text = str(raw_data['解读'])
        
        # 将数据存储在session中
        session['original_char'] = raw_data['原字']
        session['decomposition'] = decomposition_text
        session['interpretation'] = interpretation_text
        session['colors'] = colors
        
        print(f"处理后的数据: 原字={raw_data['原字']}, 拆解长度={len(decomposition_text)}, 解读长度={len(interpretation_text)}")
        print("数据格式化成功，渲染结果页面")
        
        # 返回重定向URL
        return jsonify({'redirect': url_for('decompose_result')})
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return jsonify({'error': '数据格式错误，请重试'}), 500
    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        return jsonify({'error': '获取拆解失败，请重试'}), 500

@app.route('/decompose_result')
def decompose_result():
    if 'interpretation' not in session or 'colors' not in session:
        return redirect(url_for('index'))
    return render_template(
        'decompose_result.html',
        original_char=session['original_char'],
        decomposition=session['decomposition'],
        interpretation=session['interpretation'],
        colors=session['colors']
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 