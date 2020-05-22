import asyncio
import discord
import random
import json
import bot_token
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import requests
from PIL import Image
from io import BytesIO

client = discord.Client()
mongo = MongoClient('localhost', 27017)
db = mongo.PokeDiscordBot
profiles = db.profiles

def getName(dexId):
    if type(dexId) == list:
        namesList = []

        for i in dexId:
            r = requests.get('https://pokeapi.co/api/v2/pokemon/{}/'.format(i))
            if r.status_code == requests.codes.ok:
                r = json.loads(r.text)
                name = r['name'].capitalize()
                namesList.append(name)
            else:
                namesList.append('Error getting name')
        return namesList
    else:
        r = requests.get('https://pokeapi.co/api/v2/pokemon/{}/'.format(dexId))
        if r.status_code == requests.codes.ok:
            r = json.loads(r.text)
            name = r['name'].capitalize()
        else:
            name = 'Error getting name'
        return name

#If we're just getting images we can pass in the number straight to image files that aren't hosted by the API, see createImage() requests
def getImage(dexId):
    if type(dexId) == list:
        for x in dexId:
            r = requests.get('https://pokeapi.co/api/v2/pokemon/{}/'.format(x))
            getImageResult = []
            if r.status_code == requests.codes.ok:
                r = json.loads(r.text)
                picture = r["sprites"]["front_default"]
                getImageResult.append(picture)
            else:
                error = "Error getting data: " + str(r.status_code)
                getImageResult.append(error)
    else:
        r = requests.get('https://pokeapi.co/api/v2/pokemon/{}/'.format(dexId))
        if r.status_code == requests.codes.ok:
            r = json.loads(r.text)
            getImageResult = r["sprites"]["front_default"]
        else:
            getImageResult = "Error getting data: " + str(r.status_code)
    return getImageResult


async def joinRerolls(pokemon, message):
    pnn = getName(pokemon)
    rerolls = 2
    while True:
        await message.channel.send("""Your Pokemon are:
        1. {}
        2. {}
        3. {}
        4. {}
        5. {}
        6. {}""".format(pnn[0],pnn[1],pnn[2],pnn[3],pnn[4],pnn[5]))
        if rerolls > 0:
            await message.channel.send('Would you like to "!keep" or "!reroll <name/list number>"? You have {} rerolls left.'.format(rerolls))
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
                    msgname = msg.content.replace('!reroll ', '')
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
                        name = getName(rando)
                        pokemon[ntc] = rando
                        pnn[ntc] = name
                        rerolls -= 1
                    else:
                        await message.channel.send('Error selecting Pokemon to reroll.')
        else:
            return pokemon

#Only works for teams of 6
#Join teamPicture and createImage into 1?
#Can't await from inside the function, returning True just for some kind of error checking
def teamPicture(teamArray):
    dst = Image.new('RGBA', (576, 96), (255, 0, 0, 0))
    for i in range(6):
        dst.paste(teamArray[i], (96 * i,0))
    return dst

def createImage(pokemon):
    teamArray = []
    for i in range(6):
        r = requests.get("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{}.png".format(pokemon[i]))
        img = Image.open(BytesIO(r.content))
        teamArray.append(img)
    teamPicture(teamArray).save('data/teamPicture.png')
    return True


