import yaml, discord
from discord.ext import commands

from dislash import *

## Config Load ##
config = yaml.safe_load(open('config.yml'))
bot_mod_role_id = config.get('bot_mod_role_id')
slash_guilds = config.get('slash_guilds')


class Status(commands.Cog):
    def __init__(self, client):
        """
        Status command.

        Can be used to set custom statuses
        """
        self.client = client


    @slash_commands.command(
        guild_ids=slash_guilds,
        description="Changes the bot's status message",
        options=[
            Option(
                name="activity",
                description="The activity type. Defaults to 'Playing'",
                choices=[
                    OptionChoice(name="Playing", value="playing"),
                    OptionChoice(name="Watching", value="watching"),
                    OptionChoice(name="Listening", value="listening"),
                ]
            ),
            Option(
                name="message",
                description="The status message. Leave empty to remove status"
            )
        ]
    )
    @slash_commands.has_role(bot_mod_role_id)
    async def status(self, ctx, activity=None, message=None):
        if activity == "playing":
            act = discord.ActivityType.playing
        elif activity == "watching":import pyrebase, yaml, json, discord
from discord.ext import commands

## Config Load ##
config = yaml.safe_load(open('config.yml'))
bot_mod_role_id = config.get('bot_mod_role_id')


class Status(commands.Cog):
    def __init__(self, client):
        """
        Status command.
        Can be used to set custom statuses
        Example usage:
        (,)status watching you all -> Watching you all
        (,)status listening everything -> Listening to everything
        (,)status playing games -> Playing games
        (,)status everyone -> Playing everyone
        (,)status clear -> Clears the status
        """
        self.client = client


    @commands.command()
    @commands.has_role(bot_mod_role_id)  # Diagnostics
    async def status(self, ctx, *args):
        cl(ctx)

        # For when a clown comes along and types a blank command without arguments
        if args == ():
            await ctx.send('You have to type some arguments!')
            await ctx.message.add_reaction('❌')
            return

        # Because autocorrect is a fucking bitch
        arg0 = (args[0]).lower()

        if arg0 == 'watching':
            activity = discord.ActivityType.watching
            msg = ' '.join(map(str, args[1:]))
        elif arg0 == 'playing':
            activity = discord.ActivityType.playing
            msg = ' '.join(map(str, args[1:]))
        elif arg0 == 'listening':
            activity = discord.ActivityType.listening
            msg = ' '.join(map(str, args[1:]))
        else:
            # Defaults to playing
            activity = discord.ActivityType.playing
            msg = ' '.join(map(str, args))

        # Use the keyword 'clear' to remove the status
        if arg0 == 'clear':
            await self.client.change_presence(activity=None)
            await ctx.message.add_reaction('✅')
        # Else set the desired status
        else:
            a = discord.Activity(type=activity, name=msg)
            await self.client.change_presence(activity=a)
            await ctx.message.add_reaction('✅')


def setup(client):
    client.add_cog(Status(client))
            act = discord.ActivityType.watching
        elif activity == "listening":
            act = discord.ActivityType.listening
        else:
            act = discord.ActivityType.playing

        if message is None:
            await self.client.change_presence(activity=None)
            await ctx.create_response("Status cleared!", ephemeral=True)
        else:
            await self.client.change_presence(activity=discord.Activity(type=act, name=message))
            await ctx.create_response("Status changed!", ephemeral=True)


def setup(client):
    client.add_cog(Status(client))
