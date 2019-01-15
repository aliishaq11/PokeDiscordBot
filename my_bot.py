import discord
import random
import json

client = discord.Client()

pokemon = []
data = {}
with open('data.json') as json_file:
    data = json.load(json_file)

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
        await client.send_message(message.channel, msg)

    if message.content.startswith('!join'):
        for x in range(6):
            pokemon.append(random.randint(1,809))
            data[str(message.author)] = {'win': 0, 'loss': 0, 'coins': 0, 'pokemon': pokemon}
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)
        await client.send_message(message.channel, pokemon)

    if message.content.startswith('!myprofile'):
        mypoke = data[str(message.author)]
        await client.send_message(message.channel, mypoke)
    
    if message.content.startswith('!iwin'):
        data[str(message.author)]['win'] += 1
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)
        print(data[str(message.author)]['win'])
        win_msg = "Your win has been recorded! You now have {} wins!".format(data[str(message.author)]['win'])
        await client.send_message(message.channel, win_msg)
        if data[str(message.author)]['win']%3:
            roll = random.randint(1,809)
            roll_msg = "You have won 3 games! Here is your roll: {}. Would you like to keep this roll or reroll?".format(roll)
            await client.send_message(message.channel, roll_msg)
#            msg = await client.wait_for_message(

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('NTMzNzU1MDAzNjM1MjM2ODY1.DxvsFQ._2QC7nqT75gwcESwPfEj0n9E3dw')
