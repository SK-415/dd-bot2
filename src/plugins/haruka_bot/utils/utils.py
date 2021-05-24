import os
from pathlib import Path

import nonebot
from nonebot import require
from nonebot.adapters.cqhttp import Bot, Event, MessageEvent
from nonebot.adapters.cqhttp.exception import ActionFailed, NetworkError
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.exception import FinishedException
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.rule import Rule

from .. import config

# 更换 Chromium 下载地址为非 https 淘宝源
os.environ['PYPPETEER_DOWNLOAD_HOST'] = 'http://npm.taobao.org/mirrors'
# os.environ['PYPPETEER_DOWNLOAD_HOST'] = 'http://storage.googleapis.com'
from pyppeteer.chromium_downloader import check_chromium, download_chromium

# 检查 Chromium 是否下载
if not check_chromium():
    download_chromium()


def get_path(*other):
    """获取数据文件绝对路径"""
    if config.haruka_dir:
        dir_path = Path(config.haruka_dir).absolute()
    else:
        dir_path = Path.cwd().joinpath('data')
        # dir_path = Path.cwd().joinpath('data', 'haruka_bot')
    return str(dir_path.joinpath(*other))


async def permission_check(bot: Bot, event: MessageEvent, state: dict):
    from ..database import DB as Config
    if event.message_type == 'private':
        return
    group_id = str(event.group_id)
    with Config() as config:
        if config.get_admin(group_id):
            if not await (GROUP_ADMIN | GROUP_OWNER | SUPERUSER)(bot, event):
                await bot.send(event, '权限不足，目前只有管理员才能使用')
                raise FinishedException


def to_me():
    if config.haruka_to_me:
        from nonebot.rule import to_me
        return to_me()
    async def _to_me(bot: Bot, event: Event, state: dict):
        return True
    return Rule(_to_me)


async def safe_send(bot_id, send_type, type_id, message):
    """发送出现错误时, 尝试重新发送, 并捕获异常且不会中断运行"""
    
    try:
        bot = nonebot.get_bots()[bot_id]
    except KeyError:
        logger.error(f"推送失败，Bot ID：{bot_id} 未连接")
        return

    try:
        return await bot.call_api('send_'+send_type+'_msg', **{
        'message': message,
        'user_id' if send_type == 'private' else 'group_id': type_id
        })
    except ActionFailed as e:
        logger.error(f"推送失败（操作失败），错误信息：{e.info}")
    except NetworkError as e:
        logger.error(f"推送失败（网络错误），错误信息：{e.msg}")


scheduler = require('nonebot_plugin_apscheduler').scheduler


# bot 启动时检查 src\data\haruka_bot\ 目录是否存在
if not Path(get_path()).is_dir():
    Path(get_path()).mkdir(parents=True)