import asyncio
import discord
import bot
import random
import aiohttp

name = "hi"
class TestName(object):
    def test_get_name(self):
        name = asyncio.get_event_loop().run_until_complete(bot.my_bot.getName(1))
        print(name)
        assert name == "Bulbasaur"
print(name)
