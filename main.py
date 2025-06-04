import aiohttp
import asyncio
import tempfile
import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("astrbot_plugin_yunshi", "运势图片生成器", "发送'运势'获取随机二次元运势图", "1.0.0")
class YunshiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://www.hhlqilongzhu.cn/api/tu_yunshi.php"
        self.session = None
        self.rate_limits = {}  # 用户频率限制字典
        self.cooldown = 300  # 5分钟冷却时间（秒）

    async def initialize(self):
        """初始化aiohttp会话"""
        self.session = aiohttp.ClientSession()
        logger.info("运势插件初始化完成，API会话已创建")

    async def terminate(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            logger.info("API会话已关闭")

    # 使用正则表达式匹配消息内容
    @filter.regex(r".*运势.*")
    async def handle_yunshi(self, event: AstrMessageEvent):
        """处理运势图片请求"""
        user_id = event.get_sender_id()
        current_time = asyncio.get_event_loop().time()

        # 检查频率限制
        last_request = self.rate_limits.get(user_id, 0)
        if current_time - last_request < self.cooldown:
            logger.info(f"用户 {user_id} 请求过于频繁，已忽略")
            return  # 不回复，或者可以发送提示消息

        # 更新请求时间
        self.rate_limits[user_id] = current_time

        # 创建临时文件
        temp_file = None
        try:
            # 获取发送者信息
            user_name = event.get_sender_name()
            logger.info(f"收到来自 {user_name} 的运势请求")

            # 调用API获取图片
            async with self.session.get(self.api_url) as response:
                if response.status != 200:
                    logger.warning(f"API响应异常: HTTP {response.status}")
                    yield event.plain_result("运势API暂时不可用，请稍后再试")
                    return

                # 读取图片数据
                image_data = await response.read()
                if not image_data:
                    logger.error("API返回空图片数据")
                    yield event.plain_result("获取运势图片失败，请稍后再试")
                    return

                logger.info(f"成功获取运势图片（{len(image_data)}字节）")

                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(image_data)
                    temp_file = tmp.name
                logger.info(f"临时图片文件保存至: {temp_file}")

            # 发送图片文件
            yield event.file_image(temp_file)

        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            yield event.plain_result("网络连接异常，请稍后再试")
        except Exception as e:
            logger.error(f"处理运势请求时出错: {str(e)}")
            yield event.plain_result("获取运势图片时发生错误，请稍后再试")
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.info(f"已删除临时文件: {temp_file}")
                except Exception as e:
                    logger.error(f"删除临时文件失败: {str(e)}")