from func.stuff import add_spaces
from func.levels import *

import pyrebase, discord, time, yaml, json, os
from discord.ext import commands
from numpy.random import randint
from numpy.random import seed
from discord.utils import get
from numerize import numerize

## Config Load ##
config = yaml.safe_load(open('config.yml'))

## Firebase Database ##
firebase_config = {"apiKey": "AIzaSyAr88_37tciNauGiRs73B_PrKGydwG_d1U","authDomain": "alert-result-315817.firebaseapp.com",
  "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app","storageBucket": "alert-result-315817.appspot.com",
  "serviceAccount": json.loads(os.getenv("serviceAccountKeyJSON"))}
db = pyrebase.initialize_app(firebase_config).database()


class OnMessage(commands.Cog):
    def __init__(self, client):
        """
        Leveling system.
        Auto-deleting `User xyz pinned a message` messages.
        """
        self.client = client


    @commands.Cog.listener()
    async def on_message(self, message):
        # We don't want the bot giving XP to itself now do we
        if message.author.bot:
            return

        # Auto-delete "xyz has pinned a message in this channel" messages
        if message.type == discord.MessageType.pins_add:
            await message.delete()
            return

        # Don't work in DM's
        if isinstance(message.channel, discord.channel.DMChannel):
            return

        # Basic-ass variables
        now = int(time.time())
        uid = message.author.id
        level_up = False

        # Server Totals Data
        st = db.child('serverTotals').get().val()
        if st is None:
          st_levels = 0
          st_messages = 0
          st_xp = 0
        else:
          st_levels = st.get('levels', 0)
          st_messages = st.get('messages', 0)
          st_xp = st.get('xp', 0)

        # User Data
        ud = db.child('users').child(uid).get().val()
        if ud is None:
          current_lvl = 0
          current_xp = 0
          last_xp_get = 0
          messages_count = 0
          money = 0
        else:
          current_lvl = ud.get('level', 0)
          current_xp = ud.get('xp', 0)
          last_xp_get = ud.get('last_xp_get', 0)
          messages_count = ud.get('messages_count', 0)
          money = ud.get('money', 0)

        # Get the time since the user last posted a message
        since_last_mess = now - last_xp_get

        if since_last_mess > 60:

            # Calculate new XP
            seed(now)
            xp_to_add = randint(15, 25)
            new_xp = xp_to_add + current_xp

            # +100 extra XP for a message in a new day
            if since_last_mess > 86400:
                new_xp += 100

            if new_xp >= xp_from_level(current_lvl+1):
                # Level-Up
                level_up = True
                data = {'level':current_lvl+1, 'last_xp_get':now, 'xp':new_xp, 'messages_count':messages_count+1, 'money':money+xp_to_add}
                server_totals = {'xp':st_xp + xp_to_add, 'messages':st_messages+1, 'levels':st_levels+1}

                # Level based roles
                # Removes the old role and gives a new one, is applicable
                add_r = rank_name(current_lvl+1)
                del_r = rank_name(current_lvl)
                if add_r != del_r:
                    new_r = get(message.author.guild.roles, name=add_r)
                    await message.author.add_roles(new_r)
                    old_r = get(message.author.guild.roles, name=del_r)
                    await message.author.remove_roles(old_r)
            else:
                # No level change
                data = {'xp':new_xp,
                        'last_xp_get':now,
                        'messages_count':messages_count+1,
                        'money':money+xp_to_add}

                server_totals = {'xp':st_xp + xp_to_add, 'messages':st_messages+1}

        else:
            # Too Fast (less than 60s since last message)
            data = {'messages_count':messages_count+1}
            server_totals = {'messages':st_messages+1}

        # Update users individual stats & server total stats
        db.child('users').child(uid).update(data)
        db.child('serverTotals').update(server_totals)

        # Send a level up message if there was a level up
        # could be done above, but this way it's prettier i think
        if level_up:
            dm_ch = await message.author.create_dm()
            approx_messages = add_spaces(int(((xp_from_level(data['level']+1)-xp_from_level(data['level']-1))/20)))

            embed = discord.Embed(colour=discord.Colour.random())
            embed.set_author(name=message.author.name, url='https://discord.by/leader.html')
            embed.set_thumbnail(url=message.author.avatar_url)
            embed.set_footer(text=f"That's about {approx_messages} more messages")

            # Split like this because fuck long lines
            line_1 = f'Your new level is **{data["level"]}**!'
            line_2 = f'You now have **{numerize.numerize(int(data["xp"]))}** xp'

            embed.add_field(name='You have just levelled up! Congrats!',
                            value=f'{line_1}\n{line_2}',
                            inline=False)
            await dm_ch.send(embed=embed)


def setup(client):
    client.add_cog(OnMessage(client))
