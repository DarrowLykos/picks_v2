from django.db import models
from players.models import Player, Transaction
from .custom_functions import randomised_password
from django.core.validators import MinValueValidator
from datetime import datetime, timedelta, timezone
from django.core.validators import RegexValidator
from django.db.models import Count, Sum, Avg, Max, Min
import pytz
from django.db.models import F
from .sportsDB import GetRoundEvents



# MODEL DESCRIPTIONS
'''
SCORE:          Model for applying a scoring structure to a game. Also calcs points for accurate predictions. The model 
                has functions that take a player's prediction and the actual result and returns an integer value 
                representing the points awarded for the prediction.
COMPETITION:    Real football league data. E.g. Premier League, Championship, FA Cup, etc. 
                Data provided by https://www.thesportsdb.com/ API. 
TEAM:           Real football team data. E.g. Manchester United, Arsenal, etc
                Data provided by https://www.thesportsdb.com/ API.
FIXTURE:        Real football fixture data. E.g. Manchester United vs Arsenal.
                Data provided by https://www.thesportsdb.com/ API.
MINILEAGUE:     The top level of the Footy Picks game. Players join a MiniLeague to participate in Gameweeks for that 
                League. Their performance is aggregated in the AggregatedGame leaderboards.
                Also referred to as Mini-League or League.
GAMEWEEK:       The crux of the game. Players participate in multiple Gameweeks within a Mini-League to score points. 
                A gameweek will consist of multiple Fixtures for players to make their predictions on.
                Also referred to as Game.
AGGREGATEDGAME: A variation on the Gameweek model. This model aggregates multiple Gameweeks into a leaderboard. 
                The primary difference between the two is that an AG doesn't have child predictions/fixtures, it has 
                child Gameweeks.
                Also referred to as an AG or Leaderboard.
PREDICTION:     A players prediction on a specific fixture. The Prediction is linked to a Gameweek, Player and Fixture.
                Also referred to as Pick.
PLAYERAGGREGA
TEDGAME:        A relationship model for Player and AggregatedGame. The purpose of the which is to aggregate all the 
                player's predictions for an AggregatedGame because a Prediction on its own has no relationship to an
                AggregatedGame.
PLAYERGAMEWEEK: A relationship model for Player and Gameweek. The purpose of the which is to aggregate all the 
                player's predictions for a Gameweek because a Prediction on its own has no relationship to a Gameweek.  
'''


# Statuses for Mini Leagues, Games and AggregatedGames.
GAME_STATUS = (
        ("L", "Live"),
        ("E", "Ended"),
        ("D", "Deleted"),
        ("U", "Upcoming"),
    )

# Prize split breakdown options for Games and AggregatedGames
PRIZE_SPLIT_LIST = (
    ("1", "100% to 1st place"),
    ("2", "60/40 to 1st and 2nd"),
    ("3", "50/30/20 to 1st, 2nd and 3rd"),
    ("4", "40/30/20/10 to 1st, 2nd, 3rd and 4th"),
)


# Function to convert the options from the PRIZE_SPLIT_LIST into a table of decimal values. The table is then
# used to calculate the prize split per player.
# TODO add complexity of tied positions sharing multiple prizes at a different split
def prize_split_table(prize_split):
    prize_split = int(prize_split)
    if prize_split == 1:
        return {1: 1}
    elif prize_split == 2:
        return {1: 0.6,
                2: 0.4,
                }
    elif prize_split == 3:
        return {1: 0.5,
                2: 0.3,
                3: 0.2,
                }
    elif prize_split == 4:
        return {1: 0.4,
                2: 0.3,
                3: 0.2,
                4: 0.1,
                }
    else:
        return None

