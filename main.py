from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import re
import requests
from typing import Dict, Tuple, Optional

# -------------------------- 插件核心逻辑 --------------------------
@register(
    name="LinkAnalysis",
    description="解析哔哩哔哩、GitHub、Gitee等多种链接并展示信息",
    version="0.7",
    author="sheetung"
)
class LinkMasterPlugin(BasePlugin):
    def __init__(self, host: APIHost):
        """初始化时注册所有支持的链接类型"""
        self.link_handlers = {
            "bilibili": {
                "patterns": [
                    r"www\.bilibili\.com/video/(BV\w+)",  # 标准链接
                    r"b23\.tv/(BV\w+)",                  # 短链接
                    r"www\.bilibili\.com/video/av(\d+)"  # 旧版av号
                ],
                "handler": self.handle_bilibili
            },
            "github": {
                "patterns": [r"github\.com/([^/]+)/([^/?#]+)"],  # 用户/仓库
                "handler": self.handle_github
            },
            "gitee": {
                "patterns": [r"gitee\.com/([^/]+)/([^/?#]+)"],  # 用户/仓库
                "handler": self.handle_gitee
            }
        }

    @handler(PersonMessageReceived, GroupMessageReceived)
    async def message_handler(self, ctx: EventContext):
        """消息处理入口"""
        msg = str(ctx.event.message_chain).strip()
        for platform in self.link_handlers.values():  # 遍历所有支持平台
            match = self._match_link(msg, platform["patterns"])
            if match:
                await platform["handler"](ctx, match)
                ctx.prevent_default()
                ctx.prevent_postorder()
                return  # 匹配成功后立即退出

    def _match_link(self, msg: str, patterns: list) -> Optional[re.Match]:
        """同一平台匹配多个正则"""
        for pattern in patterns:
            if match := re.search(pattern, msg):
                return match
        return None

    # -------------------------- 各平台处理逻辑 --------------------------
    async def handle_bilibili(self, ctx: EventContext, match: re.Match):
        """B站视频解析逻辑"""
        id_type = "BV" if "BV" in match.group(0) else "av"
        video_id = match.group(1)  # 从正则捕获组提取ID

        # 调用B站API获取信息
        api_url = (
            f"https://api.bilibili.com/x/web-interface/view?bvid={video_id}" 
            if id_type == "BV" else 
            f"https://api.bilibili.com/x/web-interface/view?aid={video_id}"
        )

        try:
            resp = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
            data = resp.json()
            if data["code"] != 0:
                raise ValueError("Bilibili API error")

            info = data["data"]
            await ctx.send_message(
                ctx.event.launcher_type,
                str(ctx.event.launcher_id),
                MessageChain([
                    Image(url=info["pic"]),
                    f"📺 标题：{info['title']}\n",
                    f"👤 UP主：{info['owner']['name']}\n",
                    f"🔗 链接：https://www.bilibili.com/video/{id_type}{video_id}"
                ])
            )
        except Exception as e:
            await ctx.send_message("视频解析失败")

    async def handle_github(self, ctx: EventContext, match: re.Match):
        """GitHub仓库解析逻辑"""
        await self._handle_git_repo(ctx, match.groups(), "GitHub",
            api_template="https://api.github.com/repos/{owner}/{repo}")

    async def handle_gitee(self, ctx: EventContext, match: re.Match):
        """Gitee仓库解析逻辑"""
        await self._handle_git_repo(ctx, match.groups(), "Gitee",
            api_template="https://gitee.com/api/v5/repos/{owner}/{repo}")

    async def _handle_git_repo(self, ctx: EventContext, 
                             groups: Tuple[str], 
                             platform: str,
                             api_template: str):
        """Git平台通用解析逻辑"""
        owner, repo = groups
        try:
            resp = requests.get(
                api_template.format(owner=owner, repo=repo),
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            data = resp.json()
            message = [
                f"📦 {platform} 仓库：{data['name']}",
                f"📄 描述：{data.get('description', '暂无')}",
                f"⭐ Stars: {data.get('stargazers_count', 0)}",
                f"🍴 Forks: {data.get('forks_count', 0)}",
                f"🔗 链接：{data['html_url']}"
            ]
            await ctx.send_message(
                ctx.event.launcher_type,
                str(ctx.event.launcher_id),
                MessageChain([Plain(text="\n".join(message))])
            )
        except Exception as e:
            await ctx.send_message("仓库信息获取失败")

    def __del__(self):
        """清理资源"""
        pass
