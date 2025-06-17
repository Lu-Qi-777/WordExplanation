import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///word_explanations.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 硅基API配置
    API_KEY = os.getenv('API_KEY')
    API_URL = os.getenv('API_URL')
    
    # 色系配置
    COLOR_SCHEMES = {
        "柔和粉彩系": ["#E8A4A4", "#F5D5D5", "#F8E8E8", "#F9F5F6"],  # 柔和的粉色系
        "深邃宝石系": ["#6B4F4F", "#967E76", "#D7C0AE", "#EEE3CB"],  # 温暖的棕色系
        "清新自然系": ["#7D9F90", "#A7BEA9", "#D4D4D4", "#F5F5F5"],  # 柔和的绿色系
        "高雅灰度系": ["#4A4A4A", "#6B6B6B", "#9B9B9B", "#F5F5F5"],  # 优雅的灰色系
        "复古怀旧系": ["#8B7355", "#A67B5B", "#C4A484", "#F5F5F5"],  # 温暖的棕色系
        "明亮活力系": ["#FF8B8B", "#FFB4B4", "#FFD4D4", "#FFF5F5"],  # 柔和的红色系
        "冷淡极简系": ["#7C9A92", "#A8C3BC", "#D4E4E0", "#F5F5F5"],  # 清新的蓝绿色系
        "海洋湖泊系": ["#7B9EA8", "#A3C1D6", "#D4E4E0", "#F5F5F5"],  # 柔和的蓝色系
        "秋季丰收系": ["#B87E5C", "#D4A373", "#E6CCB2", "#F5F5F5"],  # 温暖的橙色系
        "莫兰迪色系": ["#A5A5A5", "#C4C4C4", "#E0E0E0", "#F5F5F5"]   # 柔和的灰色系
    } 