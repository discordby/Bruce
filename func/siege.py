from bs4 import BeautifulSoup
import json, requests, os

from dotenv import load_dotenv
load_dotenv()

R6STATS_API_KEY = os.getenv('R6STATS_API_KEY')

def rainbow6stats(ubi_id, discordUsername):
    genericStats, seasonalStats = fetch_api_data(ubi_id)

    stats = {}
    stats['discordUsername'] = discordUsername

    try:
        # (Hopefully) get the current season
        # Should always be the first so this should work
        cs = list(seasonalStats['seasons'].keys())[0]

        GENERAL = genericStats['stats']['general']
        RANKED_QUEUE = genericStats['stats']['queue']['ranked']
        CASUAL_QUEUE = genericStats['stats']['queue']['casual']
        THIS_SEASON = seasonalStats['seasons'][cs]['regions']['emea'][0]

        stats['level'] = genericStats['progression']['level']
        stats['xp'] = genericStats['progression']['total_xp']
        stats['alphapackProbability'] = genericStats['progression']['lootbox_probability']
        stats['totalMatches'] = GENERAL['games_played']
        stats['totalPlaytime'] = GENERAL['playtime']
        stats['totalSuicides'] = GENERAL['suicides']
        stats['totalMeleeKills'] = GENERAL['melee_kills']
        stats['totalKills'] = GENERAL['kills']
        stats['totalDeaths'] = GENERAL['deaths']
        stats['totalAssists'] = GENERAL['assists']
        stats['totalDBNOs'] = GENERAL['dbnos']
        stats['totalHeadshots'] = GENERAL['headshots']
        stats['totalPenetrationKills'] = GENERAL['penetration_kills']
        stats['totalReinforcements'] = GENERAL['reinforcements_deployed']
        stats['totalGadgetsDestroyed'] = GENERAL['gadgets_destroyed']
        stats['hs'] = (GENERAL['headshots'] / GENERAL['kills']) * 100

        stats['rankedGames'] = RANKED_QUEUE['games_played']
        stats['rankedPlaytime'] = RANKED_QUEUE['playtime']
        stats['rankedKills'] = RANKED_QUEUE['kills']
        stats['rankedDeaths'] = RANKED_QUEUE['deaths']
        stats['rankedWins'] = RANKED_QUEUE['wins']
        stats['rankedLosses'] = RANKED_QUEUE['losses']

        stats['casualGames'] = CASUAL_QUEUE['games_played']
        stats['casualPlaytime'] = CASUAL_QUEUE['playtime']
        stats['casualKills'] = CASUAL_QUEUE['kills']
        stats['casualDeaths'] = CASUAL_QUEUE['deaths']
        stats['casualWins'] = CASUAL_QUEUE['wins']
        stats['casualLosses'] = CASUAL_QUEUE['losses']

        stats['ubisoftID'] = seasonalStats['ubisoft_id']
        stats['ubisoftUsername'] = seasonalStats['username']
        stats['platform'] = seasonalStats['platform']

        stats['seasonName'] = seasonalStats['seasons'][cs]['name']
        stats['currentRank'] = THIS_SEASON['rank_text']
        stats['currentMMR'] = THIS_SEASON['mmr']
        stats['currentRankImage'] = get_rank_v2(THIS_SEASON['rank_text'])
        stats['maxRank'] = THIS_SEASON['max_rank_text']
        stats['maxMMR'] = THIS_SEASON['max_mmr']
        stats['maxRankImage'] = get_rank_v2(THIS_SEASON['max_rank_text'])

        stats['nextRankMMR'] = THIS_SEASON['next_rank_mmr']
        stats['prevRankMMR'] = THIS_SEASON['prev_rank_mmr']
        stats['lastMMRchange'] = THIS_SEASON['last_match_mmr_change']

        stats['sAbandons'] = THIS_SEASON['abandons']
        stats['sKills'] = THIS_SEASON['kills']
        stats['sDeaths'] = THIS_SEASON['deaths']
        stats['sWins'] = THIS_SEASON['wins']
        stats['sLosses'] = THIS_SEASON['losses']

        return stats

    except:
        print("R6S LOOP ERROR")
        return


