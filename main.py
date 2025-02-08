from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import re
import requests
from pkg.platform.types import *

'''
当收到GitHub仓库链接时，对GitHub链接解析
'''
# 注册插件
@register(name='GitAnalysis', description='当收到GitHub仓库链接时，对GitHub链接解析', version='0.17', author="sheetung")
class GitHubAnalysisPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        pass

    @handler(PersonMessageReceived)
    @handler(GroupMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = str(ctx.event.message_chain).strip()
        # 如果msg含有https://github.com/字段则截取仓库信息
        github_match = re.search(r'https://github.com/([\w-]+)/([\w-]+)', msg)
        if github_match:
            owner = github_match.group(1)
            repo = github_match.group(2)
            # 发送仓库名称、描述、仓库链接、星标数、分叉数等信息
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
            }
            # 获取仓库基本信息
            repo_response = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            repo_data = repo_response.json()

            # 获取开放的 issue 数量
            issues_response = requests.get(f"https://api.github.com/repos/{owner}/{repo}/issues?state=open", headers=headers)
            open_issues = len(issues_response.json())

            if repo_response.status_code == 200:
                repo_name = repo_data['name']
                repo_description = repo_data['description'] if repo_data['description'] else "暂无描述"
                repo_url = repo_data['html_url']
                stars = repo_data['stargazers_count']
                forks = repo_data['forks_count']

                image_url = ""
                # 构建要发送的信息
                message = []
                if image_url:
                    message.append(Image(url=image_url))
                message.extend([
                    f"仓库名称：{repo_name}\n",
                    f"仓库描述：{repo_description}\n",
                    f"仓库链接：{repo_url}\n",
                    f"starts：{stars}\n",
                    f"forks ：{forks}\n",
                    f"issue ：{open_issues}\n"
                ])

                # 发送信息
                await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), MessageChain(message))
                ctx.prevent_default()
                ctx.prevent_postorder()
            else:
                await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), ["仓库信息获取失败"])
                ctx.prevent_default()
                ctx.prevent_postorder()
    
    # 插件卸载时触发
    def __del__(self):
        pass