#Rerolling function
async def rerolls(roll, message):
    def pred(m):
        return m.author == message.author and m.channel == message.channel and (m.content == '!keep' or m.content == '!reroll')
    msg = await client.wait_for('message', timeout=180, check=pred)
    if msg.content.startswith('!reroll'):
        rando = random.randint(1,809)
        roll = getImage(rando)
        newMsg = "Here is your new pokemon: {}".format(roll)
        profiles.find_one_and_update({'discordID': msg.author.id}, {'$push': {'pokemon': rando}})
        await message.channel.send(newMsg)
    elif msg.content.startswith('!keep'):
        newMsg = "You have kept: {}".format(roll)
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
            title = 'Hello {0.author.name}'.format(message),
            description = """In order to get started, please type the !join command. Some other commands are:
    !myprofile - Shows you your Trainer profile
    !win - wip
    !reroll - wip
    !keep - wip
    !ilose - wip"""
        )
        await message.channel.send(embed=msg)

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
            pokemon = []
            for x in range(6):
                pokemon.append(random.randint(1,809))
            pokemon = await joinRerolls(pokemon, message)
            profile = {'discordID': message.author.id,
                       'user': profileName(message.author.name, message.author.discriminator),
                       'wins': 0,
                       'loss': 0,
                       'coins': 0,
                       'pokemon': pokemon}
            profiles.insert_one(profile)
            check = createImage(pokemon)
            if check == True:
                await message.channel.send(file=discord.File('data/teamPicture.png'))

    # Call User's profile using discordID
    # TO-DO
    # - Call other user's profiles outside of your own
    # - Format message, it's ugly as you right now
    # SPIKE
    # - Do we want a user's profile to persist across all discord servers? If so,
    # should we think about multiple profiles? If so, how do we handle that?
    if message.content.startswith('!myprofile'):
        profileID = profileName(message.author.name, message.author.discriminator)
        profile = profiles.find_one({"discordID": message.author.id})
        if profiles.count_documents({"user": profileID}) != 0:
            profilemsg = discord.Embed(
                #title = "Trainer "+ message.author.name,
                description = 'Total games: {}'.format(profile['wins'] + profile['loss'])
            )
            profilemsg.set_author(name='Trainer ' + message.author.name, icon_url=message.author.avatar_url)
            image = discord.File('data/teamPicture.png', filename='teamPicture.png') #Save images to <id>.png and call them back?
            profilemsg.set_image(url='attachment://teamPicture.png')
            profilemsg.add_field(name='Wins', value='{}'.format(profile['wins']))
            profilemsg.add_field(name='Losses', value='{}'.format(profile['loss']))
            profilemsg.add_field(name='Coins', value='{}'.format(profile['coins']))
            #profilemsg.set_thumbnail(url=message.author.avatar_url)


            await message.channel.send(file=image, embed=profilemsg)
            await message.channel.send("Pokemons list WIP: {}".format(profile['pokemon']))
        else:
            await message.channel.send('You have not joined yet, type "!join" first.')


    # Allow user to record their wins and losses. Increment wins by 1 and coins
    # by 40. Increment loss by 1 and coins by 20.
    # Every 2 wins means a new roll for the User. Every 3 losses means new roll.
    # TO-DO
    # - Handle duplicate rolls
    # SPIKE
    # - Some sort of validation between parties so !iwin isn't spammed? We
    # could potentially require the input to be: !iwin <user> for the sake of
    # accountability, and that could potentially not require loser to put !ilose.
    # - Should we limit to 1 battle a day? People will receive rolls far too
    # quickly otherwise.
    if message.content.startswith('!iwin'):
        updatewin = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                     {"wins": 1, "coins": 40}})
        profile = profiles.find_one({'discordID': message.author.id})
        win_msg = "Your win has been recorded. You now have {} wins!".format(profile['wins'])
        await message.channel.send(win_msg)

        if profile['wins']%2==0:
            rando = random.randint(1,809)
            roll_msg = discord.Embed(
                title = 'New Pokemon!',
                description = 'You have won 2 games! Would you like to !keep or !reroll: {}'.format(getName(rando))
            )
            roll_msg.set_image(url=getImage(rando))
            await message.channel.send(embed=roll_msg)
            await rerolls(rando, message)


    if message.content.startswith('!ilose'):
        updateloss = profiles.find_one_and_update({'discordID': message.author.id}, {"$inc":
                                                                        {"loss": 1, "coins": 20}})
        profile = profiles.find_one({'discordID': message.author.id})
        lose_msg = "Your loss has been recorded. You now have {} losses.".format(profile['loss'])
        await message.channel.send(lose_msg)
        if profile['loss']%3==0:
            rando = random.randint(1,809)
            roll_msg = discord.Embed(
                title = 'New Pokemon!',
                description = 'You have lost 3 games. Would you like to !keep or !reroll: {}'.format(getName(rando))
            )
            roll_msg.set_image(url=getImage(rando))
            await message.channel.send(embed=roll_msg)
            await rerolls(rando, message)


    #IMAGES TEST
    if message.content.startswith('!a'):
        teamArray = []
        profile = profiles.find_one({'discordID': message.author.id})
        check = createImage(profile["pokemon"])
        if check == True:
            await message.channel.send(file=discord.File('data/teamPicture.png'))


@client.event
async def on_ready():
    print(discord.__version__)
    print('Logged in as')
    print(client.user.name)
    print('------')

client.run(bot_token.bot_token)
