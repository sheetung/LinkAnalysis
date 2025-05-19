from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import re
import requests
from typing import Dict, Tuple, Optional
from pkg.platform.types import *
# from .card_ui import CardGenerator

@register(
    name="LinkAnalysis",
    description="解析哔哩哔哩、GitHub、Gitee等多种链接并展示信息",
    version="0.72",
    author="sheetung"
)
class MyPlugin(BasePlugin):
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
        # self.ui_generator = CardGenerator(
        #     wkhtml_path="data/plugins/LinkAnalysis/wkhtmltoimage",  # 可选自定义路径
        #     temp_dir="data/plugins/LinkAnalysis/temp"           # 可选自定义目录
        # )

    @handler(PersonMessageReceived)
    @handler(GroupMessageReceived)
    async def message_handler(self, ctx: EventContext):
        """消息处理入口"""
        msg = str(ctx.event.message_chain).strip()
        launcher_id = str(ctx.event.launcher_id)
        launcher_type = str(ctx.event.launcher_type)
        # 获取黑/白名单
        # 临时适配langbot4.0特性
        pipeline_data = getattr(self.ap.pipeline_cfg, 'data', None)
        if not pipeline_data:
            # add langbot 4.0 适配
            try:
                mode = ctx.event.query.pipeline_config['trigger']['access-control']['mode']
                sess_list = ctx.event.query.pipeline_config['trigger']['access-control'][mode]
            except Exception as e:
                logger.error(f"无法从 ctx 获取 access-control 设置: {e}")
                return
        else:
            mode = pipeline_data['access-control']['mode']
            sess_list = pipeline_data['access-control'][mode]

        found = False
        if (launcher_type== 'group' and 'group_*' in sess_list) \
            or (launcher_type == 'person' and 'person_*' in sess_list):
            found = True
        else:
            for sess in sess_list:
                if sess == f"{launcher_type}_{launcher_id}":
                    found = True
                    break 
        ctn = False
        if mode == 'whitelist':
            ctn = found
        else:
            ctn = not found
        if not ctn:
            # print(f'您被杀了哦')
            return
        if 'plugin' in msg:
            return
        
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

            video_data = data['data']
            stat_data = video_data['stat']  # 核心统计数据

            description = video_data.get('desc') or video_data.get('dynamic', '')
            if isinstance(description, str) and len(description) > 0:
                description = f"📝 描述：{description[:97]}..." if len(description) > 100 else f"📝 描述：{description}"
            else:
                description = None

            message_b = [
                f"🎐 标题：{video_data['title']}",
                f"😃 UP主：{video_data['owner']['name']}"
            ]
            # 添加描述（只有存在时显示）
            if description:
                message_b.append(description.replace("\n", ""))

            message_b.extend([
                f"💖 点赞：{stat_data.get('like', 0):,}  ",
                f"🪙 投币：{stat_data.get('coin', 0):,}  ",
                f"✨ 收藏：{stat_data.get('favorite', 0):,}",
                f"🌐 链接：https://www.bilibili.com/video/{video_id}"
            ])
            message_b_chain = MessageChain([Plain(text="\n".join(message_b))])
            message_b_chain.insert(0,Image(url=video_data['pic']))

            # 生成UI
            # card_data = {
            #     "title": video_data['title'],
            #     "owner": video_data['owner'],
            #     "stat": stat_data,
            #     "description": description
            # }
            # if (img_path := self.ui_generator.generate_bilibili_card(card_data)):
            #     # 发送图片
            #     chainUI = MessageChain([Image(path=str(img_path))])
            #     chainUI.append(Plain(f"🌐 链接：https://www.bilibili.com/video/{video_id}"))
            #     await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), chainUI)
            #     # 清理图片文件
            #     img_path.unlink()
            #     return
            # else:
            #     # 回退到文本
            #     await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), MessageChain([Plain(f"视频解析失败")]))
            await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), message_b_chain)
        except Exception as e:
            await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), MessageChain([Plain(f"视频解析失败")]))
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
            message_git = [
                "━" * 3,
                f"📦 {platform} 仓库：{data['name']}",
                f"📄 描述：{data.get('description', '暂无')}",
                f"⭐ Stars: {data.get('stargazers_count', 0)}",
                f"🍴 Forks: {data.get('forks_count', 0)}",
                f"📌 Forks: {data.get('forks_count', 0)}",
                "━" * 3,
                f"🌐 链接：{data['html_url']}"
            ]
            await ctx.send_message(
                ctx.event.launcher_type,
                str(ctx.event.launcher_id),
                MessageChain([Plain(text="\n".join(message_git))])
            )
        except Exception as e:
            await ctx.send_message(ctx.event.launcher_type, str(ctx.event.launcher_id), MessageChain([Plain(f"仓库信息获取失败")]))

    def __del__(self):
        """清理资源"""
        pass