class Score(models.Model):
    name = models.CharField(max_length=100)
    correct_score = models.IntegerField(default=0)
    correct_result = models.IntegerField(default=0)
    correct_home_score = models.IntegerField(default=0)
    correct_away_score = models.IntegerField(default=0)
    joker_multiplier = models.IntegerField(default=0)
    joker_correct_score = models.IntegerField(default=0)
    joker_correct_result = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    def get_fields(self):
        fields = [(field.name, field.value_to_string(self)) for field in Score._meta.fields]
        fields = fields[2:]
        dct = []
        for k, v in fields:
            if int(v) > 0:
                dct.append((k, v))
        return dct

    def split_scores(self, predicted_score, actual_score):
        predicted_score = predicted_score.split("-")
        actual_score = actual_score.split("-")
        return predicted_score, actual_score

    def check_correct_score(self, predicted_score, actual_score):
        if predicted_score == actual_score:
            return self.correct_score
        else:
            return 0

    def check_correct_result(self, predicted_score, actual_score):
        predicted_score, actual_score = self.split_scores(predicted_score, actual_score)

        def res(home_score, away_score):
            # 1 = Draw
            # 2 = Home
            # 3 = Away
            home_score = int(home_score)
            away_score = int(away_score)

            if home_score == away_score:
                return 1
            elif home_score > away_score:
                return 2
            elif home_score < away_score:
                return 3

        if res(predicted_score[0], predicted_score[1]) == res(actual_score[0], actual_score[1]):
            return self.correct_result
        else:
            return 0

    def check_joker(self, points, joker):
        if joker:
            return points * self.joker_multiplier
        else:
            return points

    def calculate_points(self, predicted_score, actual_score, joker):
        print(predicted_score, actual_score, joker)
        if any(ele in actual_score for ele in ["P-P", "?-?"]):
            return 0
        points = self.check_correct_score(predicted_score, actual_score)
        points += self.check_correct_result(predicted_score, actual_score)
        points = self.check_joker(points, joker)
        print("POINTS: ", points)
        return points

# REAL WORLD FOOTBALL DATA
class Competition(models.Model):
    # A football competition such as the Premier League or FA Cup
    sportsdb_id = models.CharField(verbose_name="SportsDb ID", max_length=20, null=True, blank=True)
    name = models.CharField(max_length=25)
    short_name = models.CharField(max_length=3)
    season = models.CharField(max_length=9, validators=[RegexValidator(r"\d{4}-\d{4}")])

    def __str__(self):
        return f"{self.name} | {self.season}"

    def get_fixtures_by_round(self, round_number):
        fixtures = GetRoundEvents(self, round_number)
        fixtures.update_fixtures()


class Team(models.Model):
    # A football team
    sportsdb_id = models.CharField(verbose_name="SportsDb ID", max_length=20, null=True, blank=True)
    long_name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=12)
    initial_name = models.CharField(max_length=3)
    thumbnail = models.ImageField('Logo', upload_to="team-logos/", blank=True, null=True)
    competitions = models.ManyToManyField(Competition)

    def __str__(self):
        return self.short_name

    class Meta:
        ordering = ('long_name', )

    def get_home_fixtures(self, comp=None, status=None, limit=None):
        # Return list of home fixtures with optional filters
        # comp filters by Competition model
        # status filters by Fixture status
        # limit returns set number of fixtures
        pass

    def get_away_fixtures(self, comp=None, status=None, limit=None):
        # Return list of away fixtures with optional filters
        # comp filters by Competition model
        # status filters by Fixture status
        # limit returns set number of fixtures

        pass

    def get_fixtures(self, comp=None, status=None, limit=None):
        # Return list of fixtures with optional filters
        # comp filters by Competition model
        # status filters by Fixture status
        # limit returns set number of fixtures
        pass


