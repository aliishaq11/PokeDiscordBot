import asyncio
import discord
import random
from random import choice
import json
try:
    import bot_token
except:
    tokenVar = 0
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.collection import ReturnDocument
import aiohttp
from PIL import Image
from io import BytesIO

from discord.ext import tasks, commands

client = discord.Client()
mongo = MongoClient('localhost', 27017)
db = mongo.PokeDiscordBot
profiles = db.profiles
pokedex = db.pokedex

async def getName(dexId):
    if type(dexId) == list:
        namesList = []
        for i in dexId:
            pokemonDoc = pokedex.find_one({'id': i})
            name = pokemonDoc['name'].capitalize()
            namesList.append(name)
        return namesList
    else:
        pokemonDoc = pokedex.find_one({'id': dexId})
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
    else:
        pokemonDoc = pokedex.find_one({"id": dexId})
        tier = pokemonDoc['tier']
        return tier

#pokeArray has to be list of pokemon already owned by user, so as to not roll them again
async def getPokemon(pokeArray):
    randPoke = choice([i for i in range(1,891) if i not in pokeArray])
    poke = await evoUp(randPoke)

    #checks if evolution is in array
    while poke in pokeArray:
        poke = await getPokemon(pokeArray)

    #checks if pokemon is unusable
    pokemonDoc = pokedex.find_one({"id": poke})
    pokeTier = pokemonDoc['tier']
    if pokeTier == 'Illegal' or pokeTier == 'Uber':
        poke = await getPokemon(pokeArray)

    return poke

#PokeAPI does not work with gen 8
async def getImage(dexId):
    if type(dexId) == list:
        getImageResult = []
        for i in dexId:
            image = f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{i}.png'
            getImageResult.append(image)
            return getImageResult
    else:
        image = f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{dexId}.png'
        return image

