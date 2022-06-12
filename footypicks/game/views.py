from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, TemplateView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormMixin
from .forms import DummyPredictionForm
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from players.models import Player
from .models import *

# Create your views here.

class HomeView(TemplateView):
    template_name = 'game/pages/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['leagues'] = self.request.user.player.minileague_set.all()
        return context


class MiniLeagueDetail(DetailView):
    model = MiniLeague
    template_name = 'game/pages/minileague_detail.html'
    context_object_name = 'league'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['leaderboards'] = self.object.get_aggregated_gameweeks()
        context['players'] = self.object.players.all().order_by('user__username')
        context['games'] = self.object.get_gameweeks()
        context['prev_games'] = self.object.get_gameweeks().filter(end_date__lte=datetime.now())[:2]
        context['next_games'] = self.object.get_gameweeks().filter(start_date__gte=datetime.now())[:2]
        context['score'] = self.object.score_structure.get_fields()
        if self.request.user.is_authenticated:
            current_player = self.request.user.player
            context['player_is_owner'] = self.object.player_is_owner(current_player.id)
            context['player_is_member'] = self.object.player_is_owner(current_player.id)
        context['primary_leaderboard'] = self.object.leaderboards.get(primary_ag=True).leaderboard()
        return context

class GameweekDetail(DetailView):
    model = Gameweek
    context_object_name = 'game'
    template_name = 'game/pages/gameweek_detail.html'

    '''def get(self, *args, **kwargs):
        obj = self.model.objects.get(pk=kwargs['pk'])
        if obj.view_only:
            return redirect('game:leaderboard_detail', pk=kwargs['pk'])
        return super().get(*args, **kwargs)'''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.refresh_game()
        context['score'] = self.object.mini_league.score_structure.get_fields()
        context['games'] = self.object.mini_league.get_gameweeks()
        context['leaderboards'] = self.object.mini_league.get_aggregated_gameweeks()
        context['prize_pool'] = self.object.prize_table()

        player_selected = self.request.GET.get("player", None)
        if self.request.user.is_authenticated:
            current_player = self.request.user.player
            context['can_predict'] = self.object.check_player_is_member(current_player.id)
        if player_selected:
            player_selected = Player.objects.get(pk=player_selected)
        elif self.request.user.is_authenticated:
            player_selected = current_player
        else:
            return context

        context['player'] = player_selected
        context['player_picks'] = self.object.get_predictions_by_player(player_selected.id)


        return context


class GameweekLeaderboardDetail(DetailView):
    model = AggregatedGame
    context_object_name = 'game'
    template_name = 'game/pages/leaderboard_detail.html'

    '''def get(self, *args, **kwargs):
        obj = self.model.objects.get(pk=kwargs['pk'])
        if not obj.view_only:
            return redirect('game:game_detail', pk=kwargs['pk'])
        return super().get(*args, **kwargs)'''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.refresh_game()

        context['score'] = self.object.mini_league.score_structure.get_fields()
        context['games'] = self.object.mini_league.get_gameweeks()
        # context['player_games'] = PlayerGameweek.objects.filter(gameweeks__in=self.object.mini_league.get_gameweeks())
        context['games_for_lb'] = self.object.gameweeks.all()
        context['leaderboards'] = self.object.mini_league.get_aggregated_gameweeks()
        print(self.object.leaderboard())
        context['leaderboard'] = self.object.leaderboard()

        return context


