import pyrebase, yaml, json, discord, os
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

## Config Load ##
config = yaml.safe_load(open('config.yml'))
bot_mod_role_id = config.get('bot_mod_role_id')
mod_role_id = config.get('mod_role_id')

## Firebase Database ##
firebase_config = {"apiKey": "AIzaSyAr88_37tciNauGiRs73B_PrKGydwG_d1U","authDomain": "alert-result-315817.firebaseapp.com",
  "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app","storageBucket": "alert-result-315817.appspot.com",
  "serviceAccount": json.loads(os.getenv("serviceAccountKeyJSON"))}
db = pyrebase.initialize_app(firebase_config).database()


class Admin(commands.Cog):
    def __init__(self, client):
        """
        Admin commands.

        - backup_db
        - clear
        - add_reaction
        - say
        - edit
        """
        self.client = client


    @commands.command(aliases=['bdb'])
    @commands.is_owner()
    async def backup_db(self, ctx):
        dm_ch = await ctx.author.create_dm()
        with open("db_backup.json","w") as f:
            f.write(json.dumps(db.get().val(), indent=2))
        with open("db_backup.json", "rb") as f:
            await dm_ch.send(file=discord.File(f, "db_backup.json"))


    @commands.command(aliases=['mdb'])
    @commands.is_owner()
    async def manually_add_to_db(self, ctx, user: discord.User = None):
        if user is None:
            return await ctx.send('Need a user chief..')

        member = ctx.guild.get_member(user.id)

        joinedServer = int(member.joined_at.timestamp())
        joinedDiscord = int(member.created_at.timestamp())
        avatarURL = str(member.avatar_url_as(size=4096))

        # Create users individial stats
        d = {'reacc_points':0,
             'username':str(member),
             'xp':0,
             'level':0,
             'last_xp_get':joinedServer,
             'messages_count':0,
             'joined_server':joinedServer,
             'joined_discord':joinedDiscord,
             'avatar_url':avatarURL,
             'in_server':True
             }
        db.child('users').child(member.id).set(d)


    @commands.command()
    @commands.has_any_role(bot_mod_role_id, mod_role_id)
    async def clear(self, ctx, amount: int = 1):
        await ctx.channel.purge(limit=(amount+1))


    @commands.command(aliases=['add'])
    @commands.has_any_role(bot_mod_role_id, mod_role_id)
    async def add_reaction(self, ctx, e):
        ref_ch = self.client.get_channel(ctx.message.reference.channel_id)
        ref_msg = await ref_ch.fetch_message(ctx.message.reference.message_id)
        await ref_msg.add_reaction(e)
        await ctx.message.delete()


    @commands.command()
    @commands.has_any_role(bot_mod_role_id, mod_role_id)
    async def say(self, ctx, *, a):
        await ctx.send(a)
        await ctx.message.delete()


    @commands.command()
    @commands.has_any_role(bot_mod_role_id, mod_role_id)
    async def edit(self, ctx, *, a):
        ref_ch = self.client.get_channel(ctx.message.reference.channel_id)
        ref_msg = await ref_ch.fetch_message(ctx.message.reference.message_id)
        await ref_msg.edit(content=a)
        await ctx.message.delete()


def setup(client):
    client.add_cog(Admin(client))
