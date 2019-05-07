import discord
import random
import json
import bot_token
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

client = discord.Client()
mongo = MongoClient('localhost', 27017)
db = mongo.PokeDiscordBot
profiles = db.profiles
pokemon = []

def profileName(name, discriminator):
    profileID = str(name) + str(discriminator)
    return profileID

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    # !help command
    if message.content.startswith('!help'):
        msg = """Hello {0.author.mention}, in order to get started, please type
the !join command. Some other commands are:
    !myprofile - Shows you your Trainer profile
    more to come""".format(message)
        await message.channel.send(msg)

    # !join command. Init User object, generate list of 6 pokemon, and send message to user
    # containing Pokemon. If User has already joined, throw error.
    # TO-DO
    # - Do not allow duplicate pokemon to be rolled as starting 6
    # - Allow 2 rerolls for starting 6 (requires input of which need to be rerolled)
    # - Format message, it's ugly as your mom right now
    if message.content.startswith('!join'):
        profileID = profileName(message.author.name, message.author.discriminator)
        if profiles.count_documents({"user": profileID}) != 0:
            msg = "You have already joined! To view your profile, type !myprofile"
            await message.channel.send(msg)
        else:
            for x in range(6):
                pokemon.append(random.randint(1,809))
            profile = {'discordID': message.author.id, 
                       'user': profileName(message.author.name, message.author.discriminator), 
                       'wins': 0, 
                       'loss': 0, 
                       'coins': 0, 
                       'pokemon': pokemon}
            profiles.insert_one(profile)
            await message.channel.send(pokemon)

    # Call User's profile using discordID
    # TO-DO
    # - Call other user's profiles outside of your own
    # - Format message, it's ugly as you right now
    # SPIKE
    # - Do we want a user's profile to persist across all discord servers? If so,
    # should we think about multiple profiles? If so, how do we handle that?
    if message.content.startswith('!myprofile'):
        profile = profiles.find_one({"discordID": message.author.id})
        await message.channel.send(profile)

    # Allow user to record their win. Increment wins by 1 and coins by 40.
    # Every 2 wins means a new roll for the User.
    # TECH DEBT ALERT
    # - Win message gets sent before win is incremented (HIGH PRIO)
    # TO-DO
    # - Handle duplicate rolls
    # SPIKE
    # - Some sort of validation between parties so !iwin isn't spammed? We
    # could potentially require the input to be: !iwin <user> for the sake of
    # accountability
    # - Should we limit to 1 battle a day? People will receive rolls far too
    # quickly otherwise
    if message.content.startswith('!iwin'):
        profile = profiles.find_one({'discordID': message.author.id})
        updatewin = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                     {"wins": 1, "coins": 40}})
        win_msg = "Your win has been recorded."
        await message.channel.send(win_msg)
        if profile['wins']%2==0:
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
                profiles.find_one_and_update({'discordID': message.author.id}, {'$push': {'pokemon': roll}})
                await message.channel.send(reroll_msg)
            elif msg.content.startswith('!keep'):
                keep_msg = "You have kept: {}".format(roll)
                profiles.find_one_and_update({'discordID': message.author.id}, {'$push': {'pokemon': roll}})
                await message.channel.send(keep_msg)

    # Everything below here has not been converted to go through MongoDB.
    if message.content.startswith('!ilose'):
        updateloss = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                        {"loss": 1, "coins": 20}})
        lose_msg = "Your loss has been recorded."
        await message.channel.send(lose_msg)
        if profile['loss']%3==0:
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