class EditPredictions(LoginRequiredMixin, FormMixin, DetailView):
    model = Gameweek
    template_name = 'game/pages/predictions_create.html'
    context_object_name = 'game'
    form_class = DummyPredictionForm
    success_url = ''

    def get_success_url(self):
        return reverse_lazy('game:game_detail' )

    def post(self, request, *args, **kwargs):
        def test_input(val):
            try:
                val = int(val)
                if val < 0:  # if not a positive int print message and ask for input again
                    return False
            except ValueError:
                return False
            return True

        post = request.POST
        print(post)
        msgs_success = []
        msgs_warnings = []
        player_gameweek = PlayerGameweek.objects.get(player=self.request.user.player, gameweek=Gameweek.objects.get(pk=kwargs['pk']))
        joker = request.POST.get('joker_select', "")
        if joker == "Select Joker Fixture...":
            messages.error(self.request, "Please select a Joker Fixture")
            return self.render_to_response()
        print("JOKER: ", joker)
        changed = False
        for x, y in post.items():
            if any(ele in x for ele in ['home', 'away']):
                if not test_input(y):
                    messages.error(self.request, "One or more inputs are empty/do not contain a positive number. Check your picks")
                    return redirect('game:game_predict', kwargs['pk'])
        for x, y in post.items():
            if "exist" in x:
                print(x, y)
                pick_id =int(x.split("_")[-1])
                pick = Prediction.objects.get(pk=pick_id)
                fixture = pick.fixture
                if not pick.locked and fixture.status() == "Upcoming":
                    if "home" in x:
                        if pick.home_score != int(y):
                            pick.home_score = int(y)
                            pick.last_changed = datetime.now()
                            # msgs_success.append(f"{pick.fixture} prediction updated")
                            changed = True
                    else:
                        if pick.away_score != int(y):
                            pick.away_score = int(y)
                            # msgs_success.append(f"{pick.fixture} prediction updated")
                            changed = True
                    print(pick.fixture.fixture, joker, pick.joker)
                    if pick.fixture.fixture == joker and not pick.joker:
                        pick.joker = True
                        # msgs_success.append(f"{pick.fixture} prediction updated")
                        changed = True
                    elif pick.fixture != joker:
                        pick.joker = False
                    if changed:
                        pick.last_changed = datetime.now()
                        pick.save()
                        msgs_success.append(f"{pick.fixture.fixture} prediction updated")
                        changed = False
                        print('saved')
                else:
                    print('not saved')
                    msgs_warnings.append(f"{pick.fixture.fixture} prediction not updated. Fixture locked")
            elif "new" in x:
                print(x, y)
                fixture_id = int(x.split("_")[-1])
                fixture = Fixture.objects.get(pk=fixture_id)
                print(fixture.status())
                if fixture.status() == "Upcoming":
                    if "home" in x:
                        new_pick = Prediction(player=request.user.player,
                                              fixture=fixture,
                                              home_score=int(y),
                                              away_score=0,
                                              )
                        msgs_success.append(f"{fixture.fixture} prediction added")
                    elif "away" in x:
                        new_pick = Prediction.objects.filter(player=request.user.player,
                                                             fixture=fixture_id,
                                                             )[0]
                        new_pick.away_score = int(y)
                    if fixture == joker:
                        new_pick.joker = True
                    new_pick.last_changed = datetime.now()
                    new_pick.save()
                    player_gameweek.predictions.add(new_pick)
                    print('created')
                else:
                    messages.warning(self.request, f"{fixture.fixture} is {fixture.status}. Pick not submitted")
        msgs = list(dict.fromkeys(msgs_success))
        for msg in msgs:
            print(msg)
            messages.success(self.request, msg)
        msgs = list(dict.fromkeys(msgs_warnings))
        for msg in msgs:
            print(msg)
            messages.warning(self.request, msg)
        return redirect('game:game_detail', kwargs['pk'])


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_player = self.request.user.player
        player_gameweek = PlayerGameweek.objects.get_or_create(player=current_player, gameweek=self.object)[0]
        #existing_picks = player_gameweek.get_predictions()  # All predictions for the current gameweek/player
        existing_picks = player_gameweek.predictions.all()
        all_fixtures = self.object.fixtures.all()  # All fixtures assigned to the Gameweek
        new_fixtures = all_fixtures.exclude(
            id__in=existing_picks.values_list('fixture_id', flat=True))  # Fixtures with no prediction yet for the current player
        context['existing_picks'] = existing_picks
        context['all_fixtures'] = all_fixtures
        print(existing_picks.count())
        print(new_fixtures)
        context['new_fixtures'] = new_fixtures
        context['joker'] = player_gameweek.get_joker()
        context['score'] = self.object.mini_league.score_structure.get_fields()

        return context

class PlayerDetail(DetailView):
    model = Player
    template_name = 'game/pages/player_detail.html'
    context_object_name = 'player'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['cleared_transactions'] = self.object.transaction_balances(pending=False)
        context['pending_transactions'] = self.object.transaction_balances(pending=True)
        context['all_transactions'] = self.object.all_transactions()
        context['leagues'] = self.object.minileague_set.all()
        return context