class Fixture(models.Model):
    # A football fixture between two teams that Players will predict the score
    sportsdb_id = models.CharField(verbose_name="SportsDb ID", max_length=20, null=True, blank=True)
    home_team = models.ForeignKey(Team, null=True, on_delete=models.SET_NULL, related_name="home_fixtures",
                                  related_query_name="home_fixture")
    away_team = models.ForeignKey(Team, null=True, on_delete=models.SET_NULL, related_name="away_fixtures",
                                  related_query_name="away_fixture")
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    competition = models.ForeignKey(Competition, null=True, on_delete=models.SET_NULL)
    ko_date = models.DateField("Date", null=True)
    ko_time = models.TimeField("Kick-Off", null=True)
    penalties = models.BooleanField(default=False)
    extra_time = models.BooleanField(default=False)
    postponed = models.BooleanField(default=False)
    sportsdb_round = models.IntegerField(null=True, )


    def __str__(self):
        return self.full_desc()

    class Meta:
        ordering = ('ko_date', 'ko_time')

    @property
    def fixture(self):
        return f"{self.home_team} vs {self.away_team}"

    def fix(self):
        # ABC vs XYZ
        return f"{self.home_team.initial_name} vs {self.away_team.initial_name}"

    def full_desc(self):
        # Home Team vs Away Team | Comp Name | Kick Off | Score
        return f"{self.home_team} vs {self.away_team} | {self.competition.short_name} | {self.kick_off()} | {self.final_score}"

    def short_desc(self):
        # ABC vs XYZ | CMP
        return f"{self.home_team.initial_name} vs {self.away_team.initial_name} | {self.competition.short_name}"


    @property
    def final_score(self):
        # 1-2, 0-0, etc
        if self.postponed:
            return "P-P"
        elif self.home_score is not None and self.away_score is not None:
            res = f"{self.home_score}-{self.away_score}"
            '''if self.extra_time:
                return f"{res} AET"
            else:
                return res'''
            return res
        else:
            return "?-?"



    def kick_off(self, str=False):
        # Date, Time
        if str:
            return datetime.combine(self.ko_date, self.ko_time).strftime('%d %b %Y, %H:%M')
        else:
            return datetime.combine(self.ko_date, self.ko_time)

    def status(self):
        current_datetime = datetime.now()
        ko_datetime = self.kick_off(str=False)
        if self.postponed:
            return "Postponed"
        elif current_datetime < ko_datetime:
            return "Upcoming"
        elif current_datetime > ko_datetime:
            return "In play"
        elif current_datetime > ko_datetime + timedelta(minutes=90):
            return "Complete"
        else:
            return None

    def result(self):
        if not self.home_score and not self.away_score:
            return "TBC"
        if self.home_score > self.away_score:
            return "Home win"
        elif self.home_score < self.away_score:
            return "Away win"
        elif self.home_score == self.away_score:
            return "Draw"

# Footy Picks game data
class MiniLeague(models.Model):

    # Players are part of a Mini League where they compete against each other
    # to score the most points in each Gameweek
    name = models.CharField(max_length=25)
    # password to join league
    password = models.CharField(max_length=100, default=randomised_password)
    players = models.ManyToManyField(Player, blank=True)
    status = models.CharField(choices=GAME_STATUS, max_length=1, default="L")
    created_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL, related_name='owned', related_query_name='owner')
    new_players_allowed = models.BooleanField(default=True)
    last_update = models.DateTimeField(auto_now=True)
    score_structure = models.ForeignKey(Score, on_delete=models.SET_NULL, null=True)
    gameweek_fee = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mini League"

    def player_is_member(self, player_id):
        if self.players.filter(pk=player_id).exists():
            return True

    def player_is_owner(self, player_id):
        if self.owner.id == player_id:
            return True

    def get_gameweeks(self):
        # TODO: Add PlayerGameweek relationship to results so the tick/cross is displayed on Game lists
        return self.gameweek_set.filter(view_only=False)

    def get_aggregated_gameweeks(self):
        return self.leaderboards.all()

    def primary_leaderboard(self):
        return self.leaderboards.get(primary_ag=True)


