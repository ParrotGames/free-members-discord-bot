import discord
import requests
import json
import os
import asyncio
from discord.ext import commands
import time

print("🚀 STARTING BOT...")

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    BOT_TOKEN = config['token']
    CLIENT_ID = config['id']
    CLIENT_SECRET = config['secret']
    
    print(f"✅ Config loaded")
    print(f"🔑 Token: {BOT_TOKEN[:20]}...")
    print(f"🆔 Client ID: {CLIENT_ID}")
    print(f"🔒 Secret: {CLIENT_SECRET[:8]}...")
    
except Exception as e:
    print(f"❌ Config error: {e}")
    exit(1)

# Create bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f'🎯 Bot is ready: {bot.user}')

def refresh_access_token(refresh_token):
    """Refresh an expired access token"""
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    response = requests.post('https://discord.com/api/v10/oauth2/token', data=data)
    if response.status_code == 200:
        return response.json()
    return None

@bot.command(name='auth')
async def authenticate_user(ctx, authorization_code: str):
    """Authenticate user with code - COMPLETELY FIXED file writing"""
    try:
        authorization_code = authorization_code.strip()
        current_user_id = str(ctx.author.id)
        
        print(f"🔐 PROCESSING CODE: {authorization_code} for user {current_user_id}")
        
        msg = await ctx.send("🔄 Starting authentication...")
        
        # Token exchange
        token_data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code', 
            'code': authorization_code,
            'redirect_uri': "https://parrotgames.free.nf/discord-redirect.html"
        }
        
        await msg.edit(content="🔄 Exchanging code for token...")
        token_response = requests.post('https://discord.com/api/v10/oauth2/token', data=token_data)
        
        if token_response.status_code != 200:
            error_info = token_response.json()
            await msg.edit(content=f"❌ Token exchange failed: {error_info.get('error_description', 'Unknown error')}")
            return
        
        token_info = token_response.json()
        access_token = token_info['access_token']
        refresh_token = token_info['refresh_token']
        
        print(f"✅ Token obtained: {access_token[:20]}...")
        
        # ALWAYS use the command author's ID to avoid mismatches
        username = ctx.author.name
        
        # FIXED: Proper file handling with explicit newlines
        auth_entry = f"{current_user_id},{access_token},{refresh_token}\n"
        
        print(f"💾 Preparing to save: {auth_entry.strip()}")
        
        # Read existing entries
        existing_entries = []
        if os.path.exists('auths.txt'):
            try:
                with open('auths.txt', 'r', encoding='utf-8') as auth_file:
                    existing_entries = auth_file.readlines()
                print(f"📖 Read {len(existing_entries)} existing entries")
            except Exception as e:
                print(f"⚠️ Error reading auth file: {e}")
                existing_entries = []
        
        # Remove any existing entry for this user and clean up empty lines
        cleaned_entries = []
        for line in existing_entries:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            parts = line.split(',')
            if len(parts) >= 1 and parts[0] == current_user_id:
                print(f"🔄 Replacing old entry for user {current_user_id}")
                continue  # Skip old entry
            cleaned_entries.append(line + '\n')  # Add newline back
        
        # Add the new entry with explicit newline
        cleaned_entries.append(auth_entry)
        
        # Write back to file with proper formatting
        try:
            with open('auths.txt', 'w', encoding='utf-8') as auth_file:
                auth_file.writelines(cleaned_entries)
            print(f"✅ Successfully wrote {len(cleaned_entries)} entries to auths.txt")
        except Exception as e:
            print(f"❌ Error writing to auth file: {e}")
            await ctx.send(f"❌ Error saving authentication: {e}")
            return
        
        # Verify the file was written correctly
        try:
            with open('auths.txt', 'r', encoding='utf-8') as auth_file:
                verify_content = auth_file.read()
            print(f"🔍 Verification - File content: {repr(verify_content)}")
            print(f"🔍 Verification - Lines: {len(verify_content.splitlines())}")
        except Exception as e:
            print(f"⚠️ Could not verify file: {e}")
        
        success_embed = discord.Embed(
            title="✅ AUTHENTICATION SUCCESSFUL!",
            description=f"**{username}** is now authenticated!",
            color=0x57F287
        )
        success_embed.add_field(name="User ID", value=f"`{current_user_id}`", inline=True)
        success_embed.add_field(name="Next Step", value="You will be added to servers when admin uses `!join SERVER_ID`", inline=False)
        
        await msg.edit(content="", embed=success_embed)
        print(f"✅ Authentication completed for user {current_user_id}")
        
    except Exception as error:
        await ctx.send(f"❌ Error: {str(error)}")
        print(f"❌ Exception: {error}")

