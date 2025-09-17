import discord
import csv
import sqlite3
import os
from helpers import send_email

from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

check_channel_id = 1417565908695646321  # Replace with your channel ID
roleid = 897543335277916200  # Replace with your role ID
is_student_role = "is_student"

# Database setup
conn = sqlite3.connect('discorduserlinks.db')
c = conn.cursor()
# Table for users who are fully verified
c.execute('''CREATE TABLE IF NOT EXISTS user_links
             (discord_id TEXT PRIMARY KEY, upid TEXT)''')
# New table for users pending email verification
c.execute('''CREATE TABLE IF NOT EXISTS pending_verifications
             (discord_id TEXT PRIMARY KEY, upid TEXT, code TEXT)''')
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

        #check if the user is already verified
        c.execute("SELECT * FROM user_links WHERE discord_id = ?", (str(message.author.id),))
        if c.fetchone():
            await message.channel.send(f'You are already verified as a student. {message.author.mention}.')
            student_role = discord.utils.get(message.guild.roles, name=is_student_role)
            await message.author.add_roles(student_role)
            return
        

        
        verifycode = str(os.urandom(3).hex())  # Generate a random 6-character hex code
        print("Generated code:", verifycode)
        print("Please check your email for the verification code.")
        c.execute("INSERT OR REPLACE INTO pending_verifications (discord_id, upid, code) VALUES (?, ?, ?)", (str(message.author.id), upid, verifycode))
        conn.commit()

        #send email to the user with the code
        email_address = f"up{upid}@myport.ac.uk"
        if send_email(email_address, verifycode):
            await message.channel.send(f'A verification code has been sent to your email {email_address}, {message.author.mention}. Please check your email and use the !verify command followed by the code to complete the verification process. Example: !verify {verifycode}')
        else:
            await message.channel.send(f'Failed to send verification email to, {message.author.mention}. Please contact an admin.')
    #process commands after on_message
    await bot.process_commands(message)

@bot.command()
async def verify(ctx, code: str):
    """Verifies the user with the provided code."""
    if ctx.channel.id != check_channel_id:
        return

    c.execute("SELECT upid FROM pending_verifications WHERE discord_id = ? AND code = ?", (str(ctx.author.id), code))
    result = c.fetchone()

    if result:
        upid = result[0]
        # Move user from pending_verifications to user_links
        c.execute("INSERT OR REPLACE INTO user_links (discord_id, upid) VALUES (?, ?)", (str(ctx.author.id), upid))
        c.execute("DELETE FROM pending_verifications WHERE discord_id = ?", (str(ctx.author.id),))
        conn.commit()

        role = ctx.guild.get_role(roleid)
        student_role = discord.utils.get(ctx.guild.roles, name=is_student_role)
        await ctx.author.add_roles(role, student_role)
        await ctx.send(f'Student Verification successful! Starting Membership Verification, {ctx.author.mention}.')
    else:
        await ctx.send(f'Invalid verification code, {ctx.author.mention}. Please try again.')


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(TOKEN)
    
