import discord
import csv
import sqlite3
import os

from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

check_channel_id = 1417565908695646321  # Replace with your channel ID
roleid = 897543335277916200  # Replace with your role ID

# Database setup
conn = sqlite3.connect('discorduserlinks.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS user_links
             (discord_id TEXT PRIMARY KEY, upid TEXT)''')
conn.commit()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id != check_channel_id:
        return

    print(f'Message from {message.author}: {message.content}')
    #a message in the form of upxxxxxxxxx where x is a digit is expected check if the number can be found in the csv file called members.csv
    if message.content.startswith('up')  and message.content[2:].isdigit():
        upid = message.content.replace("up", "").strip()
        with open('members.csv', 'r') as f:
            reader = csv.reader(f)
            found = False
            for row in reader:
                if row and row[0] == upid:
                    found = True
                    break
        if found:
            #insert if not there else post a error message
            c.execute("INSERT OR IGNORE INTO user_links (discord_id, upid) VALUES (?, ?)", (str(message.author.id), upid))
            conn.commit()
            print("User linked:", message.author.id, upid)
            if c.rowcount == 0:
                await message.channel.send(f'You have already linked a UPID, {message.author.mention}. If you need to change it, please contact an admin.')

        else:
            await message.channel.send(f'UPID {upid} not found in records, {message.author.mention}. Please check and try again.')

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(TOKEN)
    
