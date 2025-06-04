from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import asyncio
from io import BytesIO
from astrbot.api.message_components import Image

@register("astrbot_plugin_yunshi", "Abyss-Seeker", "发送运势获取随机二次元运势图", "1.0.0")
class YunshiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://www.hhlqilongzhu.cn/api/tu_yunshi.php"
        self.session = None
        self.rate_limit = {}  # 用户频率限制字典
        self.cooldown = 0  # 5分钟冷却时间（秒）

    async def initialize(self):
        """初始化aiohttp会话"""
        self.session = aiohttp.ClientSession()
        logger.info("运势插件初始化完成，API会话已创建")

    async def terminate(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            logger.info("API会话已关闭")

    @filter.contains("运势")
    async def handle_yunshi(self, event: AstrMessageEvent):
        """处理运势图片请求"""
        user_id = event.get_sender_id()
        current_time = asyncio.get_event_loop().time()

        # 检查频率限制
        last_request = self.rate_limit.get(user_id, 0)
        if current_time - last_request < self.cooldown:
            logger.info(f"用户 {user_id} 请求过于频繁，已忽略")
            return event.plain_result(f"运势查询过于频繁，请{self.cooldown - (current_time - last_request)}秒后再试")

        # 更新请求时间
        self.rate_limit[user_id] = current_time

        try:
            # 获取发送者信息
            user_name = event.get_sender_name()
            logger.info(f"收到来自 {user_name} 的运势请求")

            # 调用API获取图片
            async with self.session.get(self.api_url) as response:
                if response.status != 200:
                    logger.warning(f"API响应异常: HTTP {response.status}")
                    return event.plain_result("运势API暂时不可用，请稍后再试")

                # 获取图片数据
                image_data = await response.read()
                if not image_data:
                    logger.error("API返回空图片数据")
                    return event.plain_result("获取运势图片失败，请稍后再试")

                logger.info(f"成功获取运势图片（{len(image_data)}字节）")

            # 创建图片消息
            return event.message_result().file_image(BytesIO(image_data))

        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            return event.plain_result("网络连接异常，请稍后再试")

        except Exception as e:
            logger.error(f"处理运势请求时出错: {str(e)}")
            return event.plain_result("获取运势图片时发生错误，请稍后再试")