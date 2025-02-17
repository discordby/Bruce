from collections import OrderedDict

import datetime
import asyncio
import logging

from .definitions.models import OperatorInfo
from .definitions import operators, seasons

from .exceptions import InvalidRequest
from .platforms import PlatformURLNames
from .weapons import *
from .gamemodes import *
from .gamequeues import *
from .operators import *
from .ranks import *


class PlayerUrlTemplates:
    """ Private class, base API URLs """

    FETCH_STATISTIC = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/playerstats2/statistics?populations=%s&statistics=%s"
    LOAD_LEVEL = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/r6playerprofile/playerprofile/progressions?profile_ids=%s"
    LOAD_RANK = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/r6karma/players?board_id=pvp_ranked&profile_ids=%s&region_id=%s&season_id=%s"
    LOAD_CASUAL = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/r6karma/players?board_id=pvp_casual&profile_ids=%s&region_id=%s&season_id=%s"
    LOAD_OPERATOR = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/playerstats2/statistics?populations=%s&statistics=%s"
    LOAD_WEAPON = "https://public-ubiservices.ubi.com/v1/spaces/%s/sandboxes/%s/playerstats2/statistics?populations=%s&statistics=weapontypepvp_kills,weapontypepvp_headshot,weapontypepvp_bulletfired,weapontypepvp_bullethit"
    LOAD_MAPS = "https://r6s-stats.ubisoft.com/v1/current/maps/%s?gameMode=all,ranked,casual,unranked&platform=PC&teamRole=all,attacker,defender"

class PlayerUrlBuilder:
    """ Private class, creates URLs for different types of requests """

    def __init__(self, spaceid, platform_url, player_ids):
        self.spaceid = spaceid
        self.platform_url = platform_url
        self.player_ids = player_ids

        if isinstance(player_ids, list) or isinstance(player_ids, tuple):
            player_ids = ",".join(player_ids)

    def fetch_statistic_url(self, statistics):
        return PlayerUrlTemplates.FETCH_STATISTIC % (self.spaceid, self.platform_url, self.player_ids, ",".join(statistics))

    def load_level_url(self):
        return PlayerUrlTemplates.LOAD_LEVEL % (self.spaceid, self.platform_url, self.player_ids)

    def load_rank_url(self, region, season):
        return PlayerUrlTemplates.LOAD_RANK % (self.spaceid, self.platform_url, self.player_ids, region, season)

    def load_casual_url(self, region, season):
        return PlayerUrlTemplates.LOAD_CASUAL % (self.spaceid, self.platform_url, self.player_ids, region, season)

    def load_operator_url(self, statistics):
        return PlayerUrlTemplates.LOAD_OPERATOR % (self.spaceid, self.platform_url, self.player_ids, statistics)

    def load_weapon_url(self):
        return PlayerUrlTemplates.LOAD_WEAPON % (self.spaceid, self.platform_url, self.player_ids)

    def load_maps_url(self):
        return PlayerUrlTemplates.LOAD_MAPS % (self.player_ids)


class PlayerBatch:
    """ Accumulates requests for multiple players' stats in to a single request, saving time.

    Acts as a proxy for any asynchronous method in :class:`Player`. The response of the method will be a dictionary of
    the responses from each player, with the player ids as keys.

    This class is also an iterable, and iterates over the :class:`Player` objects contained in the batch.
    Individual players in the batch can be accessed via their ID using an item accessor (player_batch[player.id])

    Parameters
    ----------
    players : list[:class:`Player`]
        the list of players in the batch """

    def __init__(self, players):
        self.players = players
        self.player_ids = [player_id for player_id in players]
        self._player_objs = [players[player_id] for player_id in players]

        if len(players) == 0:
            raise ValueError("batch must contain at least one player")

    def __iter__(self):
        return iter(self._player_objs)

    def __getitem__(self, name):
        return self.players[name]

    def __getattr__(self, name):
        root_player = self.players[self.player_ids[0]]
        root_method = getattr(root_player, name)

        async def _proxy(*args, **kwargs):
            results = {}

            # temporarily override url builder so we get data for all players
            root_player.url_builder.player_ids = ",".join(self.player_ids)

            root_result = await root_method(*args, **kwargs)
            results[root_player.id] = root_result

            data = root_player._last_data
            kwargs["data"] = data

            for player_id in self.players:
                if player_id != root_player.id:
                    results[player_id] = await getattr(self.players[player_id], name)(*args, **kwargs)

            # reset root player url builder to default state
            root_player.url_builder.player_ids = root_player.id

            return results

        return _proxy


