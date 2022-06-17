from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, TemplateView, View, RedirectView
from django.shortcuts import get_object_or_404, redirect, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormMixin
from .forms import DummyPredictionForm, JoinLeagueForm, PlayerDetailsForm
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from players.models import Player, Transaction
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

'''
Custom Template Views
'''

class CreateTemplate(CreateView):
    template_name = 'game/pages/simple_form.html'
    fields = '__all__'
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create'
        context['subtitle'] = 'Create'
        return context


class UpdateTemplate(UpdateView):
    template_name = 'game/pages/simple_form.html'
    fields = '__all__'
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit'
        context['subtitle'] = 'Edit'
        return context


'''
Home page View. Only seen by anons
'''

class HomeView(TemplateView):
    template_name = 'game/pages/home.html'

    '''def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['leagues'] = self.request.user.player.minileague_set.all()
        return context'''

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            league_id = self.request.user.player.minileague_set.all().order_by('-pk')[0].id
            return redirect('game:minileague_detail', pk=league_id)
        else:
            return super().get(request, *args, **kwargs)
            # return redirect('login')


'''
Mini League Views
'''

class MiniLeagueDetail(DetailView):
    model = MiniLeague
    template_name = 'game/pages/minileague_detail.html'
    context_object_name = 'league'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['leaderboards'] = self.object.get_aggregated_gameweeks()
        context['players'] = self.object.players.all().order_by('user__username')
        games = self.object.get_gameweeks()
        context['games'] = games
        context['prev_games'] = games.filter(end_date__lte=datetime.now()).order_by('-end_date')[:3]
        context['next_games'] = games.filter(start_date__gte=datetime.now())[:3]
        context['score'] = self.object.score_structure.get_fields()
        if self.request.user.is_authenticated:
            current_player = self.request.user.player
            context['player_is_owner'] = self.object.player_is_owner(current_player.id)
            context['player_is_member'] = self.object.player_is_owner(current_player.id)
        context['primary_leaderboard'] = self.object.leaderboards.get(primary_ag=True).leaderboard()
        return context


class MiniLeagueJoin(LoginRequiredMixin, FormMixin, DetailView):
    model = MiniLeague
    template_name = 'game/pages/simple_form.html'
    context_object_name = 'league'
    form_class = JoinLeagueForm
    success_url = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Join League'
        context['subtitle'] = self.object.name
        return context

    def get(self, request, *args, **kwargs):
        statuses = ("E", "D",)
        obj = self.model.objects.get(pk=kwargs['pk'])
        if any(ele in statuses for ele in obj.status):
            messages.warning(self.request, "MiniLeague closed to new members")
            return redirect('game:minileague_detail', kwargs['pk'])

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['league_password'] = self.request.GET.get('password', None)
        return initial


    def post(self, request, *args, **kwargs):
        post = request.POST
        print(post)
        attempt_password = post['league_password']
        obj = self.model.objects.get(pk=kwargs['pk'])
        correct_password = obj.password
        print("P", correct_password)

        if obj.players.filter(pk=request.user.player.id).count() == 1:
            messages.info(self.request, "Already a member of the Mini-league")
            return redirect('game:minileague_detail', kwargs['pk'])
        elif attempt_password == correct_password:
            obj.players.add(request.user.player)
            obj.save()
            messages.success(self.request, "Successfully joined Mini-League")
            return redirect('game:minileague_detail', kwargs['pk'])
        else:
            messages.error(self.request, "Incorrect password provided")
            return redirect('game:minileague_join', kwargs['pk'])

    def form_valid(self, form):
        print(form.cleaned_data)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('game:minileague_detail')


class MiniLeagueInvite(TemplateView):
    template_name = 'game/pages/minileague_detail.html'

    def get(self, request, *args, **kwargs):
        league_id = kwargs['pk']
        league = MiniLeague.objects.get(pk=league_id)
        if self.request.user.is_authenticated and league.player_is_owner(self.request.user.player.id):
            url = request.build_absolute_uri(reverse('game:minileague_join', kwargs={'pk': league_id}))
            url += f"?password={league.password}"
            messages.info(request, f" Share Link: <a href='{url}'>{url}</a>")
        else:
            messages.warning(request, f"Only the League Owner can see the League Password")
        return redirect('game:minileague_detail', pk=league_id)


class MiniLeagueEdit(UpdateTemplate):
    model = MiniLeague

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit League'
        context['subtitle'] = self.object.name
        return context

'''
Game Views
'''

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
        games = self.object.mini_league.get_gameweeks()
        context['games'] = games
        context['prev_games'] = games.filter(end_date__lte=datetime.now()).order_by('-end_date')[:3]
        context['next_games'] = games.filter(start_date__gte=datetime.now())[:3]
        context['leaderboards'] = self.object.mini_league.get_aggregated_gameweeks()
        context['prize_pool'] = self.object.prize_table()

        player_selected = self.request.GET.get("player", None)
        statuses = ("E", "D",)
        if self.request.user.is_authenticated and not any(ele in statuses for ele in self.object.status):
            current_player = self.request.user.player
            context['can_predict'] = self.object.check_player_is_member(current_player.id)
        if player_selected:
            player_selected = Player.objects.get(pk=player_selected)
        elif self.request.user.is_authenticated:
            current_player = self.request.user.player
            player_selected = current_player
        else:
            return context

        context['player'] = player_selected
        context['player_picks'] = self.object.get_predictions_by_player(player_selected.id)


        return context

