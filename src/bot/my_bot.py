import asyncio
import discord
import random
import json
try:
    import bot_token
except:
    tokenVar = 0
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import aiohttp
from PIL import Image
from io import BytesIO

client = discord.Client()
mongo = MongoClient('localhost', 27017)
db = mongo.PokeDiscordBot
profiles = db.profiles
pokedex = db.pokedex
try:
    tokenVar = bot_token.bot_token
except:
    print("Travis workaround")

async def getName(dexId):
    if type(dexId) == list:
        namesList = []
        for i in dexId:
            pokemonDoc = pokedex.find_one({"id": i})
            name = pokemonDoc['name'].capitalize()
            namesList.append(name)
        return namesList
    else:
        pokemonDoc = pokedex.find_one({"id": dexId})
        name = pokemonDoc['name'].capitalize()
    return name

#Only works with pokedex id's for now
async def getTier(dexId):
    if type(dexId) == list:
        tierList = []
        for i in dexId:
            pokemonDoc = pokedex.find_one({"id": i})
            tier = pokemonDoc['tier']
            tierList.append(tier)
        return tierList

#If we're just getting images we can pass in the number straight to image files that aren't hosted by the API, see createImage() requests
async def getImage(dexId):
    async with aiohttp.ClientSession() as session:

        if type(dexId) == list:
            for i in dexId:
                async with session.get(f'https://pokeapi.co/api/v2/pokemon/{i}/') as r:
                    getImageResult = []
                    if r.status == 200:
                        r = await r.json()
                        picture = r["sprites"]["front_default"]
                        getImageResult.append(picture)
                    else:
                        error = "Error getting data: " + str(r.status)
                        getImageResult.append(error)
        else:
            async with session.get(f'https://pokeapi.co/api/v2/pokemon/{dexId}/') as r:
                if r.status == 200:
                    r = await r.json()
                    getImageResult = r["sprites"]["front_default"]
                else:
                    getImageResult = "Error getting data: " + str(r.status)

    return getImageResult


async def joinRerolls(pokemon, message):
    pnn = await getName(pokemon)
    rerolls = 2
    while True:
        await message.channel.send(f"""Your Pokemon are:
        1. {pnn[0]}
        2. {pnn[1]}
        3. {pnn[2]}
        4. {pnn[3]}
        5. {pnn[4]}
        6. {pnn[5]}""")
        if rerolls > 0:
            await message.channel.send(f'Would you like to "!keep" or "!reroll <name/list number>"? You have {rerolls} rerolls left.')
            def pred(m):
                return m.author == message.author and m.channel == message.channel and (m.content.startswith('!keep') or m.content.startswith('!reroll'))
            try:
                msg = await client.wait_for('message', timeout=180, check=pred)
            except asyncio.TimeoutError:
                return pokemon
            else:
                if msg.content == '!keep':
                    return pokemon
                else:
                    msgname = msg.content.replace('!reroll ', '').strip()
                    ntclist = [name.lower() for name in pnn]

                    if msgname.isnumeric() == True:
                        ntc = int(msgname) - 1
                    else:
                        try:
                            ntc = ntclist.index(msgname)
                        except Exception as e:
                            ntc = -1

                    if ntc >= 0 and ntc <= 5:
                        rando = random.randint(1,809)
                        while random.randint(1,809) in pokemon == True:
                            rando = random.randint(1,809)
                        name = await getName(rando)
                        pokemon[ntc] = rando
                        pnn[ntc] = name
                        rerolls -= 1
                    else:
                        await message.channel.send('Error selecting Pokemon to reroll.')
        else:
            return pokemon

