from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import re
import requests
from pkg.platform.types import *

@register(name='GitAnalysis', description='解析GitHub/Gitee仓库链接并展示信息', version='0.23', author="sheetung")
class GitHubAnalysisPlugin(BasePlugin):

    def __init__(self, host: APIHost):
        pass

    @handler(PersonMessageReceived)
    @handler(GroupMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain).strip()
        
        # 匹配GitHub或Gitee仓库链接
        github_match = re.search(r'https?://github\.com/([^/]+)/([^/?#]+)', msg)
        gitee_match = re.search(r'https?://gitee\.com/([^/]+)/([^/?#]+)', msg)

        if not (github_match or gitee_match):
            return

        # 确定平台和仓库信息
        platform = "GitHub" if github_match else "Gitee"
        owner, repo = (github_match.groups() if github_match else gitee_match.groups())

        # 构造API地址
        api_url = (
            f"https://api.github.com/repos/{owner}/{repo}"
            if platform == "GitHub"
            else f"https://gitee.com/api/v5/repos/{owner}/{repo}"
        )

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'}
        
        try:
            repo_response = requests.get(api_url, headers=headers, timeout=10)
            repo_response.raise_for_status()
            repo_data = repo_response.json()
        except Exception as e:
            await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), ["仓库信息获取失败"])
            ctx.prevent_default()
            ctx.prevent_postorder()
            return

        # 提取仓库信息
        repo_name = repo_data.get('name', '未知仓库')
        repo_description = repo_data.get('description', '暂无描述') or '暂无描述'
        repo_url = repo_data.get('html_url', '')
        stars = repo_data.get('stargazers_count', 0)
        forks = repo_data.get('forks_count', 0)
        open_issues = repo_data.get('open_issues_count', 0)
        cover_url = repo_data.get('owner', {}).get('avatar_url', '')

        # 处理长描述
        if len(repo_description) > 100:
            repo_description = f"{repo_description[:97]}..."

        # 构造美观的消息格式
        message = []
        if cover_url:
            # message.append(Image(url=cover_url))
            pass
        
        info_lines = [
            "━" * 3,
            f"📦 名称：{repo_name}",
            f"📄 描述：{repo_description}",
            f"⭐ Stars：{stars}",
            f"🍴 Forks：{forks}",
            f"📌 Issues：{open_issues}",
            "━" * 3,
            f"🌐 {platform}链接：{repo_url}"
        ]
        
        message.extend([Plain(text=line + "\n") for line in info_lines])

        await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), MessageChain(message))
        ctx.prevent_default()
        ctx.prevent_postorder()

    def __del__(self):
        pass