class GameweekList(ListView):
    model = Gameweek
    template_name = 'game/pages/gameweek_list.html'

    def get_queryset(self, *args, **kwargs):
        league_id = self.kwargs.get('pk')
        qs = super(GameweekList, self).get_queryset(*args, **kwargs)
        qs = qs.filter(mini_league=league_id)
        return qs


class GameweekCreate(CreateTemplate):
    model = Gameweek

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Game'
        return context


class GameweekEdit(UpdateTemplate):
    model = Gameweek

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Game'
        context['subtitle'] = self.object.name
        return context


'''
Gameweek Leaderboard / Aggregated Game Views
'''

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
        games = self.object.mini_league.get_gameweeks()
        context['games'] = games
        context['prev_games'] = games.filter(end_date__lte=datetime.now()).order_by('-end_date')[:3]
        context['next_games'] = games.filter(start_date__gte=datetime.now())[:3]
        # context['player_games'] = PlayerGameweek.objects.filter(gameweeks__in=self.object.mini_league.get_gameweeks())
        context['games_for_lb'] = self.object.gameweeks.all()
        context['leaderboards'] = self.object.mini_league.get_aggregated_gameweeks()
        print(self.object.leaderboard())
        context['leaderboard'] = self.object.leaderboard()

        return context


class GameweekLeaderboardCreate(CreateTemplate):
    model = AggregatedGame

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Leaderboard'
        return context


class GameweekLeaderboardEdit(UpdateTemplate):
    model = AggregatedGame

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Leaderboard'
        context['subtitle'] = self.object.name
        return context


'''
Prediction Views
'''

class EditPredictions(LoginRequiredMixin, FormMixin, DetailView):
    model = Gameweek
    template_name = 'game/pages/predictions_create.html'
    context_object_name = 'game'
    form_class = DummyPredictionForm
    success_url = ''

    def get_success_url(self):
        return reverse_lazy('game:game_detail')

    def get(self, request, *args, **kwargs):
        obj = self.model.objects.get(pk=kwargs['pk']).mini_league
        print(obj)
        print(obj.player_is_member(request.user.player.id))
        if not obj.player_is_member(request.user.player.id):
            messages.warning(self.request, "Only League Members can make predictions")
            return redirect('game:game_detail', kwargs['pk'])
        return super().get(request, *args, **kwargs)

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


'''
Player Views (move to own app eventually)
'''

class PlayerDetail(DetailView):
    model = Player
    template_name = 'game/pages/player_detail.html'
    context_object_name = 'player'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['cleared_transactions'] = self.object.transaction_balances(pending=False)
        context['pending_transactions'] = self.object.transaction_balances(pending=True)
        context['all_transactions'] = self.object.all_transactions()[5][:10]
        print("P", self.object.all_transactions()[:10])
        context['leagues'] = self.object.minileague_set.all()
        return context


class PlayerSignUp(CreateTemplate):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    fields = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Player'
        context['subtitle'] = 'Your Details'
        return context

    def form_valid(self, form):
        user = form.save()
        new_player = Player.objects.create(user=user)
        new_player.save()
        return super().form_valid(form)

class PlayerEdit(LoginRequiredMixin, FormView):
    form_class = PlayerDetailsForm
    template_name = 'game/pages/simple_form.html'
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Details'
        context['subtitle'] = 'Your Details'
        return context

    def get_object(self, queryset=None):
        return Player.objects.get(pk=self.request.user.player.id)

    def get_success_url(self):
        player = self.get_object()
        return reverse_lazy('game:player_edit')

    def get_initial(self):
        initial = super().get_initial()
        initial['display_pic'] = self.get_object().thumbnail
        initial['username'] = self.get_object().user.username
        return initial

    def form_valid(self, form):

        form = form.cleaned_data
        player = self.get_object()
        user = player.user
        if not user.username == form['username']:
            user.username = form['username']
            user.save()
            messages.success(self.request, "Username changed")
        print(player.thumbnail)
        print(form['display_pic'])
        print(form)
        if not player.thumbnail == form['display_pic']:
            player.thumbnail = form['display_pic']
            player.save()
            messages.success(self.request, "Display pic changed")
        return super().form_valid(form)


class PlayerTransactionCreate(LoginRequiredMixin, CreateTemplate):
    model = Transaction

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Transaction'
        context['subtitle'] = 'Transaction Details'
        return context

class PlayerTransactionEdit(LoginRequiredMixin, UpdateTemplate):
    model = Transaction

class PlayerTransactionList(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'game/pages/transaction_list.html'

    def get_queryset(self, *args, **kwargs):
        player = self.request.user.player
        qs = super(PlayerTransactionList, self).get_queryset(*args, **kwargs)
        qs = qs.filter(player=player)
        print(qs)
        return qs