class Player:

    def __init__(self, auth, data):
        self.auth = auth

        self.id = data.get("profileId")
        self.userid = data.get("userId")
        self.platform = data.get("platformType")
        self.platform_url = PlatformURLNames[self.platform]
        self.id_on_platform = data.get("idOnPlatform")
        self.name = data.get("nameOnPlatform")
        self.url_builder = PlayerUrlBuilder(self.spaceid, self.platform_url, self.id)

        self.url = f"https://game-rainbow6.ubi.com/en-us/{self.platform}/player-statistics/{self.id}/multiplayer"
        self.icon_url = f"https://ubisoft-avatars.akamaized.net/{self.id}/default_256_256.png"

        self.ranks = {}
        self.casuals = {}
        self.operators = {}
        self.gamemodes = {}
        self.weapons = []

        self.casual = None
        self.ranked = None
        self.terrorist_hunt = None

        self._last_data = None

    @property
    def spaceid(self):
        return self.auth.spaceids[self.platform]

    async def _fetch_statistics(self, *statistics, data=None):
        if data is None:
            data = await self.auth.get(self.url_builder.fetch_statistic_url(statistics))
            self._last_data = data

        if "results" not in data or self.id not in data["results"]:
            raise InvalidRequest("Missing results key in returned JSON object %s" % str(data))

        data = data["results"][self.id]
        stats = {}

        for x in data:
            statistic = x.split(":")[0]
            if statistic in statistics:
                stats[statistic] = data[x]

        return stats

    async def load_level(self, data=None):
        """|coro|

        Load the players XP and level"""
        if data is None:
            data = await self.auth.get(self.url_builder.load_level_url())
            self._last_data = data

        if "player_profiles" in data and len(data["player_profiles"]) > 0:
            self.xp = data["player_profiles"][0].get("xp", 0)
            self.level = data["player_profiles"][0].get("level", 0)
            self.lootbox_probability = data["player_profiles"][0].get("lootbox_probability", 0)
        else:
            raise InvalidRequest("Missing key player_profiles in returned JSON object %s" % str(data))

    async def check_level(self):
        """|coro|

        Check the players XP and level, only loading it if it hasn't been loaded yet"""
        if not hasattr(self, "level"):
            await self.load_level()



    async def load_maps(self):
        xddd = {'headers':{
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36 Edg/90.0.818.51',
            'cache-control':'no-cache',
            'expiration':f'{(datetime.datetime.now()+datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z',
            'accept':'*/*',
            'Accept-Encoding':'gzip, deflate, br',
            'origin':'https://www.ubisoft.com',
            'referer':'https://www.ubisoft.com',
        }}
        data = await self.auth.get(self.url_builder.load_maps_url(), **xddd)
        return self._process_maps(data)

    def _process_map_name(self, sd):
        maps_dict = {
            'HOUSE V3': 'House',
            'BANK': 'Bank',
            'YACHT': 'Yacht',
            'OUTBACK': 'Outback',
            'HEREFORD BASE': 'Hereford Base',
            'CLUB HOUSE': 'Club House',
            'COASTLINE': 'Coastline',
            'PRESIDENTIAL PLANE': 'Presidential Plane',
            'CHALET V2': 'Chalet',
            'TOWER': 'Tower',
            'BORDER V2': 'Border',
            'FORTRESS': 'Fortress',
            'THEME PARK V2': 'Theme Park',
            'VILLA': 'Villa',
            'FAVELA': 'Favela',
            'SKYSCRAPER V2': 'Skyscraper',
            'BORDER': 'Border',
            'CONSULATE': 'Consulate',
            'OREGON': 'Oregon',
            'KANAL': 'Kanal',
            'KAFE DOSTOYEVSKY': 'Kafe Dostoyevsky'
        }
        return maps_dict.get(sd)

    def _get_map_image(self, map_name):
        links = {
            'HOUSE V3': 'https://i.imgur.com/9kOltw3.png',
            'BANK': 'https://i.imgur.com/B8W0Yiz.png',
            'YACHT': 'https://i.imgur.com/yBHfPeV.jpg',
            'OUTBACK': 'https://i.imgur.com/N4E4BpK.png',
            'HEREFORD BASE': 'https://i.imgur.com/t47T2mO.png',
            'CLUB HOUSE': 'https://i.imgur.com/7HFAkRl.png',
            'COASTLINE': 'https://i.imgur.com/ziVyTsr.png',
            'PRESIDENTIAL PLANE': 'https://i.imgur.com/h963KeO.jpg',
            'CHALET V2': 'https://i.imgur.com/DwUqw3Z.png',
            'TOWER': 'https://i.imgur.com/CD9JPkJ.png',
            'BORDER V2': 'https://i.imgur.com/AqPy3Gw.jpg',
            'BORDER': 'https://i.imgur.com/AqPy3Gw.jpg',
            'FORTRESS': 'https://i.imgur.com/J1RwhgZ.png',
            'THEME PARK V2': 'https://i.imgur.com/4UbPyVs.png',
            'VILLA': 'https://i.imgur.com/20MBjB7.png',
            'FAVELA': 'https://i.imgur.com/HofAV1W.jpg',
            'SKYSCRAPER V2': 'https://i.imgur.com/lY2Htwr.png',
            'CONSULATE': 'https://i.imgur.com/r3Xhjkf.png',
            'OREGON': 'https://i.imgur.com/d13gtbi.jpg',
            'KANAL': 'https://i.imgur.com/trkka0D.png',
            'KAFE DOSTOYEVSKY': 'https://i.imgur.com/UsUHH9b.png'
        }
        return links.get(map_name)

    def _process_gamemode(self, data):
        for role in data:
            for one_map in data[role]:
                one_map['mapName'] = self._process_map_name(one_map['statsDetail'])
                one_map['mapImage'] = self._get_map_image(one_map['statsDetail'])
                del one_map['statsDetail']
                del one_map['type']
                del one_map['statsType']
                one_map['killsPerRound'] = one_map['killsPerRound']['value']
                one_map['killDeathRatio'] = one_map['killDeathRatio']['value']
                one_map['headshotAccuracy'] = one_map['headshotAccuracy']['value']
                one_map['roundsWithAKill'] = one_map['roundsWithAKill']['value']
                one_map['roundsWithMultiKill'] = one_map['roundsWithMultiKill']['value']
                one_map['roundsWithOpeningKill'] = one_map['roundsWithOpeningKill']['value']
                one_map['roundsWithOpeningDeath'] = one_map['roundsWithOpeningDeath']['value']
                one_map['roundsWithKOST'] = one_map['roundsWithKOST']['value']
                one_map['roundsSurvived'] = one_map['roundsSurvived']['value']
                one_map['roundsWithAnAce'] = one_map['roundsWithAnAce']['value']
                one_map['roundsWithClutch'] = one_map['roundsWithClutch']['value']
        return data

    def _process_maps(self, data, xd={'all':{},'casual':{},'ranked':{},'unranked':{}}):
        if 'all' in data['platforms']['PC']['gameModes']:
            xd['all'] = self._process_gamemode(data['platforms']['PC']['gameModes']['all']['teamRoles'])
        if 'casual' in data['platforms']['PC']['gameModes']:
            xd['casual'] = self._process_gamemode(data['platforms']['PC']['gameModes']['casual']['teamRoles'])
        if 'ranked' in data['platforms']['PC']['gameModes']:
            xd['ranked'] = self._process_gamemode(data['platforms']['PC']['gameModes']['ranked']['teamRoles'])
        if 'unranked' in data['platforms']['PC']['gameModes']:
            xd['unranked'] = self._process_gamemode(data['platforms']['PC']['gameModes']['unranked']['teamRoles'])
        return xd



    async def load_casual(self, region, season=-1, data=None):
        """|coro|
        Loads the players rank for this region and season

        Parameters
        ----------
        region : str
            the name of the region you want to get the rank for (defaults to EU)
        season : Optional[int]
            the season you want to get the rank for (defaults to -1, latest season)

        Returns
        -------
        :class:`Rank`
            the players rank for this region and season"""
        if data is None:
            data = await self.auth.get(self.url_builder.load_casual_url(region, season))
            self._last_data = data

        queried_season = seasons[season]
        rank_definitions = queried_season.season_ranks

        if "players" in data and self.id in data["players"]:
            regionkey = "%s:%s" % (region, season)
            self.ranks[regionkey] = Rank(data["players"][self.id], rank_definitions)
            return self.ranks[regionkey]
        else:
            raise InvalidRequest("Missing players key in returned JSON object %s" % str(data))

    async def get_casual(self, region='EU', season=-1, data=None):
        """|coro|

        Checks the players casual rank for this region, only loading it if it hasn't already been found

        Parameters
        ----------
        region : str
            the name of the region you want to get the rank for (defaults to EU)
        season : Optional[int]
            the season you want to get the rank for (defaults to -1, latest season)

        Returns
        -------
        :class:`Rank`
            the players rank for this region and season"""
        cache_key = "%s:%s" % (region, season)
        if cache_key in self.casuals:
            return self.casuals[cache_key]

        result = await self.load_casual(region, season, data=data)
        return result

    async def load_rank(self, region, season=-1, data=None):
        """|coro|
        Loads the players rank for this region and season

        Parameters
        ----------
        region : str
            the name of the region you want to get the rank for (defaults to EU)
        season : Optional[int]
            the season you want to get the rank for (defaults to -1, latest season)

        Returns
        -------
        :class:`Rank`
            the players rank for this region and season"""
        if data is None:
            data = await self.auth.get(self.url_builder.load_rank_url(region, season))
            self._last_data = data

        queried_season = seasons[season]
        rank_definitions = queried_season.season_ranks

        if "players" in data and self.id in data["players"]:
            regionkey = "%s:%s" % (region, season)
            self.ranks[regionkey] = Rank(data["players"][self.id], rank_definitions)
            return self.ranks[regionkey]
        else:
            raise InvalidRequest("Missing players key in returned JSON object %s" % str(data))

    async def get_rank(self, region='EU', season=-1, data=None):
        """|coro|

        Checks the players rank for this region, only loading it if it hasn't already been found

        Parameters
        ----------
        region : str
            the name of the region you want to get the rank for (defaults to EU)
        season : Optional[int]
            the season you want to get the rank for (defaults to -1, latest season)

        Returns
        -------
        :class:`Rank`
            the players rank for this region and season"""
        cache_key = "%s:%s" % (region, season)
        if cache_key in self.ranks:
            return self.ranks[cache_key]

        result = await self.load_rank(region, season, data=data)
        return result

    @staticmethod
    def _process_data(data, operators_get):
        lol = {}
        for og in operators_get:
            for stat in data:
                statU = stat.replace(':infinite','')
                if statU.endswith(og.index):
                    ss = f'{og.name}_{statU[12:-4]}'
                    lol[ss] = data[stat]
        return lol

    @staticmethod
    def _process_basic_data_v2(data, oi):
        xd = {}
        for stat in data:
            if stat.startswith(oi.name):
                ss = f'{stat[len(oi.name)+1:]}'
                xd[ss] = data[stat]
        return xd

    @staticmethod
    def _process_basic_data(data, operator_info):
        """
        Filters out the basic data like kills, deaths etc that are common to all operators
        and processes them, removing the operator:infinite postfix and prefix, returning
        it as a new dictionary

        Note that the current implementation doesn't remove extraneous items
        """
        return {x.split(":")[0].split("_", maxsplit=1)[1]: data[x] for x in data if x is not None}

    @staticmethod
    def _process_unique_data(data, operator_info):
        """
        Filters out the unique attributes, based on the attributes of the operator_info passed.
        Returns them as a ordered dictionary of :class:`UniqueOperatorStat` to the value of the stat.
        The order is preserved to allow the 'main' attribute to always be inserted first and used for
        the operator's `statistic` and `statistic_name` values
        """
        unique_data = OrderedDict()
        for ability in operator_info.unique_abilities:
            # try to match each ability to the data returned from the API
            # currently hard-coded to only return PVP stats
            match = f"{ability.pvp_stat_name}:{operator_info.index}:infinite"
            if match in data:
                unique_data[ability] = data[match]
            else:
                unique_data[ability] = 0  # the stupid API just doesnt return anything if we have zero of that stat

        return unique_data

    async def load_all_operators(self, data=None):
        # ask the api for all the basic stat names WITHOUT a postfix to ask for all (I assume)
        statistics = list(OperatorUrlStatisticNames)

        # also add in all the unique
        for operator_info in operators.get_all():
            for ability in operator_info.unique_abilities:
                statistics.append(f"{ability.pvp_stat_name}:{operator_info.index}:infinite")

        statistics = ",".join(statistics)

        if data is None:
            data = await self.auth.get(self.url_builder.load_operator_url(statistics))
            self._last_data = data

        if "results" not in data or self.id not in data["results"]:
            raise InvalidRequest("Missing results key in returned JSON object %s" % str(data))

        data = data["results"][self.id]



        data = self._process_data(data, operators.get_all())



        for operator_info in operators.get_all():
            #base_data = self._process_basic_data(data, operator_info)
            unique_data = self._process_unique_data(data, operator_info)

            base_data = self._process_basic_data_v2(data, operator_info)


            self.operators[operator_info.name.lower()] = Operator(operator_info.name.lower(), base_data, unique_data)



        return self.operators

    async def get_all_operators(self, data=None):
        """|coro|

        Checks the player stats for all operators, loading them all again if any aren't found
        This is significantly more efficient than calling get_operator for every operator name.

        Returns
        -------
        dict[:class:`Operator`]
            the dictionary of all operators found"""
        if len(self.operators) >= len(OperatorStatisticNames):
            return self.operators

        result = await self.load_all_operators(data=data)
        return result

    async def load_operator(self, operator, data=None):
        """|coro|

        Loads the players stats for the operator

        Parameters
        ----------
        operator : str
            the name of the operator

        Returns
        -------
        :class:`Operator`
            the operator object found"""
        operator = operator.lower()

        # check if operator occurs in the definitions
        op = operators.from_name(operator)
        if op is None:
            raise ValueError("invalid operator %s" % operator)

        statistics = []
        for stat_name in OperatorUrlStatisticNames:
            # the statistic key is the stat name e.g. `operatorpvp_kills` + an "operator index"
            # to filter the result + ":infinite"
            # the resulting key will look something like `operatorpvp_kills:1:2:infinite`
            # where :1:2: varies depending on the operator
            statistics.append("{stat_name}:{index}:infinite".format(stat_name=stat_name, index=op.index))

        # now get the operator unique stats
        for ability in op.unique_abilities:
            statistics.append("{stat_name}:{index}:infinite".format(stat_name=ability.pvp_stat_name, index=op.index))

        if data is None:
            # join the statistic name strings to build the url
            statistics = ",".join(statistics)
            data = await self.auth.get(self.url_builder.load_operator_url(statistics))
            self._last_data = data

        if "results" not in data or self.id not in data["results"]:
            raise InvalidRequest("Missing results key in returned JSON object %s" % str(data))

        data = data["results"][self.id]

        base_data = self._process_basic_data(data)
        unique_data = self._process_unique_data(data, op)

        oper = Operator(operator, base_data, unique_data)
        self.operators[operator] = oper
        return oper

    async def get_operator(self, operator, data=None):
        """|coro|

        Checks the players stats for this operator, only loading them if they haven't already been found

        Parameters
        ----------
        operator : str
            the name of the operator

        Returns
        -------
        :class:`Operator`
            the operator object found"""
        if operator in self.operators:
            return self.operators[operator]

        result = await self.load_operator(operator, data=data)
        return result

    async def load_weapons(self, data=None):
        """|coro|

        Load the players weapon stats

        Returns
        -------
        list[:class:`Weapon`]
            list of all the weapon objects found"""
        if data is None:
            data = await self.auth.get(self.url_builder.load_weapon_url())
            self._last_data = data

        if not "results" in data or not self.id in data["results"]:
            raise InvalidRequest("Missing key results in returned JSON object %s" % str(data))

        data = data["results"][self.id]
        self.weapons = [Weapon(i, data) for i in range(7)]

        return self.weapons

    async def check_weapons(self, data=None):
        """|coro|

        Check the players weapon stats, only loading them if they haven't already been found

        Returns
        -------
        list[:class:`Weapon`]
            list of all the weapon objects found"""
        if len(self.weapons) == 0:
            await self.load_weapons(data=data)
        return self.weapons

    async def load_gamemodes(self, data=None):
        """|coro|

        Loads the players gamemode stats

        Returns
        -------
        dict
            dict of all the gamemodes found (gamemode_name: :class:`Gamemode`)"""

        stats = await self._fetch_statistics("secureareapvp_matchwon", "secureareapvp_matchlost", "secureareapvp_matchplayed",
                                                  "secureareapvp_bestscore", "rescuehostagepvp_matchwon", "rescuehostagepvp_matchlost",
                                                  "rescuehostagepvp_matchplayed", "rescuehostagepvp_bestscore", "plantbombpvp_matchwon",
                                                  "plantbombpvp_matchlost", "plantbombpvp_matchplayed", "plantbombpvp_bestscore",
                                                  "generalpvp_servershacked", "generalpvp_serverdefender", "generalpvp_serveraggression",
                                                  "generalpvp_hostagerescue", "generalpvp_hostagedefense", data=data)

        self.gamemodes = {x: Gamemode(x, stats) for x in GamemodeNames}

        return self.gamemodes

    async def check_gamemodes(self, data=None):
        """|coro|

        Checks the players gamemode stats, only loading them if they haven't already been found

        Returns
        -------
        dict
            dict of all the gamemodes found (gamemode_name: :class:`Gamemode`)"""
        if len(self.gamemodes) == 0:
            await self.load_gamemodes(data=data)
        return self.gamemodes

    async def load_general(self, data=None):
        """|coro|

        Loads the players general stats"""

        stats = await self._fetch_statistics("generalpvp_timeplayed", "generalpvp_matchplayed", "generalpvp_matchwon",
                                                  "generalpvp_matchlost", "generalpvp_kills", "generalpvp_death",
                                                  "generalpvp_bullethit", "generalpvp_bulletfired", "generalpvp_killassists",
                                                  "generalpvp_revive", "generalpvp_headshot", "generalpvp_penetrationkills",
                                                  "generalpvp_meleekills", "generalpvp_dbnoassists", "generalpvp_suicide",
                                                  "generalpvp_barricadedeployed", "generalpvp_reinforcementdeploy", "generalpvp_totalxp",
                                                  "generalpvp_rappelbreach", "generalpvp_distancetravelled", "generalpvp_revivedenied",
                                                  "generalpvp_dbno", "generalpvp_gadgetdestroy", "generalpvp_blindkills", data=data)

        statname = "generalpvp_"
        self.deaths = stats.get(statname + "death", 0)
        self.penetration_kills = stats.get(statname + "penetrationkills", 0)
        self.matches_won = stats.get(statname + "matchwon", 0)
        self.bullets_hit = stats.get(statname + "bullethit", 0)
        self.melee_kills = stats.get(statname + "meleekills", 0)
        self.bullets_fired = stats.get(statname + "bulletfired", 0)
        self.matches_played = stats.get(statname + "matchplayed", 0)
        self.kill_assists = stats.get(statname + "killassists", 0)
        self.time_played = stats.get(statname + "timeplayed", 0)
        self.revives = stats.get(statname + "revive", 0)
        self.kills = stats.get(statname + "kills", 0)
        self.headshots = stats.get(statname + "headshot", 0)
        self.matches_lost = stats.get(statname + "matchlost", 0)
        self.dbno_assists = stats.get(statname + "dbnoassists", 0)
        self.suicides = stats.get(statname + "suicide", 0)
        self.barricades_deployed = stats.get(statname + "barricadedeployed", 0)
        self.reinforcements_deployed = stats.get(statname + "reinforcementdeploy", 0)
        self.total_xp = stats.get(statname + "totalxp", 0)
        self.rappel_breaches = stats.get(statname + "rappelbreach", 0)
        self.distance_travelled = stats.get(statname + "distancetravelled", 0)
        self.revives_denied = stats.get(statname + "revivedenied", 0)
        self.dbnos = stats.get(statname + "dbno", 0)
        self.gadgets_destroyed = stats.get(statname + "gadgetdestroy", 0)
        self.blind_kills = stats.get(statname + "blindkills")

    async def check_general(self, data=None):
        """|coro|

        Checks the players general stats, only loading them if they haven't already been found"""
        if not hasattr(self, "kills"):
            await self.load_general(data=data)

    async def load_queues(self, data=None):
        """|coro|

        Loads the players game queues"""

        stats = await self._fetch_statistics("casualpvp_matchwon", "casualpvp_matchlost", "casualpvp_timeplayed",
                                                  "casualpvp_matchplayed", "casualpvp_kills", "casualpvp_death",
                                                  "rankedpvp_matchwon", "rankedpvp_matchlost", "rankedpvp_timeplayed",
                                                  "rankedpvp_matchplayed", "rankedpvp_kills", "rankedpvp_death", data=data)

        self.ranked = GameQueue("ranked", stats)
        self.casual = GameQueue("casual", stats)

    async def check_queues(self, data=None):
        """|coro|

        Checks the players game queues, only loading them if they haven't already been found"""
        if self.casual is None:
            await self.load_queues(data=data)

    async def load_terrohunt(self, data=None):
        """|coro|

        Loads the player's general stats for terrorist hunt"""
        stats = await self._fetch_statistics("generalpve_dbnoassists", "generalpve_death", "generalpve_revive",
                                                  "generalpve_matchwon", "generalpve_suicide", "generalpve_servershacked",
                                                  "generalpve_serverdefender", "generalpve_barricadedeployed", "generalpve_reinforcementdeploy",
                                                  "generalpve_kills", "generalpve_hostagedefense", "generalpve_bulletfired",
                                                  "generalpve_matchlost", "generalpve_killassists", "generalpve_totalxp",
                                                  "generalpve_hostagerescue", "generalpve_penetrationkills", "generalpve_meleekills",
                                                  "generalpve_rappelbreach", "generalpve_distancetravelled", "generalpve_matchplayed",
                                                  "generalpve_serveraggression", "generalpve_timeplayed", "generalpve_revivedenied",
                                                  "generalpve_dbno", "generalpve_bullethit", "generalpve_blindkills", "generalpve_headshot",
                                                  "generalpve_gadgetdestroy", "generalpve_accuracy", data=data)

        self.terrorist_hunt = GameQueue("terrohunt")

        statname = "generalpve_"
        self.terrorist_hunt.deaths = stats.get(statname + "death", 0)
        self.terrorist_hunt.penetration_kills = stats.get(statname + "penetrationkills", 0)
        self.terrorist_hunt.matches_won = stats.get(statname + "matchwon", 0)
        self.terrorist_hunt.bullets_hit = stats.get(statname + "bullethit", 0)
        self.terrorist_hunt.melee_kills = stats.get(statname + "meleekills", 0)
        self.terrorist_hunt.bullets_fired = stats.get(statname + "bulletfired", 0)
        self.terrorist_hunt.matches_played = stats.get(statname + "matchplayed", 0)
        self.terrorist_hunt.kill_assists = stats.get(statname + "killassists", 0)
        self.terrorist_hunt.time_played = stats.get(statname + "timeplayed", 0)
        self.terrorist_hunt.revives = stats.get(statname + "revive", 0)
        self.terrorist_hunt.kills = stats.get(statname + "kills", 0)
        self.terrorist_hunt.headshots = stats.get(statname + "headshot", 0)
        self.terrorist_hunt.matches_lost = stats.get(statname + "matchlost", 0)
        self.terrorist_hunt.dbno_assists = stats.get(statname + "dbnoassists", 0)
        self.terrorist_hunt.suicides = stats.get(statname + "suicide", 0)
        self.terrorist_hunt.barricades_deployed = stats.get(statname + "barricadedeployed", 0)
        self.terrorist_hunt.reinforcements_deployed = stats.get(statname + "reinforcementdeploy", 0)
        self.terrorist_hunt.total_xp = stats.get(statname + "totalxp", 0)
        self.terrorist_hunt.rappel_breaches = stats.get(statname + "rappelbreach", 0)
        self.terrorist_hunt.distance_travelled = stats.get(statname + "distancetravelled", 0)
        self.terrorist_hunt.revives_denied = stats.get(statname + "revivedenied", 0)
        self.terrorist_hunt.dbnos = stats.get(statname + "dbno", 0)
        self.terrorist_hunt.gadgets_destroyed = stats.get(statname + "gadgetdestroy", 0)
        self.terrorist_hunt.areas_secured = stats.get(statname + "servershacked", 0)
        self.terrorist_hunt.areas_defended = stats.get(statname + "serverdefender", 0)
        self.terrorist_hunt.areas_contested = stats.get(statname + "serveraggression", 0)
        self.terrorist_hunt.hostages_rescued = stats.get(statname + "hostagerescue", 0)
        self.terrorist_hunt.hostages_defended = stats.get(statname + "hostagedefense", 0)
        self.terrorist_hunt.blind_kills = stats.get(statname + "blindkills", 0)

        return self.terrorist_hunt

    async def check_terrohunt(self, data=None):
        """|coro|

        Checks the players general stats for terrorist hunt, only loading them if they haven't been loaded already"""
        if self.terrorist_hunt is None:
            await self.load_terrohunt(data=data)
        return self.terrorist_hunt

    @property
    def wins(self):
        return self.won

    @property
    def losses(self):
        return self.lost