class Gameweek(models.Model):
    # TODO block creation if start date > end date
    # A collection of fixtures for Players to make predictions on
    # There are multiple Gameweeks in a Mini League
    name = models.CharField(max_length=25)
    last_update = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(Player, on_delete=models.CASCADE)
    mini_league = models.ForeignKey(MiniLeague, on_delete=models.CASCADE)
    fixtures = models.ManyToManyField(Fixture, blank=True, )
    status = models.CharField(max_length=1, choices=GAME_STATUS, default="U")
    # fee = models.DecimalField(max_digits=10, decimal_places=2)  # Moved to MiniLeague
    # A percentage of the leftover prize pool. Used for Leaderboards,
    # aka view-only Games as they usually cover multiple Games
    # prize_pool_percent = models.DecimalField(max_digits=10, decimal_places=3)
    # A fixed amount taken from the Mini-league field called gameweek_fee to accumulate the prize pool for a Game.
    split_of_gameweek_fee = models.DecimalField(max_digits=10, decimal_places=2)
    view_only = models.BooleanField(default=False)  # turns the Gameweek into a leaderboard
    prize_split = models.CharField(max_length=1, choices=PRIZE_SPLIT_LIST, default="1")
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='gameweek_wins', related_query_name='gameweeks_won')
    # last_refresh = models.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('start_date', )

    def check_status(self):
        pass

    def award_prizes(self):
        # get list of players who have won, solve prize_list and then update paid field on Player/Gameweek and
        # Player/AggregatedGame, then create transaction. double check game has ended first.
        pass

    def leader(self):
        return self.leaderboard()[0]

    def leaderboard(self, limit=None):

        #self.update_points()
        lb = self.playergameweek_set.all()
        return lb.order_by('-points')

    def refresh_game(self, finalise=False, override=False):
        print('refresh')
        self.update_fixtures()
        if self.status in ["L", "U"] or override:
            current_datetime = datetime.now(pytz.utc)
            print(self.last_update + timedelta(minutes=15))
            if (self.last_update + timedelta(minutes=15) < current_datetime) or override:
                self.update_points()
                self.last_update = current_datetime
                if finalise:
                    self.status = "E"
                self.save()
                print('saved gw')


    def update_fixtures(self):
        unique_comps_ids = self.fixtures.order_by('competition').values_list('competition', flat=True).distinct()
        unique_comps = Competition.objects.filter(id__in=unique_comps_ids)
        from .sportsDB import GetRoundEvents
        for comp in unique_comps:
            rounds = self.fixtures.filter(competition=comp).order_by('sportsdb_round').values_list('sportsdb_round', flat=True).distinct()
            for round in rounds:
                if round:
                    print(f'Updating Round {round} of {comp}')
                    GetRoundEvents(comp, round).update_fixtures()

    def update_points(self):
        #self.playergameweek_set.update_points(self.mini_league.score_structure)
        for pg in self.playergameweek_set.all():
            try:
                pg.update_points()
            except:
                pass
        return True

    def count_fixtures(self):
        self.fixtures.all().count()

    def get_predictions_by_player(self, player_id):
        try:
            #self.playergameweek_set.get(player_id=player_id).predictions.update_points(self.mini_league.score_structure)
            print(self.playergameweek_set.get(player_id=player_id).predictions.all())
            picks = self.playergameweek_set.get(player_id=player_id).predictions.all()
            return picks
            #return self.playergameweek_set.get(player_id=player_id).get_predictions()
        except:
            return None

    def check_player_is_member(self, player_id):
        if self.mini_league.players.filter(pk=player_id).count() == 1:
            return True
        else:
            return False

    def prize_table(self):
        prize_pool = self.prize_pool()
        tbl = prize_split_table(self.prize_split)
        for k, v in tbl.items():
            tbl[k] = v * prize_pool

        lb = self.leaderboard()
        for plr in lb:
            # Check total points vs next player. If more than, then the player has current forloop count and return
            # prize split. If players have equal points then adjust prize split values to share between them.
            pass

        return tbl

    def prize_pool(self):
        total_plays = PlayerGameweek.objects.exclude(valid=False).annotate(
            count=Count('predictions')).filter(gameweek=self, count__gt=0).count()
        return total_plays * self.split_of_gameweek_fee