@bot.command(name='get_token')
async def get_auth_token(ctx):
    """Get authentication link"""
    redirect_url = "https://parrotgames.free.nf/discord-redirect.html"
    
    # CORRECTED SCOPES - Use space-separated string, not list
    scopes = "identify guilds.join email"
    
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': redirect_url,
        'scope': scopes,  # Use the string directly
        'prompt': 'consent'
    }
    
    # Build URL properly
    from urllib.parse import urlencode
    oauth_url = f"https://discord.com/oauth2/authorize?{urlencode(auth_params)}"
    
    embed = discord.Embed(
        title="🔐 Authentication Required",
        description="**Click the link below to get your authentication code:**",
        color=0x5865F2
    )
    embed.add_field(
        name="🚨 IMPORTANT",
        value="**Codes expire in 10 minutes!** Complete authentication quickly.",
        inline=False
    )
    embed.add_field(
        name="🔗 Auth Link", 
        value=f"[**👉 CLICK HERE TO AUTHENTICATE 👈**]({oauth_url})",
        inline=False
    )
    embed.add_field(
        name="📝 Steps:",
        value="1. Click the link above\n2. Authorize the application\n3. **IMMEDIATELY** copy the code\n4. Use `!auth YOUR_CODE_HERE`",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='invite')
async def generate_invite(ctx):
    """Generate bot invite link for any server"""
    invite_url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands"
    
    embed = discord.Embed(
        title="🤖 BOT INVITE LINK",
        description="**Use this link to add the bot to any server:**",
        color=0x5865F2
    )
    embed.add_field(
        name="🔗 Invite Link", 
        value=f"[**👉 CLICK HERE TO INVITE BOT 👈**]({invite_url})",
        inline=False
    )
    embed.add_field(
        name="📝 Steps to Join Servers:",
        value="1. Use this link to add bot to target server\n2. Use `!servers` to confirm bot is in server\n3. Use `!join SERVER_ID` to add ALL auth users",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='join')
