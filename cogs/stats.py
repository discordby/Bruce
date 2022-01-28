from func.stats import get_stat_embed

import disnake
from disnake.ext import commands

class Iccup(commands.Cog):
    def __init__(self, client):
        """Iccup data."""
        self.client = client

    @commands.slash_command(name="iccup", description="статистика")
    async def _stats(self, inter: disnake.ApplicationCommandInteraction):
      #nick: str = Param(None, desc="The text after the activity. Leave blank to clear the status.")
        embed = get_stat_embed()
        await inter.send(embed=embed)


def setup(client):
    client.add_cog(Iccup(client))