class AggregatedGame(models.Model):
    name = models.CharField(max_length=25)
    status = models.CharField(max_length=1, choices=GAME_STATUS, default="U")
    gameweeks = models.ManyToManyField(Gameweek, related_name="leaderboards", blank=True)
    mini_league = models.ForeignKey(MiniLeague, on_delete=models.CASCADE, related_name="leaderboards")
    primary_ag = models.BooleanField(verbose_name="Primary Mini-League Leaderboard", default=False) #  determines if this is the primary AG for the mini-league
    status = models.CharField(max_length=1, choices=GAME_STATUS, default="U")
    last_update = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL)
    # A fixed amount taken from the Mini-league field called gameweek_fee to accumulate the prize pool for a Game.
    # Fee is per Gameweek, so Leaderboards with multiple gameweeks will have multiple fees
    split_of_gameweek_fee = models.DecimalField(max_digits=10, decimal_places=2)
    prize_split = models.CharField(max_length=1, choices=PRIZE_SPLIT_LIST, default="1")
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='leaderboard_wins', related_query_name='leaderboards_won')

    def __str__(self):
        return f"{self.mini_league} | {self.name}"

    class Meta:
        verbose_name = "Leaderboard"
        verbose_name_plural = "Leaderboards"

    def update_points(self):
        for gw in self.gameweeks.all():
            for pg in gw.playergameweek_set.all():
                try:
                    pg.update_points()
                except:
                    pass
        return True

    def award_prizes(self):
        # get list of players who have won, solve prize_list and then update paid field on Player/Gameweek and
        # Player/AggregatedGame, then create transaction. double check game has ended first.
        pass

    def refresh_game(self, finalise=False, override=False):
        print('refresh')
        if self.status in ["L", "U"] or override:
            current_datetime = datetime.now(pytz.utc)
            print(self.last_update + timedelta(minutes=15))
            if self.last_update + timedelta(minutes=15) < current_datetime:
                self.update_points()
                self.last_update = current_datetime
                if finalise:
                    self.status = "E"
                self.save()
                print('saved gw')

    def leaderboard(self, limit=None):
        gws = self.gameweeks.all()
        lb = PlayerGameweek.objects.filter(gameweek__in=gws, valid=True).values(name=F('player__user__username')).annotate(
            sum_points=Sum('points'),
            count_gameweeks=Count('gameweek'),
            avg_points=Avg('points'),
            max_points=Max('points'),
            min_points=Min('points'),
        )
        if limit:
            return list(lb.order_by('-sum_points')[:limit])
        return list(lb.order_by('-sum_points'))


    def prize_table(self):
        prize_pool = float(self.prize_pool())
        tbl = prize_split_table(self.prize_split)
        for k, v in tbl.items():
            tbl[k] = v * prize_pool
        return tbl

    def prize_pool(self):
        total_plays = PlayerGameweek.objects.exclude(valid=False).annotate(count=Count('predictions')).filter(
            gameweek__in=self.gameweeks.all(),
            count__gt=0).count()
        print("TOT", total_plays)
        return total_plays * self.split_of_gameweek_fee

class PredictionManager(models.Manager):
    def update_points(self, score):
        qs = super().get_queryset()
        print(qs)
        points = 0
        for pick in qs:
            pick.update_points(score)
        return points


