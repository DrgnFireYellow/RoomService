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
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
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


@bot.tree.command(name="create", description="Creates a temporary Voice Channel")
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

@bot.tree.command(name="rename", description="Renames your current Voice Channel")
async def rename_channel(interaction, new_name: str):
    if interaction.channel.id not in channels.keys():
        await interaction.response.send_message(messages.ERROR_NOT_MANAGED)
        return

    if channels[interaction.channel.id]["owner"] != interaction.user.id:
        await interaction.response.send_message(messages.ERROR_NOT_OWNER)
        return

    await interaction.channel.edit(name=new_name)
    await interaction.response.send_message("I have renamed your Voice Channel.")

@bot.tree.command(name="invite", description="Invites a user to your current Voice Channel")
async def invite_user(interaction, user: discord.User):
    if interaction.channel.id not in channels.keys():
        await interaction.response.send_message(messages.ERROR_NOT_MANAGED)
        return

    if channels[interaction.channel.id]["owner"] != interaction.user.id:
        await interaction.response.send_message(messages.ERROR_NOT_OWNER)
        return

    await interaction.channel.set_permissions(user, view_channel=True)

    invitation_embed = discord.Embed(title=f"{interaction.user.display_name} has requested that you join their Voice Channel.", description=f"I have delivered this invitation to join {interaction.channel.mention} in \"{interaction.guild.name}\"", color=discord.Color.blue())

    try:
        await user.send(embed=invitation_embed)
    except discord.errors.Forbidden:
        await interaction.channel.send(f"{user.mention}, {interaction.user.display_name} has requested that you join this Voice Channel.")

    await interaction.response.send_message(f"I have delivered your invitation to {user.display_name}.")

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