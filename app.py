import discord
import csv
import sqlite3
import os
import time
from helpers import send_email, get_control_server_id

from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

check_channel_id = 1417565908695646321  # Replace with your channel ID
roleid = 897543335277916200  # Replace with your role ID
is_student_role = "is_student"
Control_Server = 1417843105524088834  

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
        
    # We want to process commands, so this should be at the end.
    # await bot.process_commands(message) 

    print(f'Message from {message.author}: {message.content}')
    
    if message.content.startswith('up') and message.content[2:].isdigit():
        upid = message.content.replace("up", "").strip()
        
        # Check if the user is already verified
        c.execute("SELECT * FROM user_links WHERE discord_id = ?", (str(message.author.id),))
        if c.fetchone():
            await message.channel.send(f'You are already verified as a student, {message.author.mention}.')
            student_role = discord.utils.get(message.guild.roles, name=is_student_role)
            if student_role:
                await message.author.add_roles(student_role)
            await message.delete()
            return
        
        # Check if that up number has already been used
        c.execute("SELECT * FROM user_links WHERE upid = ?", (upid,))
        if c.fetchone():
            x = await message.channel.send(f'That UP number has already been used for verification, {message.author.mention}. If you believe this is an error, please contact an admin.')
            
            
            tosendServer = await bot.fetch_guild(Control_Server)
            if tosendServer:
                print(f"Successfully found control server: {tosendServer.name}")
                tosendChannelid = get_control_server_id(str(message.guild.id))
                tosendChannelid = await tosendServer.fetch_channel(tosendChannelid)
                #send message to control server
                if tosendChannelid:
                    await tosendChannelid.send(f'Alert: The UP number {upid} has been attempted for verification again by {message.author} (ID: {message.author.id}) in server {message.guild.name} (ID: {message.guild.id}). Please investigate for potential misuse.')
                
            await message.delete()
            return

        verifycode = str(os.urandom(5).hex())  # Generate a random 6-character hex code
        print("Generated code:", verifycode)
        print("Please check your email for the verification code.")
        c.execute("INSERT OR REPLACE INTO pending_verifications (discord_id, upid, code) VALUES (?, ?, ?)", (str(message.author.id), upid, verifycode))
        conn.commit()

        #send email to the user with the code
        email_address = f"up{upid}@myport.ac.uk"
        discord_name = str(message.author)
        discord_id = str(message.author.id)
        if await send_email(email_address, verifycode, discord_name, discord_id):
            x = await message.channel.send(f'A verification code has been sent to your email {email_address}, {message.author.mention}. Please check your email and use the !verify command followed by the code to complete the verification process. Example: !verify 77631.  **Note: It may take a few minutes for the email to arrive and please check your spam/junk folder.**')
        else:
            x = await message.channel.send(f'Failed to send verification email to, {message.author.mention}. Please contact an admin.')

        time.sleep(60)
        await x.delete()
    
    try:
        await message.delete()
    except discord.Forbidden:
        print("Failed to delete message, missing permissions.")
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
        x = await ctx.send(f'Student Verification successful! Starting Membership Verification, {ctx.author.mention}.')
        time.sleep(10)
        await x.delete()
    else:
        await ctx.send(f'Invalid verification code, {ctx.author.mention}. Please try again.')


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(TOKEN)
    
