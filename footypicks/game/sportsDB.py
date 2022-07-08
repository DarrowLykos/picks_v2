# All the functions and processes in dealing with the SportDB website go here
import requests
from datetime import datetime
import pytz
import datetime as dt

URL_PREFIX = "https://www.thesportsdb.com/api/v1/json/2/"

'''for round in rounds:
...     url = f"{url1}{premier.sportsdb_id}&r={round}&s=2021-2022"
...     for event in requests.get(url).json()['events']:
...             print(event)'''

CUP_ROUNDS = {
    'Quarter-Final': 125,
    'Semi-Final': 150,
    'Playoff': 160,
    'Playoff Semi-Final': 170,
    'Playoff Final': 180,
    'Final': 200,
}

LONDON_TZ = pytz.timezone('Europe/London')

class GetRoundEvents:

    def __init__(self, comp, round):
        self.comp = comp
        self.round = str(round)
        self.url = f"{URL_PREFIX}eventsround.php?id={comp.sportsdb_id}&r={self.round}&s={comp.season}"
        print(self.url)
        self.data = requests.get(self.url).json()['events']

    def update_team(self, team_data):
        from .models import Team
        team, created = Team.objects.get_or_create(sportsdb_id=team_data[0])
        if created:
            team.long_name = team_data[1]
            team.short_name = team_data[1][:12]
            team.initial_name = team_data[1][:3].upper()
        team.competitions.add(self.comp)
        team.save()
        return Team.objects.get(pk=team.id)

    def update_fixtures(self):
        from .models import Fixture
        for event in self.data:
            home_data = [str(event['idHomeTeam']), event['strHomeTeam']]
            away_data = [str(event['idAwayTeam']), event['strAwayTeam']]
            print(home_data, away_data)
            event_id = str(event['idEvent'])
            event_status = event['strStatus']
            home_team = self.update_team(home_data)
            away_team = self.update_team(away_data)
            print(event_id)
            fixture, created = Fixture.objects.get_or_create(sportsdb_id=event_id)
            if created:
                fixture.home_team = home_team
                fixture.away_team = away_team
                fixture.competition = self.comp

            if event_status == "Match Finished":
                fixture.home_score = int(event['intHomeScore'])
                fixture.away_score = int(event['intAwayScore'])
            if not event['strPostponed'] == "no":
                fixture.postponed = True
                fixture.sportsdb_id = None
            fixture.sportsdb_round = int(event['intRound'])
            ko_date = datetime.strptime(event['dateEvent'], "%Y-%m-%d")
            ko_time = datetime.strptime(event['strTime'], "%H:%M:%S").time()
            ko = datetime.combine(ko_date, ko_time)
            ko += LONDON_TZ.dst(ko)
            fixture.ko_date = ko.strftime("%Y-%m-%d")
            fixture.ko_time = ko.strftime("%H:%M:%S")
            fixture.save()
            print(fixture.short_desc(), "Created:", created)


'''class GetFixture:

    def __init__(self, api_id):
        self.api_id = api_id
        self.url = "https://www.thesportsdb.com/api/v1/json/2/eventresults.php?id=" + str(api_id)
        self.data = self.get_data()

    def get_data(self):
        try:
            res = requests.get(self.url)
        except Exception as e:
            print("Error retrieving fixture data", e)
        return res.json()['events'][0]

    def status(self):
        return self.data['strStatus']

    def home_team(self):
        return self.data['strHomeTeam']

    def away_team(self):
        return self.data['strAwayTeam']

    def date(self):
        return self.data['dateEvent']

    def kickoff(self):
        return self.data['strTime']'''

