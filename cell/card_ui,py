# 新建 card_ui.py 用于存放独立UI组件
import os
import time
import imgkit
from pathlib import Path
from typing import Optional, Dict, Any
from tempfile import gettempdir

class CardGenerator:
    """独立的UI生成组件"""
    
    def __init__(self, wkhtml_path: str = None, temp_dir: str = None):
        """
        初始化配置
        :param wkhtml_path: wkhtmltoimage的可执行路径
        :param temp_dir: 临时文件存储目录
        """
        # 配置临时目录
        self.temp_dir = Path(temp_dir or gettempdir()) / "link_previews"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置转换工具
        self.wkhtml_options = {
            'enable-local-file-access': None,
            'quiet': '',
            'width': '400',
            'disable-smart-width': '',
            'encoding': "UTF-8"
        }
        if wkhtml_path:
            self.config = imgkit.config(wkhtmltoimage=wkhtml_path)
        else:
            self.config = imgkit.config()

        # 定义基础样式
        self.base_style = """
        <style>
            .card {
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #f0f4ff 100%);
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border: 1px solid #e0e6ff;
                width: 380px;
            }
            .title { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
            .stats { display: flex; gap: 16px; margin: 12px 0; }
            .stat-item { display: flex; align-items: center; }
            .link { color: #00a1d6; text-decoration: none; }
            /* 更多公共样式... */
        </style>
        """

    def _generate_filename(self, prefix: str) -> Path:
        """生成临时文件名"""
        timestamp = int(time.time() * 1000)
        return self.temp_dir / f"{prefix}_{timestamp}"

    # ---------- 平台专用生成方法 ----------
    def generate_bilibili_card(self, data: Dict[str, Any]) -> Optional[Path]:
        """生成带封面的B站卡片"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            {self.base_style}
            <style>
                .cover-img {{
                    width: 100%;
                    height: auto;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    object-fit: cover;
                    max-height: 200px;
                }}
                .content-section {{
                    padding: 0 8px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <!-- 封面图 -->
                <img class="cover-img" src="{data['pic']}" 
                     onerror="this.style.display='none'" 
                     alt="视频封面">
                
                <!-- 内容区 -->
                <div class="content-section">
                    <div class="title">{self._escape_html(data['title'])}</div>
                    <div class="up-info">
                        UP主：<span style="color: #fb7299;">{data['owner']['name']}</span>
                    </div>
                    {self._build_description(data.get('description'))}
                    <div class="stats">
                        <div class="stat-item">👍 {data['stat']['like']}</div>
                        <div class="stat-item">🪙 {data['stat']['coin']}</div>
                        <div class="stat-item">❤️ {data['stat']['favorite']}</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return self._html_to_image(html_content)

    def _build_description(self, desc: Optional[str]) -> str:
        """构建描述部分"""
        if not desc or len(desc.strip()) == 0:
            return '<div class="desc" style="display:none;"></div>'
        return f'<div class="desc">📝 {self._escape_html(desc[:100])}...</div>'

    @staticmethod
    def _escape_html(text: str) -> str:
        """HTML特殊字符转义"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def generate_github_card(self, data: Dict[str, Any]) -> Optional[Path]:
        """生成GitHub仓库卡片"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>{self.base_style}</head>
        <body>
            <div class="card">
                <div class="title">📦 {data['name']}</div>
                <div class="description">📄 {data.get('description', '暂无')}</div>
                <div class="stats">
                    <div class="stat-item">⭐ {data['stargazers_count']}</div>
                    <div class="stat-item">🍴 {data['forks_count']}</div>
                </div>
                <a href="{data['html_url']}" class="link">{data['html_url']}</a>
            </div>
        </body>
        </html>
        """
        return self._html_to_image(html_content)

    # ---------- 核心转换方法 ----------
    def _html_to_image(self, html: str) -> Optional[Path]:
        """将HTML转换为图片"""
        temp_html = self._generate_filename("temp") .with_suffix(".html")
        output_png = self._generate_filename("preview").with_suffix(".png")
        
        try:
            # 写入临时文件
            temp_html.write_text(html, encoding='utf-8')
            
            # 生成图片
            imgkit.from_file(
                input=str(temp_html),
                output_path=str(output_png),
                options=self.wkhtml_options,
                config=self.config
            )
            
            return output_png if output_png.exists() else None
        except Exception as e:
            print(f"HTML转图片失败: {str(e)}")
            return None
        finally:
            # 清理临时HTML
            if temp_html.exists():
                temp_html.unlink()