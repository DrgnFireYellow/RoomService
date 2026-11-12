from functools import wraps
import os
import asyncio
import logging

import discord
from discord.ext import commands

import maitreduck.messages as messages

intents = discord.Intents.default()

bot = commands.Bot(intents=intents,command_prefix="md!")

channels = {}

logging.basicConfig(
    level=logging.INFO
)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != None:
        if before.channel.id in channels.keys() and len(before.channel.members) == 0:
            embed = discord.Embed(description=f"I have removed your Voice Channel \"{before.channel.name}\" because everyone left.", color=discord.Color.blue())

            owner = await bot.fetch_user(channels[before.channel.id]["owner"])
            await owner.send(embed=embed)

            await before.channel.delete()
            del channels[before.channel.id]

vc_group = discord.app_commands.Group(name="vc", description="Manage temporary Voice Channels")

def require_owner(func):
    @wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        if interaction.channel.id not in channels.keys():
            await interaction.response.send_message(messages.ERROR_NOT_MANAGED)
            return

        if channels[interaction.channel.id]["owner"] != interaction.user.id:
            await interaction.response.send_message(messages.ERROR_NOT_OWNER)
            return

        return await func(interaction, *args, **kwargs)
    return wrapper

@vc_group.command(name="create", description="Creates a temporary Voice Channel")
async def create_vc(interaction):
    new_channel = await interaction.guild.create_voice_channel(f"{interaction.user.display_name}'s VC Channel")

    await new_channel.set_permissions(bot.user, view_channel=True)
    await new_channel.set_permissions(interaction.user, view_channel=True)
    await new_channel.set_permissions(interaction.guild.default_role, view_channel=False)

    bots_role = discord.utils.get(interaction.guild.roles, name="Bots") or discord.utils.get(interaction.guild.roles, name="Bot")

    if bots_role:
        await new_channel.set_permissions(bots_role, view_channel=True)

    channels[new_channel.id] = {
        "owner": interaction.user.id
    }

    embed = discord.Embed(title="I have created your Voice Channel.", description=f"{new_channel.mention}", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@vc_group.command(name="open", description="Opens your current Voice Channel to the entire server")
@require_owner
async def open_channel(interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=True)
    await interaction.response.send_message("I have opened your Voice Channel to the server.")

@vc_group.command(name="rename", description="Renames your current Voice Channel")
@require_owner
async def rename_channel(interaction, new_name: str):
    await interaction.channel.edit(name=new_name)
    await interaction.response.send_message("I have renamed your Voice Channel.")

@vc_group.command(name="invite", description="Invites a user to your current Voice Channel")
@require_owner
async def invite_user(interaction, user: discord.User):
    await interaction.channel.set_permissions(user, view_channel=True)

    invitation_embed = discord.Embed(title=f"{interaction.user.display_name} has requested that you join their Voice Channel.", description=f"I have delivered this invitation to join {interaction.channel.mention} in \"{interaction.guild.name}\"", color=discord.Color.blue())

    try:
        await user.send(embed=invitation_embed)
    except discord.errors.Forbidden:
        await interaction.channel.send(f"{user.mention}, {interaction.user.display_name} has requested that you join this Voice Channel.")

    await interaction.response.send_message(f"I have delivered your invitation to {user.display_name}.")

@vc_group.command(name="kick", description="Blocks someone from accessing your current Voice Channel.")
@require_owner
async def kick_user(interaction, user: discord.Member):
    await interaction.channel.set_permissions(user, view_channel=False)
    await user.move_to(None)
    await interaction.response.send_message(f"I have removed {user.display_name} from your Voice Channel.")

bot.tree.add_command(vc_group)

async def start():
    async with bot:
        try:
            await bot.start(os.environ.get("BOT_TOKEN"))
        except asyncio.CancelledError:
            print("Shutting down bot...")
        finally:
            for channel in channels.keys():
                await bot.get_channel(channel).delete()
            await bot.close()

def main():
    asyncio.run(start())

if __name__ == "__main__":
    main()