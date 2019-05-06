import discord
import random
import json
import bot_token
import pymongo
from pymongo import MongoClient

client = discord.Client()
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo['PokeDiscordBot']
profiles = db.profiles
pokemon = []

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!help'):
        msg = """Hello {0.author.mention}, in order to get started, please type
the !join command. Some other commands are:
    !myprofile - Shows you your Trainer profile
    more to come""".format(message)
        await message.channel.send(msg)

    if message.content.startswith('!join'):
        profileID = str(message.author.name) + str(message.author.discriminator)
        if profiles.find_one({"user": profileID}):
            msg = "You have already joined! To view your profile, type !myprofile"
            await message.channel.send(msg)
        else:
            for x in range(6):
                pokemon.append(random.randint(1,809))
            profile = {'user': profileID, 'win': 0, 'loss': 0, 'coins': 0, 'pokemon': pokemon}
            profiles.insert_one(profile).inserted_id 
            await message.channel.send(pokemon)

    if message.content.startswith('!myprofile'):
        mypoke = data[str(message.author)]
        await message.channel.send(mypoke)

    if message.content.startswith('!iwin'):
        data[str(message.author)]['win'] += 1
        data[str(message.author)]['coins'] += 40
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)
        print(data[str(message.author)]['win'])
        win_msg = "Your win has been recorded! You now have {} wins!".format(data[str(message.author)]['win'])
        await message.channel.send(win_msg)
        if data[str(message.author)]['win']%2==0:
            roll = random.randint(1,809)
            roll_msg = "You have won 2 games! Here is your roll: {}. Would you like to !keep or !reroll?".format(roll)
            await message.channel.send(roll_msg)
            def pred(m):
                return m.author == message.author and m.channel == message.channel
            msg = await client.wait_for('message',
                                                check=pred)
            if msg.content.startswith('!reroll'):
                roll = random.randint(1,809)
                reroll_msg = "Here is your roll: {}".format(roll)
                data[str(message.author)]['pokemon'].append(roll)
                with open('data.json', 'w') as outfile:
                    json.dump(data, outfile)
                await message.channel.send(reroll_msg)
            elif msg.content.startswith('!keep'):
                keep_msg = "You have kept: {}".format(roll)
                data[str(message.author)]['pokemon'].append(roll)
                await message.channel.send(keep_msg)
                with open('data.json', 'w') as outfile:
                    json.dump(data, outfile)

    if message.content.startswith('!ilose'):
        data[str(message.author)]['loss'] += 1
        data[str(message.author)]['coins'] += 20
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)
        print(data[str(message.author)]['loss'])
        lose_msg = "Your loss has been recorded! You now have {} losses!".format(data[str(message.author)]['loss'])
        await message.channel.send(lose_msg)
        if data[str(message.author)]['loss']%3==0:
            roll = random.randint(1,809)
            roll_msg = "You have lost 3 games. Here is your roll: {}. Would you like to !keep or !reroll?".format(roll)
            await message.channel.send(roll_msg)
            def pred(m):
                return m.author == message.author and m.channel == message.channel
            msg = await client.wait_for('message',
                                                check=pred)
            if msg.content.startswith('!reroll'):
                roll = random.randint(1,809)
                reroll_msg = "Here is your roll: {}".format(roll)
                data[str(message.author)]['pokemon'].append(roll)
                with open('data.json', 'w') as outfile:
                    json.dump(data, outfile)
                await message.channel.send(reroll_msg)
            elif msg.content.startswith('!keep'):
                keep_msg = "You have kept: {}".format(roll)
                data[str(message.author)]['pokemon'].append(roll)
                await message.channel.send(keep_msg)
                with open('data.json', 'w') as outfile:
                    json.dump(data, outfile)

@client.event
async def on_ready():
    print(discord.__version__)
    print('Logged in as')
    print(client.user.name)
    print('------')
    db.list_collection_names()

client.run(bot_token.bot_token)