async def join_server(ctx, target_server_id: str):
    """Add ALL authenticated users to a server - MASS JOIN"""
    try:
        # Check if bot is in the target server first
        bot_in_server = False
        server_name = "Unknown"
        
        for guild in bot.guilds:
            if str(guild.id) == target_server_id:
                bot_in_server = True
                server_name = guild.name
                break
        
        if not bot_in_server:
            invite_url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands"
            
            embed = discord.Embed(
                title="❌ BOT NOT IN SERVER",
                description=f"Bot is not in server `{target_server_id}`",
                color=0xED4245
            )
            embed.add_field(
                name="🚨 Solution", 
                value=f"**[Add bot to server first]({invite_url})**\nThen use `!join {target_server_id}` again",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        if not os.path.exists('auths.txt'):
            await ctx.send("❌ No users are authenticated yet. Use `!get_token` to share with users.")
            return
        
        # Read all authenticated users
        authenticated_users = []
        with open('auths.txt', 'r') as auth_file:
            for line_num, line in enumerate(auth_file, 1):
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) >= 3:
                    user_id = parts[0]
                    access_token = parts[1]
                    authenticated_users.append({
                        'user_id': user_id,
                        'access_token': access_token,
                        'line_number': line_num
                    })
        
        if not authenticated_users:
            await ctx.send("❌ No valid authenticated users found in auths.txt")
            return
        
        total_users = len(authenticated_users)
        await ctx.send(f"🚀 **MASS JOIN STARTED**\nAdding **{total_users}** authenticated users to **{server_name}**...")
        
        success_count = 0
        failed_count = 0
        results = []
        
        # Process each user
        for user_data in authenticated_users:
            user_id = user_data['user_id']
            access_token = user_data['access_token']
            
            try:
                api_url = f"https://discord.com/api/v10/guilds/{target_server_id}/members/{user_id}"
                join_data = {"access_token": access_token}
                headers = {
                    "Authorization": f"Bot {BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
                
                response = requests.put(api_url, headers=headers, json=join_data)
                
                if response.status_code in (201, 204):
                    success_count += 1
                    results.append(f"✅ <@{user_id}> - Added successfully")
                    print(f"✅ Added user {user_id} to server {target_server_id}")
                else:
                    failed_count += 1
                    error_msg = response.json().get('message', 'Unknown error') if response.content else 'No details'
                    results.append(f"❌ <@{user_id}> - Failed: {error_msg}")
                    print(f"❌ Failed to add user {user_id}: {response.status_code} - {error_msg}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                results.append(f"❌ <@{user_id}> - Error: {str(e)}")
                print(f"❌ Exception adding user {user_id}: {e}")
        
        # Create results embed
        embed = discord.Embed(
            title="🎯 MASS JOIN COMPLETED",
            description=f"**Server:** {server_name} (`{target_server_id}`)",
            color=0x57F287 if success_count > 0 else 0xED4245
        )
        embed.add_field(name="✅ Successful", value=str(success_count), inline=True)
        embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
        embed.add_field(name="📊 Total", value=str(total_users), inline=True)
        
        # Show first 10 results
        if results:
            results_text = "\n".join(results[:10])
            if len(results) > 10:
                results_text += f"\n\n... and {len(results) - 10} more users"
            embed.add_field(name="📋 Results (First 10)", value=results_text, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as error:
        await ctx.send(f"❌ Mass join error: {str(error)}")
        print(f"❌ MASS JOIN EXCEPTION: {error}")

@bot.command(name='list_users')
async def list_authenticated_users(ctx):
    """List all authenticated users"""
    try:
        if not os.path.exists('auths.txt'):
            await ctx.send("❌ No users are authenticated yet.")
            return
        
        users = []
        with open('auths.txt', 'r') as auth_file:
            for line_num, line in enumerate(auth_file, 1):
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) >= 3:
                    user_id = parts[0]
                    token_preview = parts[1][:10] + "..." if len(parts[1]) > 10 else parts[1]
                    users.append(f"`{line_num}.` <@{user_id}> - `{token_preview}`")
        
        if not users:
            await ctx.send("❌ No valid authenticated users found.")
            return
        
        embed = discord.Embed(
            title="📋 AUTHENTICATED USERS",
            description=f"**Total: {len(users)} users**",
            color=0x5865F2
        )
        
        # Split users into chunks to avoid field length limits
        users_text = "\n".join(users[:20])  # Show first 20 users
        if len(users) > 20:
            users_text += f"\n\n... and {len(users) - 20} more users"
        
        embed.add_field(name="Users", value=users_text, inline=False)
        embed.add_field(
            name="Usage", 
            value=f"Use `!join SERVER_ID` to add all {len(users)} users to a server", 
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as error:
        await ctx.send(f"❌ Error listing users: {str(error)}")

@bot.command(name='clear_users')
async def clear_authenticated_users(ctx):
    """Clear all authenticated users (reset)"""
    try:
        if os.path.exists('auths.txt'):
            # Count users before clearing
            user_count = 0
            with open('auths.txt', 'r') as auth_file:
                for line in auth_file:
                    if line.strip():
                        user_count += 1
            
            os.remove('auths.txt')
            await ctx.send(f"✅ Cleared **{user_count}** authenticated users. File reset.")
        else:
            await ctx.send("✅ No auth file found. Already clean.")
            
    except Exception as error:
        await ctx.send(f"❌ Error clearing users: {str(error)}")

@bot.command(name='add_user')
async def add_specific_user(ctx, target_user_id: str, target_server_id: str):
    """Add a specific user to a server"""
    try:
        # Check if bot is in the target server
        bot_in_server = False
        server_name = "Unknown"
        
        for guild in bot.guilds:
            if str(guild.id) == target_server_id:
                bot_in_server = True
                server_name = guild.name
                break
        
        if not bot_in_server:
            await ctx.send(f"❌ Bot is not in server `{target_server_id}`. Use `!invite` first.")
            return
        
        if not os.path.exists('auths.txt'):
            await ctx.send("❌ No users are authenticated yet.")
            return
        
        # Find the specific user
        user_token = None
        with open('auths.txt', 'r') as auth_file:
            for line in auth_file:
                parts = line.strip().split(',')
                if len(parts) >= 3 and parts[0] == target_user_id:
                    user_token = parts[1]
                    break
        
        if not user_token:
            await ctx.send(f"❌ User <@{target_user_id}> is not authenticated.")
            return
        
        await ctx.send(f"🚀 Adding <@{target_user_id}> to **{server_name}**...")
        
        api_url = f"https://discord.com/api/v10/guilds/{target_server_id}/members/{target_user_id}"
        join_data = {"access_token": user_token}
        headers = {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.put(api_url, headers=headers, json=join_data)
        
        if response.status_code in (201, 204):
            embed = discord.Embed(
                title="✅ USER ADDED!",
                description=f"<@{target_user_id}> has been added to **{server_name}**!",
                color=0x57F287
            )
            embed.add_field(name="Server", value=server_name, inline=True)
            embed.add_field(name="Server ID", value=f"`{target_server_id}`", inline=True)
            await ctx.send(embed=embed)
        else:
            error_info = response.json() if response.content else "No details"
            await ctx.send(f"❌ Failed to add user: {response.status_code}\nError: {error_info}")
            
    except Exception as error:
        await ctx.send(f"❌ Error adding user: {str(error)}")

# ... (keep all your other existing commands like check, count, help, debug_join, servers, etc.)

@bot.command(name='help')
async def show_help(ctx):
    """Show commands"""
    embed = discord.Embed(
        title="🤖 BOT COMMANDS - MASS JOIN SYSTEM",
        color=0x5865F2
    )
    embed.add_field(
        name="🔐 AUTHENTICATION", 
        value="`!get_token` - Get auth link to share\n`!auth CODE` - Users auth themselves\n`!check` - Check your auth status", 
        inline=False
    )
    embed.add_field(
        name="🚀 MASS SERVER JOINING", 
        value="`!join SERVER_ID` - Add ALL auth users to server\n`!add_user USER_ID SERVER_ID` - Add specific user\n`!invite` - Get bot invite link", 
        inline=False
    )
    embed.add_field(
        name="👥 USER MANAGEMENT", 
        value="`!list_users` - List all auth users\n`!clear_users` - Reset all auth users\n`!count` - Count auth users", 
        inline=False
    )
    embed.add_field(
        name="🔍 DEBUGGING", 
        value="`!servers` - List bot servers\n`!server_info` - Server details\n`!debug_join` - Debug joining", 
        inline=False
    )
    embed.add_field(
        name="📝 WORKFLOW", 
        value="1. Share `!get_token` with users\n2. Users use `!auth CODE`\n3. Use `!join SERVER_ID` to mass add", 
        inline=False
    )
    
    await ctx.send(embed=embed)

# START BOT
if __name__ == "__main__":
    print("🎯 STARTING DISCORD BOT...")
    bot.run(BOT_TOKEN)
