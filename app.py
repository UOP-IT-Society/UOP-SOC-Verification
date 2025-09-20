import discord
import sqlite3
import os
from dotenv import load_dotenv
from discord.ext import commands
from helpers import send_email, get_control_server_id, is_verification_channel

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Required intent to add roles
bot = commands.Bot(command_prefix='!', intents=intents)

# --- CONFIGURATION ---
is_student_role = "is_student"  # The name of the role to assign
Control_Server_ID = 1417843105524088834 # The ID of your central control server

# --- DATABASE SETUP ---
conn = sqlite3.connect('discorduserlinks.db')
c = conn.cursor()

# Table for users who are fully verified
c.execute('''CREATE TABLE IF NOT EXISTS user_links
             (discord_id TEXT PRIMARY KEY, upid TEXT)''')
# Table for users pending email verification
c.execute('''CREATE TABLE IF NOT EXISTS pending_verifications
             (discord_id TEXT PRIMARY KEY, upid TEXT, code TEXT)''')
conn.commit()


# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print('------')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # If the message is NOT in a verification channel, process regular commands and stop.
    if not is_verification_channel(str(message.channel.id)):
        await bot.process_commands(message)
        return

    # --- VERIFICATION LOGIC (only runs in verification channels) ---
    
    # Delete the user's message (e.g., "up123456") to keep the channel clean
    try:
        await message.delete()
    except discord.Forbidden:
        print(f"Failed to delete message in {message.channel.name}, missing permissions.")

    if message.content.startswith('up') and message.content[2:].isdigit():
        upid = message.content.replace("up", "").strip()
        
        # Check if the user is already verified
        c.execute("SELECT * FROM user_links WHERE discord_id = ?", (str(message.author.id),))
        if c.fetchone():
            await message.channel.send(f'You are already verified, {message.author.mention}.', delete_after=20)

            # check if they have the role, and if not, assign it
            try:
                student_role = discord.utils.get(message.guild.roles, name=is_student_role) 
                if student_role and student_role not in message.author.roles:
                    await message.author.add_roles(student_role)
                    print(f'Assigned role to {message.author} upon re-verification attempt.')
                elif not student_role:
                    print(f'Role "{is_student_role}" not found in guild "{message.guild.name}".')
            except discord.Forbidden:
                print(f'Failed to assign role to {message.author}, missing permissions.')
            await bot.process_commands(message)
            return
        
        # Check if that UP number has already been used
        c.execute("SELECT * FROM user_links WHERE upid = ?", (upid,))
        if c.fetchone():
            await message.channel.send(f'That UP number has already been used. If this is an error, please contact an admin.', delete_after=20)
            
            # Send an alert to the control server
            control_channel_id_str = get_control_server_id(str(message.guild.id))
            if control_channel_id_str:
                try:
                    control_server = bot.get_guild(Control_Server_ID)
                    control_channel = control_server.get_channel(int(control_channel_id_str))
                    if control_channel:
                        await control_channel.send(f'**Alert:** The UP number `{upid}` was used in a duplicate verification attempt by {message.author} (`{message.author.id}`) in server **{message.guild.name}**. Please investigate.')
                except Exception as e:
                    print(f"Could not send alert to control server: {e}")
            await bot.process_commands(message)
            return

        # Check if the user is already pending to resend the same code.
        c.execute("SELECT code FROM pending_verifications WHERE discord_id = ?", (str(message.author.id),))
        pending_user = c.fetchone()

        if pending_user:
            # User is already pending, use their existing code and update their UPID attempt
            verify_code = pending_user[0]
            c.execute("UPDATE pending_verifications SET upid = ? WHERE discord_id = ?", (upid, str(message.author.id)))
            print(f"Resending existing verification code to {message.author} ({message.author.id}).")
        else:
            # New pending user, generate a new code
            verify_code = os.urandom(3).hex() # 6-character hex code
            c.execute("INSERT INTO pending_verifications (discord_id, upid, code) VALUES (?, ?, ?)", (str(message.author.id), upid, verify_code))
            print(f"Generated new verification code for {message.author} ({message.author.id}).")
        
        conn.commit()
        # Send the verification email
        email_address = f"up{upid}@myport.ac.uk"
        if await send_email(email_address, verify_code, str(message.author), str(message.author.id)):
            await message.channel.send(
                f'{message.author.mention}, a verification code has been sent to **{email_address}**. \n'
                f'Please use `!verify <code>` to complete the process. \n'
                f'*(Check your junk/spam folder. This message will disappear in 2 minutes.)*',
                delete_after=120
            )
        else:
            await message.channel.send(f'Failed to send verification email. Please contact an admin.', delete_after=30)
    await bot.process_commands(message)
    