class Prediction(models.Model):
    # A prediction made by a player on a particular fixture
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    away_score = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    joker = models.BooleanField(default=False)
    submit_datetime = models.DateTimeField(auto_now_add=True)
    last_changed = models.DateTimeField()
    points = models.IntegerField(default=0)
    valid = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)
    objects = PredictionManager()

    def __str__(self):
        return f"{self.player} | {self.fixture}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            og = Prediction.objects.get(pk=self.pk)
            checklist = ['home_score',
                         'away_score',
                         'joker']
            for ite in checklist:
                og_item = getattr(og, ite)
                new_item = getattr(self, ite)
                if og_item != new_item:
                    self.last_changed = datetime.now()
        else:
            self.last_changed = datetime.now()
        super(Prediction, self).save(*args, **kwargs)

    def status(self):
        pass

    def pick_as_string(self):
        # 1-2, 0-0, etc
        return f"{self.home_score}-{self.away_score}"

    def update_points(self, score):
        if not self.valid:
            return 0
        points = score.calculate_points(self.pick_as_string(), self.fixture.final_score, self.joker)
        if points != self.points:
            self.points = points
            self.save()
            print("Updated Points", self, self.points)
        return points


    def validate_joker(self):
        # Check rules to see if too many jokers
        pass

    def validate_pick(self):
        # Check the pick is valid for different reasons.
        print(self.fixture.kick_off(False), self.last_changed)
        # Prediction was submitted after kick off = Invalid
        if self.fixture.kick_off(False) < self.last_changed:
            self.valid = False
            self.locked = True
            self.save()
            return False

        # Prediction was submitted before kick off = Valid
        elif self.fixture.kick_off(False) > self.last_changed:
            self.valid = True
            self.save()
            return True
        else:
            return None


class PlayerAggregatedGame(models.Model):
    player = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL)
    aggregated_game = models.ForeignKey(AggregatedGame, null=True, on_delete=models.SET_NULL)
    points = models.IntegerField(default=0)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class PlayerGameweekManager(models.Manager):
    def update_points(self, score):
        qs = super().get_queryset()
        print("!")
        for player in qs:
            print("!!")
            for pick in player.predictions.all():
                print("!!!")
                points = pick.update_points(score)
                player.points = points
                player.save()
                print(player, player.points)
        return qs

    def valid_games(self):
        qs = super().get_queryset().filter(predictions__gt=0)
        return qs


class PlayerGameweek(models.Model):
    # TODO: Check player balance, deduct fee, create transaction and validate
    player = models.ForeignKey(Player, null=True, on_delete=models.SET_NULL)
    gameweek = models.ForeignKey(Gameweek, null=True, on_delete=models.SET_NULL)
    predictions = models.ManyToManyField(Prediction, blank=True, null=True)
    points = models.IntegerField(default=0)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid = models.BooleanField(default=False)
    payment = models.ForeignKey(Transaction, null=True, on_delete=models.SET_NULL, related_name="game_payements",
                                related_query_name="game_payment", blank=True)
    prize = models.ForeignKey(Transaction, null=True, on_delete=models.SET_NULL, related_name="game_prizes",
                              related_query_name="game_prize", blank=True)

    objects = PlayerGameweekManager()

    def __str__(self):
        return f"{self.player} | {self.gameweek}"

    class Meta:
        verbose_name = "Player/Gameweek"
        verbose_name_plural = "Players/Gameweeks"

    def save(self, *args, **kwargs):
        '''try:
            if self.predictions.all().count() > 0:
                self.valid = True
        except ValueError:
            self.valid = False'''
        super(PlayerGameweek, self).save(*args, **kwargs)

    def update_points(self):
        self.predictions.update_points(self.gameweek.mini_league.score_structure)
        points = self.predictions.all().aggregate(total_points=Sum('points'))['total_points']
        print(points)
        self.points = points
        self.save()

    def update_paid(self):
        pass

    @property
    def total_valid_picks(self):
        return self.predictions.all().count()

    def get_fixtures(self):
        fixtures = self.gameweek.fixtures.all()
        return fixtures

    def validate_predictions(self):
        pass


    def get_joker(self):
        try:
            #return self.get_predictions().filter(joker=True)[0]
            return self.predictions.filter(joker=True)[0]
        except IndexError:
            return None

    '''@property
    def valid(self):
        # TODO Also check balance and invalidate if in arrears
        if self.predictions.all().count() > 0:
            return True
        else:
            return False'''