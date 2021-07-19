import discord, pyrebase, yaml, json, os
from discord.ext import commands, tasks
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

## Config Load ##
config = yaml.safe_load(open('config.yml'))
db_backup_loop_time = config.get('db_backup_loop_time')
db_auto_backup_loop = config.get('db_auto_backup_loop')

## Firebase Database ##
firebase_config = {"apiKey": "AIzaSyAr88_37tciNauGiRs73B_PrKGydwG_d1U","authDomain": "alert-result-315817.firebaseapp.com",
  "databaseURL": "https://alert-result-315817-default-rtdb.europe-west1.firebasedatabase.app","storageBucket": "alert-result-315817.appspot.com",
  "serviceAccount": json.loads(os.getenv("serviceAccountKeyJSON"))}
db = pyrebase.initialize_app(firebase_config).database()

class AutoBackupDB(commands.Cog):
    def __init__(self, client):
        """
        Automatically backs up the whole database
        and sends it to a Discord channel to rot
        """
        self.client = client
        if db_auto_backup_loop: self.dbAutoBackup.start()


    @tasks.loop(hours=db_backup_loop_time)
    async def dbAutoBackup(self):
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"dbAutoBackup_{stamp}.json"

        with open(filename,"w") as f:
            f.write(json.dumps(db.get().val(), indent=2))

        for guild in self.client.guilds:
            if guild.id == 703307518230790274:
                for channel in guild.channels:
                    if channel.id == 764488011911004210:
                        with open(filename, "rb") as f:
                            await channel.send(file=discord.File(f, filename))


def setup(client):
    client.add_cog(AutoBackupDB(client))