# Check if this account has already been verified when joining a server
@bot.event
async def on_member_join(member):
    c.execute("SELECT upid FROM user_links WHERE discord_id = ?", (str(member.id),))
    result = c.fetchone()
    if result:
        try:
            student_role = discord.utils.get(member.guild.roles, name=is_student_role) 
            if student_role:
                await member.add_roles(student_role)
                print(f'Assigned role to {member} upon joining.')
            else:
                print(f'Role "{is_student_role}" not found in guild "{member.guild.name}".')
        except discord.Forbidden:
            print(f'Failed to assign role to {member}, missing permissions.')
    

@bot.command()
async def verify(ctx, code: str):
    await ctx.message.delete()
    """Verifies the user with the provided code."""
    print(f"'{ctx.author}' initiated !verify command in channel '{ctx.channel.name}' with code '{code}'.") # DEBUG PRINT
    
    # Check if the code is valid
    c.execute("SELECT upid FROM pending_verifications WHERE discord_id = ? AND code = ?", (str(ctx.author.id), code))
    result = c.fetchone()
    print(f"Database query result for verification: {result}") # DEBUG PRINT
    if result:
        upid = result[0]
        try:
            # Add to verified users
            c.execute("INSERT OR REPLACE INTO user_links (discord_id, upid) VALUES (?, ?)", (str(ctx.author.id), upid))
            # Remove from pending verifications
            c.execute("DELETE FROM pending_verifications WHERE discord_id = ?", (str(ctx.author.id),))
            conn.commit()

            # Assign the role
            student_role = discord.utils.get(ctx.guild.roles, name=is_student_role)
            if student_role:
                await ctx.author.add_roles(student_role)
                await ctx.send(f'Congratulations {ctx.author.mention}, you have been verified and assigned the `{student_role.name}` role!', delete_after=30)
            else:
                await ctx.send(f'You have been verified, but the role `{is_student_role}` was not found. Please contact an admin.', delete_after=30)

        except sqlite3.Error as e:
            await ctx.send(f"A database error occurred: {e}", delete_after=30)
            print(f"Database error during verification: {e}")
        except discord.Forbidden:
            await ctx.send("I have verified you in the database, but I don't have permissions to assign roles.", delete_after=30)
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}", delete_after=30)
            print(f"Unexpected error during verification: {e}")
    else:
        await ctx.send(f'Invalid verification code, {ctx.author.mention}. Please check the code and try again.', delete_after=30)


@bot.command()
@commands.has_permissions(administrator=True)
async def updateverify(ctx, member: discord.Member, upid: str):
    """Manually verifies a user or updates their UP number. (Admin only)"""
    # Clean the input UPID to ensure it's just the numbers
    cleaned_upid = upid.lower().replace("up", "").strip()
    if not cleaned_upid.isdigit():
        await ctx.send("Invalid UP number format. It should be, for example, `up123456` or `123456`.", delete_after=15)
        return

    try:
        
        c.execute("DELETE FROM user_links WHERE upid = ?", (cleaned_upid,))
        c.execute("DELETE FROM pending_verifications WHERE discord_id = ?", (str(member.id),))
        c.execute("INSERT OR REPLACE INTO user_links (discord_id, upid) VALUES (?, ?)", (str(member.id), cleaned_upid))
        
        conn.commit()

        # --- Role Assignment ---
        student_role = discord.utils.get(ctx.guild.roles, name=is_student_role)
        if student_role:
            await member.add_roles(student_role)
            await ctx.send(f"Successfully verified {member.mention} with UP number `{cleaned_upid}` and assigned the `{student_role.name}` role.")
        else:
            await ctx.send(f"Successfully verified {member.mention} with UP number `{cleaned_upid}`, but the role `{is_student_role}` was not found.")

    except sqlite3.Error as e:
        await ctx.send(f"A database error occurred: {e}")
        print(f"Database error during manual verification: {e}")
    except discord.Forbidden:
        await ctx.send("I have verified the user in the database, but I don't have permissions to assign roles.")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")
        print(f"Unexpected error during manual verification: {e}")

@updateverify.error
async def updateverify_error(ctx, error):
    """Error handler for the updateverify command."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.", delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!updateverify <@member> <up_number>` (e.g., `!updateverify @JohnDoe up123456`)", delete_after=15)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"Could not find the member: `{error.argument}`.", delete_after=15)
    else:
        print(f"An error occurred with the !updateverify command: {error}")
        await ctx.send("An unexpected error occurred while running this command.", delete_after=10)


# --- RUN THE BOT ---
if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)