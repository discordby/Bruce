import pyrebase, yaml, json, datetime, discord, os, time
from discord.ext import commands
import numpy as np

from dotenv import load_dotenv
load_dotenv()

## Firebase Database ##
firebase_config = {"apiKey": "AIzaSyAr88_37tciNauGiRs73B_PrKGydwG_d1U","authDomain": "alert-result-315817.firebaseapp.com",
  "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app","storageBucket": "alert-result-315817.appspot.com",
  "serviceAccount": json.loads(os.getenv("serviceAccountKeyJSON"))}
db = pyrebase.initialize_app(firebase_config).database()

class FirstDatabaseSetup(commands.Cog):
    def __init__(self, client):

        self.client = client


    @commands.command()
    @commands.is_owner()
    async def do_first_setup(self, ctx):
        async for member in ctx.guild.fetch_members(limit=150):
            if member.bot:
                continue

            count = 0
            joinedServer = int(member.joined_at.timestamp())
            joinedDiscord = int(member.created_at.timestamp())
            avatarURL = str(member.avatar_url_as(size=4096))

            d = {'reacc_points':0,
                 'username':str(member),
                 'xp':0,
                 'level':0,
                 'last_xp_get':joinedServer,
                 'messages_count':0,
                 'joined_server':joinedServer,
                 'joined_discord':joinedDiscord,
                 'avatar_url':avatarURL,
                 'in_server':True,
                 'money': 0,
                }
            db.child('users').child(member.id).set(d)
            count += 1

        print("DONE")
        print(f"Succesfully added {count} members into the database")
        print("You can now remove this file!")

def setup(client):
    client.add_cog(FirstDatabaseSetup(client))
