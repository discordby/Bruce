from cgitb import text
import requests
import disnake
from bs4 import BeautifulSoup
import datetime
import os


def _get_stats() -> dict[str: str | int] | dict[str: int]:
 nickname = 'gamer'
 url = "https://iccup.com/dota/gamingprofile/"
 response = requests.get(url+nickname)
 soup = BeautifulSoup(response.text, 'lxml')
 ptss = soup.find_all('span',class_='i-pts')
 for pts in ptss:
     myptstrue = (pts.text)

 cdacs = soup.find_all('span',id='k-num')
 for cdac in cdacs:
  mykdatrue = (cdac.text)
  my_dict = {
        'one': myptstrue,
        'two': mykdatrue,
    }
 return(my_dict)



def get_stat_embed() -> disnake.Embed:
     data = _get_stats()
     #err_c = dict("errr")
     if (err_c := data.get("err", None)) is not None:
      return disnake.Embed(title="Error", description="Error", color=0xd31145)

     embed = disnake.Embed(title=f"test - 19 data", description=err_c, color=0x280a59)
     embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/8/82/SARS-CoV-2_without_background.png")
     embed.set_footer(text=f"id: {data['one']}")

     return embed


#dayss = get_stat_embed()
#days = _get_stats()
#print(days)
#print(dayss)