async def evoUp(dexId):
    pokemonDoc = pokedex.find_one({'id': dexId})
    if len(pokemonDoc['evo']) > 1:
        pickEvo = random.randint(0, len(pokemonDoc['evo'])-1)
        pokeName = pokemonDoc['evo'][pickEvo]
        evoDoc = pokedex.find_one({'name': pokeName})
        print(pokeName)
        recurs = await evoUp(evoDoc['id'])
        return recurs
    elif len(pokemonDoc['evo']) == 1:
        pokeName = pokemonDoc['evo'][0]
        evoDoc = pokedex.find_one({'name': pokeName})
        print(pokeName)
        recurs = await evoUp(evoDoc['id'])
        return recurs
    elif len(pokemonDoc['evo']) == 0:
        return dexId

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
                        rando = await getPokemon(pokemon)
                        while rando in pokemon:
                            rando = await getPokemon(pokemon)
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
    for i in pokemon:
        img = Image.open(f'data/images/{i}.png')
        teamArray.append(img)

    dst = Image.new('RGBA', (720, 100), (255, 0, 0, 0))
    for i in range(6):
        dst.paste(teamArray[i], (120 * i,0))
    dst.save('data/teamPicture.png')
    return True

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
    !ibeat @user - Update your win count.
    !ilost @user - Update your loss count."""
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
            evolist = []
            for i in range(6):
                newPoke = await getPokemon(evolist)
                evolist.append(newPoke)
            pokemon = await joinRerolls(evolist, message)
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
        if profiles.count_documents({"discordID": message.author.id}) != 0:
            profile = profiles.find_one({"discordID": message.author.id})

            profilemsg = discord.Embed(
                description = f'Total games: {profile["wins"] + profile["loss"]}'
            )
            profilemsg.set_author(name='Trainer ' + message.author.name, icon_url=message.author.avatar_url)
            sixPokeImage = random.sample(profile['pokemon'], 6)
            await createImage(sixPokeImage)
            image = discord.File('data/teamPicture.png', filename='teamPicture.png')
            profilemsg.set_image(url='attachment://teamPicture.png')
            profilemsg.add_field(name='Wins', value=f'{profile["wins"]}')
            profilemsg.add_field(name='Losses', value=f'{profile["loss"]}')
            profilemsg.add_field(name='Coins', value=f'{profile["coins"]}')

            pokemonNames = await getName(profile['pokemon'])
            pokemonTiers = await getTier(profile['pokemon'])

            origString = ""
            for i in range(len(pokemonNames)):
                origString += f'**{pokemonNames[i]}**, Tier: {pokemonTiers[i]}\n'

            await message.channel.send(file=image, embed=profilemsg)
            await message.channel.send(origString)
        else:
            await message.channel.send('You have not joined yet, type "!join" first.')

    # Allows user to claim either victory or defeat (!ibeat or !ilost) and records wins/losses for both users.
    # Increment wins by 1 and coins by 40. Increment loss by 1 and coins by 20.
    # Every 2 wins means a new roll and every 3 losses means new roll.
    if (message.content.startswith('!ibeat') or message.content.startswith('!ilost')) and not str(message.channel).startswith('Direct '):
        # Check for multiple mentions or no mentions when using !ibeat or !ilost.
        if len(message.mentions) > 1:
            err_msg = 'Please only mention a single user at a time, ex: !ibeat @<username>'
            await message.channel.send(err_msg)
        elif len(message.mentions) == 0:
            err_msg = 'No user mentioned, please mention at least a single user, ex: !ibeat @<username>'
            await message.channel.send(err_msg)
        elif message.mentions[0].id == message.author.id:
            err_msg = 'https://www.youtube.com/watch?v=Zd9muK2M36c'
            await message.channel.send(err_msg)
        else:
            userCount = 0
            mentioned = message.mentions[0].id
            eligibleUsers = [message.author.id, mentioned]
            for i, v in enumerate(eligibleUsers):
                userCount += profiles.count_documents({'discordID': v})

            if userCount == 2:
                if message.content.startswith('!ibeat'):
                    winner = eligibleUsers[0]
                    loser = eligibleUsers[1]
                elif message.content.startswith('!ilost'):
                    winner = eligibleUsers[1]
                    loser = eligibleUsers[0]

                winProfile = profiles.find_one_and_update({'discordID': winner}, {"$inc":
                    {"wins": 1, "coins": 40}}, return_document=ReturnDocument.AFTER)
                loseProfile = profiles.find_one_and_update({'discordID': loser}, {"$inc":
                    {"loss": 1, "coins": 20}}, return_document=ReturnDocument.AFTER)
                vs_msg = (f'<@{winner}> now has {winProfile["wins"]} wins and {winProfile["loss"]} losses!\n'
                f'<@{loser}> now has {loseProfile["wins"]} wins and {loseProfile["loss"]} losses!')
                await message.channel.send(vs_msg)

                #Functions to call the messager first below
                async def winnerCheck(winProfile, message):
                    if winProfile['wins']%2==0:
                        rando = await getPokemon(winProfile['pokemon'])
                        roll_msg = discord.Embed(
                            title = 'New Pokemon!',
                            description = f'You have won 2 games! Would you like to !keep or !reroll: {await getName(rando)}'
                        )
                        roll_msg.set_image(url=await getImage(rando))
                        user = client.get_user(winProfile['discordID'])
                        await user.send(embed=roll_msg)
                        await rerolls(rando, user, winProfile['pokemon'], winProfile['discordID'])

                async def loserCheck(loseProfile, message):
                    if loseProfile['loss']%3==0:
                        rando = await getPokemon(loseProfile['pokemon'])
                        roll_msg = discord.Embed(
                            title = 'New Pokemon!',
                            description = f'You have lost 3 games. Would you like to !keep or !reroll: {await getName(rando)}'
                        )
                        roll_msg.set_image(url=await getImage(rando))
                        user = client.get_user(loseProfile['discordID'])
                        await user.send(embed=roll_msg)
                        await rerolls(rando, user, loseProfile['pokemon'], loseProfile['discordID'])

                async def rerolls(roll, message, currentPokemon, user):
                    def pred(m):
                        return m.author == message and (m.content == '!keep' or m.content == '!reroll')
                    try:
                        msg = await client.wait_for('message', timeout=600, check=pred)
                    except asyncio.TimeoutError:
                        newMsg = f"You have kept: {roll}"
                        profiles.find_one_and_update({'discordID': user}, {'$push': {'pokemon': roll}})
                        await message.channel.send(newMsg)
                    else:
                        if msg.content.startswith('!reroll'):
                            currentPokemon.append(roll)
                            rando = await getPokemon(currentPokemon)
                            roll = await getImage(rando)
                            newMsg = f"Here is your new pokemon: {roll}"
                            profiles.find_one_and_update({'discordID': msg.author.id}, {'$push': {'pokemon': rando}})
                            await message.send(newMsg)
                        elif msg.content.startswith('!keep'):
                            newMsg = f"You have kept: {roll}"
                            profiles.find_one_and_update({'discordID': msg.author.id}, {'$push': {'pokemon': roll}})
                            await message.send(newMsg)

                client.loop.create_task(winnerCheck(winProfile, message))
                client.loop.create_task(loserCheck(loseProfile, message))
            else:
                err_msg = 'The user(s) mentioned do not exist or have not created a profile. Please use the !myprofile command to check if a profile exists. If not, use the !join command to create one.'
                await message.channel.send(err_msg)

    #IMAGES TEST
    if message.content.startswith('!ppic'):
        pokes = message.content.replace('!ppic ', '').lower().strip()
        pokes = pokes.split(' ')
        print(pokes)
        profile = profiles.find_one({"discordID": message.author.id})
        if len(pokes) == 6:
            pokenums = []
            for i in pokes:
                pokemonDoc = pokedex.find_one({'name': i})
                pokenums.append(pokemonDoc['id'])
            if set(pokenums).issubset(profile['pokemon']):
                print('True')

    if message.content.startswith('!shop') or message.content.startswith('!buy'):
        items = {
        'typeegg': 120,
        'randegg': 100,
        'title': 60
        }
        if message.content.startswith('!shop'):
            shopMsg = discord.Embed(
                title = 'Poke Mart',
                description = f'Items:'
            )
            shopMsg.set_thumbnail(url='https://cdn.bulbagarden.net/upload/f/f8/Pok%C3%A9_Mart_interior_FRLG.png')
            for i in items:
                shopMsg.add_field(name=i, value=items[i], inline=False)
            await message.channel.send(embed=shopMsg)

        elif message.content.startswith('!buy'):
            profile = profiles.find_one({"discordID": message.author.id})
            boughtItem = message.content.replace('!buy ', '').lower().strip()
            if boughtItem in items:
                if profile['coins'] >= items[boughtItem]:
                    profileAfter = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                        {"coins": -items[boughtItem]}}, return_document=ReturnDocument.AFTER)

                    async def singleRoll(rando, message):
                        rollMsg = discord.Embed(
                            title = 'New Pokemon!',
                            description = f'{await getName(rando)} has hatched!'
                        )
                        rollMsg.set_image(url=await getImage(rando))
                        await message.channel.send(embed=rollMsg)

                    if boughtItem == 'randegg':
                        rando = await getPokemon(profileAfter['pokemon'])
                        profiles.find_one_and_update({'discordID': message.author.id}, {'$push': {'pokemon': rando}})
                        await singleRoll(rando, message)




@client.event
async def on_ready():
    print(discord.__version__)
    print('Logged in as')
    print(client.user.name)
    print('------')

try:
    tokenVar = bot_token.bot_token
    client.run(tokenVar)
except:
    print("No bot token found. Travis testing?")
