from discord.ext import commands
import pyrebase, json, os

from dotenv import load_dotenv
load_dotenv()

## Firebase Database ##
firebase_config = {"apiKey": "AIzaSyAr88_37tciNauGiRs73B_PrKGydwG_d1U","authDomain": "alert-result-315817.firebaseapp.com",
  "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app","storageBucket": "alert-result-315817.appspot.com",
  "serviceAccount": json.loads(os.getenv("serviceAccountKeyJSON"))}
db = pyrebase.initialize_app(firebase_config).database()

## Commands ##
class OnUserUpdate(commands.Cog):
    def __init__(self, client):
        """
        On User Update Event.
        Updates users username and avatar url in the database
        whenever they change anything about their account
        """
        self.client = client


    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        data = {
        "username": str(after),
        "avatar_url":str(after.avatar_url_as(size=4096))
        }
        db.child('users').child(after.id).update(data)


def setup(client):
    client.add_cog(OnUserUpdate(client))
