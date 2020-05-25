import asyncio
import src.my_bot
import discord
import random
import aiohttp

class TestName(object):
    def test_get_name():
        name = my_bot.getName(1)
        assert name == "Bulbasaur"

