import asyncio
import sys

import aiohttp
from functools import wraps




async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.google.com/'):
            pass


if __name__ == '__main__':
    if sys.version_info[:2] == (3, 7):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