#Only works for teams of 6
#Can't await from inside the function, returning True just for some kind of error checking // Not true anymore, but still have to change
async def createImage(pokemon):
    teamArray = []
    async with aiohttp.ClientSession() as session:
        for i in pokemon:
            async with session.get(f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{i}.png') as r:
                if r.status == 200:
                    r = await r.read()
                    img = Image.open(BytesIO(r))
                    teamArray.append(img)
                else:
                    teamArray.append('Error')

    dst = Image.new('RGBA', (576, 96), (255, 0, 0, 0))
    for i in range(6):
        dst.paste(teamArray[i], (96 * i,0))
    dst.save('data/teamPicture.png')
    return True


#Rerolling function
async def rerolls(roll, message, currentPokemon, user):
    def pred(m):
        return m.author.id == user and m.channel == message.channel and (m.content == '!keep' or m.content == '!reroll')
    msg = await client.wait_for('message', timeout=180, check=pred)
    if msg.content.startswith('!reroll'):
        rando = random.randint(1,809)
        while rando in currentPokemon == True:
            rando = random.randint(1,809)
        roll = await getImage(rando)
        newMsg = f"Here is your new pokemon: {roll}"
        profiles.find_one_and_update({'discordID': msg.author.id}, {'$push': {'pokemon': rando}})
        await message.channel.send(newMsg)
    elif msg.content.startswith('!keep'):
        newMsg = f"You have kept: {roll}"
        profiles.find_one_and_update({'discordID': msg.author.id}, {'$push': {'pokemon': roll}})
        await message.channel.send(newMsg)


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
        msg = discord.Embed(
            title = f'Hello {message.author.name}',
            description = """In order to get started, please type the !join command. Some other commands are:
    !myprofile - Display your trainer profile.
    !win - Update your win count.
    !ilose - Update your loss count."""
        )
        await message.channel.send(embed=msg)

    # !join command. Init User object, generate list of 6 pokemon, and send message to user
    # containing Pokemon. If User has already joined, throw error.
    if message.content.startswith('!join'):
        profileID = profileName(message.author.name, message.author.discriminator)
        if profiles.count_documents({"user": profileID}) != 0:
            msg = "You have already joined! To view your profile, type !myprofile"
            await message.channel.send(msg)
        else:
            pokemon = random.sample(range(1,809), 6)
            pokemon = await joinRerolls(pokemon, message)
            profile = {'discordID': message.author.id,
                       'user': profileName(message.author.name, message.author.discriminator),
                       'wins': 0,
                       'loss': 0,
                       'coins': 0,
                       'pokemon': pokemon}
            profiles.insert_one(profile)
            check = await createImage(pokemon)
            if check == True:
                await message.channel.send(file=discord.File('data/teamPicture.png'))

    # Call User's profile using discordID
    if message.content.startswith('!myprofile'):
        profileID = profileName(message.author.name, message.author.discriminator)
        profile = profiles.find_one({"discordID": message.author.id})
        if profiles.count_documents({"user": profileID}) != 0:
            profilemsg = discord.Embed(
                #title = "Trainer "+ message.author.name,
                description = f'Total games: {profile["wins"] + profile["loss"]}'
            )
            profilemsg.set_author(name='Trainer ' + message.author.name, icon_url=message.author.avatar_url)
            image = discord.File('data/teamPicture.png', filename='teamPicture.png') #Save images to <id>.png and call them back?
            profilemsg.set_image(url='attachment://teamPicture.png')
            profilemsg.add_field(name='Wins', value=f'{profile["wins"]}')
            profilemsg.add_field(name='Losses', value=f'{profile["loss"]}')
            profilemsg.add_field(name='Coins', value=f'{profile["coins"]}')
            #profilemsg.set_thumbnail(url=message.author.avatar_url)

            pokemonNames = await getName(profile['pokemon'])
            pokemonTiers = await getTier(profile['pokemon'])

            origString = ""
            for i in range(len(pokemonNames)):
                origString += "**" + pokemonNames[i] + "**, Tier: " + pokemonTiers[i] + "\n"

            await message.channel.send(file=image, embed=profilemsg)
            await message.channel.send(origString)
        else:
            await message.channel.send('You have not joined yet, type "!join" first.')

    # Allows user to claim either victory or defeat (!ibeat or !ilost) and records wins/losses for both users.
    # Increment wins by 1 and coins by 40. Increment loss by 1 and coins by 20.
    # Every 2 wins means a new roll and every 3 losses means new roll.
    if (message.content.startswith('!ibeat') or message.content.startswith('!ilost')) and message.mentions[0].id != message.author.id and len(message.mentions) == 1: 
        userCount = 0
        try: 
            mentioned = message.mentions[0].id
            eligibleUsers = [message.author.id, mentioned]
            for i, v in enumerate(eligibleUsers):
                userCount += profiles.count_documents({'discordID': v})
        except:
            err_msg = 'No user mentioned, please mention at least a single user, ex: !ibeat @<username>'
        else: 
            if userCount == 2:
                if message.content.startswith('!ibeat'):
                    updatewin = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                            {"wins": 1, "coins": 40}})
                    updateloss = profiles.find_one_and_update({'discordID': mentioned}, {"$inc":
                                                                                {"loss": 1, "coins": 20}})
                    winProfile = profiles.find_one({'discordID': message.author.id})
                    loseProfile = profiles.find_one({'discordID': mentioned})
                elif message.content.startswith('!ilost'):
                    updatewin = profiles.find_one_and_update({'discordID': mentioned}, {"$inc":
                                                                            {"wins": 1, "coins": 40}})
                    updateloss = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                                {"loss": 1, "coins": 20}})
                    winProfile = profiles.find_one({'discordID': mentioned})
                    loseProfile = profiles.find_one({'discordID': message.author.id})

                profile = profiles.find_one({'discordID': message.author.id})
                vsProfile = profiles.find_one({'discordID': mentioned})
                vs_msg = f'''<@{message.author.id}> now has {profile['wins']} wins and {profile['loss']} losses! 
<@{mentioned}> now has {vsProfile['wins']} wins and {vsProfile['loss']} losses!'''
                await message.channel.send(vs_msg)

                if winProfile['wins']%2==0:
                    rando = random.randint(1,809)
                    while rando in winProfile['pokemon'] == True:
                        rando = random.randint(1,809)
                    roll_msg = discord.Embed(
                        title = 'New Pokemon!',
                        description = f'You have won 2 games! Would you like to !keep or !reroll: {await getName(rando)}'
                    )
                    roll_msg.set_image(url=await getImage(rando))
                    await message.channel.send(embed=roll_msg)
                    await rerolls(rando, message, winProfile['pokemon'], winProfile['discordID'])
                
                if loseProfile['loss']%3==0:
                    rando = random.randint(1,809)
                    while rando in loseProfile['pokemon'] == True:
                        rando = random.randint(1,809)
                    roll_msg = discord.Embed(
                        title = 'New Pokemon!',
                        description = f'You have lost 3 games. Would you like to !keep or !reroll: {await getName(rando)}'
                    )
                    roll_msg.set_image(url=await getImage(rando))
                    await message.channel.send(embed=roll_msg)
                    await rerolls(rando, message, loseProfile['pokemon'], loseProfile['discordID'])
            else:
                err_msg = 'The user(s) mentioned do not exist or have not created a profile. Please use the !myprofile command to check if a profile exists. If not, use the !join command to create one.'
                await message.channel.send(err_msg)

    # Check for multiple mentions when using !ibeat or !ilost.
    if (message.content.startswith('!ibeat') or message.content.startswith('!ilost')) and len(message.mentions) != 1: 
        err_msg = 'Please only mention a single user at a time, ex: !ibeat @<username>'
        await message.channel.send(err_msg)

    #IMAGES TEST
    if message.content.startswith('!a'):
        teamArray = []
        profile = profiles.find_one({'discordID': message.author.id})
        check = await createImage(profile["pokemon"])
        if check == True:
            await message.channel.send(file=discord.File('data/teamPicture.png'))


@client.event
async def on_ready():
    print(discord.__version__)
    print('Logged in as')
    print(client.user.name)
    print('------')

if tokenVar != 0:
    client.run(bot_token.bot_token)