def get_rank_v2(rank):
    # A really obscene way to do this, BUT it was easier than to use the Firebase Storage calls every time
    rank_dict = {
        "unranked": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FUnranked.png?alt=media&token=295b2528-9813-4add-a46f-9e5c7e2a13c8",
        "copper v": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FCopper_05.png?alt=media&token=34112e43-01cd-496a-83ca-a6d2008b1c70",
        "copper iv": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FCopper_04.png?alt=media&token=4e1351b3-25bc-4176-a7a0-f513626be2d7",
        "copper iii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FCopper_03.png?alt=media&token=b6e0acf8-98d0-4acf-b991-e660ec57be36",
        "copper ii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FCopper_02.png?alt=media&token=85f9e162-5a17-45ff-bac4-b7ceb08391ff",
        "copper i": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FCopper_01.png?alt=media&token=f7bdf9c6-a82d-4ca4-a12c-b73dc1a68cd5",
        "bronze v": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FBronze_05.png?alt=media&token=46f3b6d7-22ad-478d-841f-af659a254b6e",
        "bronze iv": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FBronze_04.png?alt=media&token=ccb5e10e-4941-469d-8b2b-2c5b0d1d58bd",
        "bronze iii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FBronze_03.png?alt=media&token=fa0aa632-b533-44d7-aefc-57a5a1aad708",
        "bronze ii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FBronze_02.png?alt=media&token=70f6b0c8-307a-4bfb-9f83-c1e98e9748d9",
        "bronze i": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FBronze_01.png?alt=media&token=a4ef33bb-cebe-49f9-a712-9b0e28af1a14",
        "silver v": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FSilver_05.png?alt=media&token=85011248-cf4e-4799-bee9-eb758375de7c",
        "silver iv": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FSilver_04.png?alt=media&token=454fe077-5a6e-4c9f-887e-c789265374a9",
        "silver iii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FSilver_03.png?alt=media&token=9e50ead1-cf08-4f55-a99c-da9160f8f171",
        "silver ii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FSilver_02.png?alt=media&token=8fd1e6df-67a1-4abd-820a-b5da03cc2e23",
        "silver i": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FSilver_01.png?alt=media&token=4331a891-e150-4b18-b940-50667ec27185",
        "gold iv": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FGOLD_04.png?alt=media&token=bae67b53-35f3-4f81-a019-a7a69fe82f67",
        "gold iii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FGOLD_03.png?alt=media&token=9a489888-23ac-4290-97fc-59276dc34044",
        "gold ii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FGOLD_02.png?alt=media&token=615b0a9f-39c6-4db2-a97e-13fa5b0bf8c1",
        "gold i": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FGOLD_01.png?alt=media&token=3661b9e6-99d8-4742-a913-9788ac94c810",
        "platinum iii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FPlatinum_03.png?alt=media&token=e5944dea-8df2-4b33-a6e7-b07800bd870b",
        "platinum ii": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FPlatinum_02.png?alt=media&token=9a09a0f4-2d66-4092-8e26-3d4528c315a4",
        "platinum i": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FPlatinum_01.png?alt=media&token=00086d17-f099-4c00-a2e8-530392d70ce9",
        "diamond": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FDiamond_01.png?alt=media&token=b64afb2e-4739-4d07-b0d5-41fb74a22b21",
        "champion": "https://firebasestorage.googleapis.com/v0/b/chuckwalla-69.appspot.com/o/R6%20Ranks%2FChampions_01.png?alt=media&token=aefcce88-98cf-48e3-ac76-7acfa2af30c4"
    }
    return rank_dict.get(rank.lower())


def ubi_id_to_name(ubi_id):
    response = requests.get(f"https://r6.tracker.network/profile/id/{ubi_id}")
    soup = BeautifulSoup(response.content, 'html.parser')
    name = soup.find("h1", {"class", "trn-profile-header__name"})
    return name.find("span").get_text()


def fetch_api_data(ubi_id):
    """
    auth header: 'Authorization: Bearer API_KEY_HERE'

    stats endpoint: https://api2.r6stats.com/public-api/stats/<username>/<platform>/<type>
    <username> = username
    <platform> = pc / xbox? / psn?
    <type> = generic / seasonal / operators / weapon-categories / weapons

    leaderboard endpoint: https://api2.r6stats.com/public-api/leaderboard/<platform>/<region>
    <platform> = pc / xbox? / psn?
    <region> = ncsa / emea / apac / all (defaults to 'all')
    """
    ubi_username = ubi_id_to_name(ubi_id)
    headers = {"Authorization": f"Bearer {R6STATS_API_KEY}"}

    generic_end = f"https://api2.r6stats.com/public-api/stats/{ubi_username}/pc/generic"
    generic_req = requests.get(generic_end, headers=headers)
    generic_stats = generic_req.json()
    seasonalEnd = f"https://api2.r6stats.com/public-api/stats/{ubi_username}/pc/seasonal"
    seasonalREQ = requests.get(seasonalEnd, headers=headers)
    seasonalStats = seasonalREQ.json()

    return generic_stats, seasonalStats
