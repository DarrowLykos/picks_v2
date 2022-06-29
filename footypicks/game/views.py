from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, TemplateView, View, RedirectView
from django.shortcuts import get_object_or_404, redirect, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormMixin
from .forms import *
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from players.models import Player, Transaction
from players.forms import TransactionCreateForm
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

DEAD_STATUSES = ("E", "D",)

# Custom Template Views (DRY)
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


# Home page View. Only seen by anons
class HomeView(TemplateView):
    template_name = 'game/pages/home.html'

    def get(self, request, *args, **kwargs):
        # Redirect user to their profile page if logged in
        if self.request.user.is_authenticated:
            #league_id = self.request.user.player.minileague_set.all().order_by('-pk')[0].id
            return redirect('game:player_detail', pk=request.user.player.id)
        else: # Redirect to login
            #return super().get(request, *args, **kwargs)
            return redirect('login')



# Mini League Views
class MiniLeagueDetail(DetailView):
    '''
    Overall View for a Mini-League.
    '''

    model = MiniLeague
    template_name = 'game/pages/minileague_detail.html'
    context_object_name = 'league'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # List of leaderboards for the ML
        context['leaderboards'] = self.object.get_aggregated_gameweeks()
        # context['players'] = self.object.players.all().order_by('user__username')
        # Gameweek queryset
        games = self.object.get_gameweeks()
        # Provide context with all games, previous 3 games and, upcoming 3 games
        context['games'] = games
        context['prev_games'] = games.filter(end_date__lte=datetime.now()).order_by('-end_date')[:3]
        context['next_games'] = games.filter(start_date__gte=datetime.now())[:3]
        # Score Structure of Mini-League
        context['score'] = self.object.score_structure.get_fields()
        # If user is logged in provide additional context
        if self.request.user.is_authenticated:
            current_player = self.request.user.player
            # These determine if user can edit the ML
            context['player_is_owner'] = self.object.player_is_owner(current_player.id)
            context['player_is_member'] = self.object.player_is_owner(current_player.id)
        # Try to provide Primary AG Leaderboard. Wrapped in a Try to avoid errors if one doesn't exist.
        try:
            context['primary_leaderboard'] = self.object.leaderboards.get(primary_ag=True).leaderboard()
        except:
            pass
        return context


class MiniLeagueJoin(LoginRequiredMixin, FormMixin, DetailView):
    '''
    Simple form for new players to join an existing ML.
    '''

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
        obj = self.model.objects.get(pk=kwargs['pk'])
        # Block players joining a dead League
        if any(ele in DEAD_STATUSES for ele in obj.status):
            messages.warning(self.request, "MiniLeague closed to new members")
            return redirect('game:minileague_detail', kwargs['pk'])
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        # Prefill password field if URL parameter exists
        initial['league_password'] = self.request.GET.get('password', None)
        return initial


    def post(self, request, *args, **kwargs):
        post = request.POST
        print(post)
        attempt_password = post['league_password']
        obj = self.model.objects.get(pk=kwargs['pk'])
        correct_password = obj.password
        print("P", correct_password)
        # Checks password provided.

        if obj.players.filter(pk=request.user.player.id).count() == 1: # Player is already a member
            messages.info(self.request, "Already a member of the Mini-league")
            return redirect('game:minileague_detail', kwargs['pk'])
        elif attempt_password == correct_password: # Correct password provided
            obj.players.add(request.user.player)
            obj.save()
            messages.success(self.request, "Successfully joined Mini-League")
            return redirect('game:minileague_detail', kwargs['pk'])
        else: # Incorrect password provided
            messages.error(self.request, "Incorrect password provided")
            return redirect('game:minileague_join', kwargs['pk'])

    def form_valid(self, form):
        print(form.cleaned_data)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('game:minileague_detail')


class MiniLeagueInvite(TemplateView):
    '''
    Simple redirect back to MiniLeagueDetail page providing a message with the invite link
    '''
    template_name = 'game/pages/minileague_detail.html'

    def get(self, request, *args, **kwargs):
        league_id = kwargs['pk']
        league = MiniLeague.objects.get(pk=league_id)
        # Only a League owner can request the password for a League
        if self.request.user.is_authenticated and league.player_is_owner(self.request.user.player.id):
            url = request.build_absolute_uri(reverse('game:minileague_join', kwargs={'pk': league_id}))
            url += f"?password={league.password}"
            # Provide the invite link as a message
            messages.info(request, f" Share Link: <a href='{url}'>{url}</a>")
        else:
            # User isn't authorised to ask for a link
            messages.warning(request, f"Only the League Owner can see the League Password")
        return redirect('game:minileague_detail', pk=league_id)


class MiniLeagueEdit(LoginRequiredMixin, UserPassesTestMixin, UpdateTemplate):
    '''
    Simple form to edit some of the Mini League values
    '''

    model = MiniLeague
    form_class = MiniLeagueEditForm
    fields = None

    def test_func(self):
        # Only League Owners can access this page
        return self.get_object().player_is_owner(self.request.user.player.id)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit League'
        context['subtitle'] = self.object.name

        # Generates tables of score structures for easy reference

        context['additional_html'] = "<h3>Score Structures</h3>"
        context['additional_html'] += "<div class='row'>"
        for s in Score.objects.all():
            context['additional_html'] += f"<div class'col-auto'><h4>{s.name}</h4><table>"

            for k, v in s.get_fields():
                context['additional_html'] += f"<tr><th>{k.replace('_', ' ').upper()}</th><td>{v}</td></tr>"
            context['additional_html'] += "</table></div>"
        context['additional_html'] += "</div>"
        return context


class MiniLeagueEnd(LoginRequiredMixin, UserPassesTestMixin, UpdateTemplate):
    pass

# Game Views
class GameweekDetail(DetailView):
    '''
    Basic view of a Gameweek
    '''

    model = Gameweek
    context_object_name = 'game'
    template_name = 'game/pages/gameweek_detail.html'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # refresh the Gameweek
        self.object.refresh_game()
        # Score structure
        context['score'] = self.object.mini_league.score_structure.get_fields()
        # Gameweek list queryset
        games = self.object.mini_league.get_gameweeks()
        # Provide the context with all games, recent 3 and next 3
        context['games'] = games
        context['prev_games'] = games.filter(end_date__lte=datetime.now()).order_by('-end_date')[:3]
        context['next_games'] = games.filter(start_date__gte=datetime.now())[:3]
        # Provide context with list of leaderboards
        context['leaderboards'] = self.object.mini_league.get_aggregated_gameweeks()
        # Prize pool table
        context['prize_pool'] = self.object.prize_table()
        # Provide additional context if user is logged in
        if self.request.user.is_authenticated:
            current_player = self.request.user.player
            context['player_is_owner'] = self.object.mini_league.player_is_owner(current_player.id)
        if self.request.user.is_authenticated and not any(ele in DEAD_STATUSES for ele in self.object.status):
            context['can_predict'] = self.object.check_player_is_member(current_player.id)
        # Tell page which player's predictions to display
        player_selected = self.request.GET.get("player", None)
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
    '''
    Full list of Gameweeks in a Mini League
    '''

    model = Gameweek
    template_name = 'game/pages/gameweek_list.html'

    def get_queryset(self, *args, **kwargs):
        league_id = self.kwargs.get('pk')
        qs = super(GameweekList, self).get_queryset(*args, **kwargs)
        qs = qs.filter(mini_league=league_id)
        return qs


class GameweekCreate(LoginRequiredMixin, UserPassesTestMixin, CreateTemplate):
    '''
    Creation of new Gameweeks
    '''

    model = Gameweek
    form_class = GameweekCreateForm
    fields = None

    def test_func(self):
        # Only allow Mini League owner to add new Gameweek to the League
        minileague = self.request.GET.get('minileague', None)
        if minileague:
            return MiniLeague.objects.get(pk=minileague).player_is_owner(self.request.user.player.id)
        else:  # No ML provided
            return True

    def get_success_url(self):
        # Go to Gameweek edit page afterwards to allow user to pick fixtures
        return reverse('game:game_edit', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Game'
        return context

    def get_form_kwargs(self):
        # Provides the form_class with additional kwargs to filter Foreign Key fields on the form
        kwargs = super(GameweekCreate, self).get_form_kwargs()
        kwargs.update({'player': self.request.user.player})
        kwargs.update({'minileague': self.request.GET.get('minileague', None)})
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Game created. Now add fixtures")
        form_cleaned = form.save()
        # Auto-adds the new Gameweek to the Primary AggregatedGame
        primary_ag = form_cleaned.mini_league.primary_leaderboard()
        if primary_ag:
            primary_ag.gameweeks.add(form_cleaned)
            messages.success(self.request, f"Game added to Primary Leaderboard: {primary_ag}")
        # Auto-add the Gameweek to any AggregatedGames that cover the same start/end period
        for ag in form_cleaned.mini_league.leaderboards.filter(start_date__gte=form_cleaned.start_date,
                                                               end_date__lte=form_cleaned.end_date):
            # TODO: auto-add gameweek to AggregatedGames
            pass

        return super().form_valid(form)


class GameweekEdit(LoginRequiredMixin, UserPassesTestMixin, UpdateTemplate):
    '''
    Edit the Gameweek details. Primarily used to apply Fixtures to the Gameweek.
    '''

    model = Gameweek
    form_class = GameweekEditForm
    fields = None

    def test_func(self):
        # Only the MiniLeague owner can edit the Gameweek
        return self.get_object().created_by == self.request.user.player

    def get_success_url(self):
        # Redirect to the Gameweek detail page
        return reverse('game:game_detail', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Game'
        context['subtitle'] = self.object.name
        return context

    def get_form_kwargs(self):
        # Provide the form_class with kwargs to filter Foreign Key fields
        kwargs = super(GameweekEdit, self).get_form_kwargs()
        kwargs.update({'player': self.request.user.player})

        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Game updated")
        form_cleaned = form.save()
        # Auto-adds the new Gameweek to the Primary AggregatedGame
        primary_ag = form_cleaned.mini_league.primary_leaderboard()
        if primary_ag and not primary_ag.gameweeks.filter(pk=form_cleaned.id).exists():
            primary_ag.gameweeks.add(form_cleaned)
            messages.success(self.request, f"Game added to Primary Leaderboard: {primary_ag}")
        return super().form_valid(form)


class GameweekEnd(GameweekEdit):
    form_class = GameweekEndForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'End Game'
        context['additional_html'] = "<table class='table table-sm table-hover w-50'><thead><th>Player</th><th>Points</th>"
        for x in self.object.leaderboard():
            context['additional_html'] += "<tr>"
            context['additional_html'] += f"<td>{x.player}</td><td>{x.points}</td>"
            context['additional_html'] += "</tr>"
        context['additional_html'] += "</table>"
        context['additional_html'] += f"<h5>Prize</h5>&pound;{self.object.prize_pool()}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Game ended")
        form_cleaned = form.save(commit=False)
        winner = form_cleaned.winner
        # create prize transaction for the winner
        player_gameweek = PlayerGameweek.objects.get(player=winner, gameweek=self.object.id)
        player_gameweek.prize = Transaction.objects.create(player=winner,
                                              type="P",
                                              amount=self.object.prize_pool(),
                                              pending=False,
                                              confirmed_date=datetime.now(),
                                              note=f"{self.object.mini_league} | {self.object}",
                                                           )
        form_cleaned.status = "E"
        form_cleaned.save()
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if any(ele in self.get_object().status for ele in DEAD_STATUSES):
            messages.error(request, "Game already ended")
            print(self.get_object().id)
            return redirect(reverse('game:game_detail',  kwargs={'pk': self.get_object().id}))
        return super().get(request, *args, **kwargs)

# Gameweek Leaderboard / Aggregated Game Views
class GameweekLeaderboardDetail(DetailView):
    model = AggregatedGame
    context_object_name = 'game'
    template_name = 'game/pages/leaderboard_detail.html'

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
        context['player_is_owner'] = self.object.mini_league.player_is_owner(self.request.user.player.id)

        return context


class GameweekLeaderboardCreate(LoginRequiredMixin, UserPassesTestMixin, CreateTemplate):
    model = AggregatedGame
    form_class = LeaderboardCreateForm
    fields = None


    def test_func(self):
        # Only allow Mini League owner to add new Gameweek to the League
        minileague = self.request.GET.get('minileague', None)
        if minileague:
            return MiniLeague.objects.get(pk=minileague).player_is_owner(self.request.user.player.id)
        else:  # No ML provided
            return True
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Leaderboard'
        return context

    def form_valid(self, form):
        form = form.cleaned_data
        primary_ag = form['primary_ag']
        ml = form.mini_league
        if ml.leaderboards.filter(primary_ag=True) == 1:
            messages.error(self.request, "Mini League already has a primary Leaderboard. Please remove that first, then try again")
            return reverse('game:leaderboard_create', kwargs={'pk': self.object.id, 'initial': form})
        # TODO double check split_of_gameweek_fee doesn't push us over the gameweek_fee for shared gameweeks
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(GameweekLeaderboardCreate, self).get_form_kwargs()
        kwargs.update({'player': self.request.user.player})
        kwargs.update({'minileague': self.request.GET.get('minileague', None)})
        return kwargs


class GameweekLeaderboardEdit(LoginRequiredMixin, UserPassesTestMixin, UpdateTemplate):
    model = AggregatedGame
    form_class = LeaderboardEditForm
    fields = None

    def test_func(self):
        # Only the MiniLeague owner can edit the Gameweek
        return self.get_object().created_by == self.request.user.player

    def get_success_url(self):
        # Redirect to the Gameweek detail page
        return reverse('game:leaderboard_detail', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Leaderboard'
        context['subtitle'] = self.object.name
        return context

    def form_valid(self, form):
        form_cleaned = form.save(commit=False)
        primary_ag = form_cleaned.primary_ag
        ml = form_cleaned.mini_league
        print(ml.leaderboards.filter(primary_ag=True))
        if ml.leaderboards.filter(primary_ag=True).count() >= 1 and primary_ag:
            messages.error(self.request, "Mini League already has a primary Leaderboard. Please remove that first, then try again")
            form_cleaned.primary_ag = False
            #return reverse('game:leaderboard_edit', kwargs={'pk': form_cleaned.id})
        form_cleaned.save()
        return super().form_valid(form)


class GameweekLeaderboardEnd(GameweekLeaderboardEdit):
    form_class = LeaderboardEndForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'End Game'
        context[
            'additional_html'] = "<table class='table table-sm table-hover w-50'><thead><th>Player</th><th>Points</th>"
        print(self.object.leaderboard())
        for x in self.object.leaderboard():
            context['additional_html'] += "<tr>"
            context['additional_html'] += f"<td>{x['name']}</td><td>{x['sum_points']}</td>"
            context['additional_html'] += "</tr>"
        context['additional_html'] += "</table>"
        context['additional_html'] += f"<h5>Prize</h5>&pound;{self.object.prize_pool()}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Leaderboard ended")
        form_cleaned = form.save(commit=False)
        winner = form_cleaned.winner
        # create prize transaction for the winner
        transaction = Transaction.objects.get_or_create(player=winner,
                                                        type="P",
                                                        amount=self.object.prize_pool(),
                                                        pending=False,
                                                        confirmed_date=datetime.now(),
                                                        note=self.object,
                                                        )
        form_cleaned.status = "E"
        form_cleaned.save()
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if any(ele in self.get_object().status for ele in DEAD_STATUSES):
            messages.error(request, "Leaderboard already ended")
            return redirect(reverse('game:leaderboard_detail',  kwargs={'pk': self.get_object().id}))
        return super().get(request, *args, **kwargs)

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

        # TODO Check players balance and warn if in arrears

        # Only allows members of the league to predict
        if not obj.player_is_member(request.user.player.id):
            messages.warning(self.request, "Only League Members can make predictions")
            return redirect('game:game_detail', kwargs['pk'])
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        def test_input(val):
            # Checks the value provided is a positive integer.
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
        # Gets or created a PlayerGameweek object that marries the Player to the Gameweek and links their predictions
        # to the gameweek
        player_gameweek = PlayerGameweek.objects.get(player=self.request.user.player, gameweek=Gameweek.objects.get(pk=kwargs['pk']))
        # Get the joker value from the form and checks the user has selected an option
        joker = request.POST.get('joker_select', "")
        if joker == "Select Joker Fixture...":
            messages.error(self.request, "Please select a Joker Fixture")
            # Sends the user back to the webpage if they haven't selected a joker
            return self.render_to_response()
        # Reset changed boolean to false. To be used later to identify if a pick has been changed.
        changed = False
        # Goes through the dictionary of form responses in the POST and checks if any fields were omitted.
        for x, y in post.items():
            # Only need to check if score fields are empty or invalid
            if any(ele in x for ele in ['home', 'away']):
                if not test_input(y):
                    # Rejects the submission
                    messages.error(self.request, "One or more inputs are empty/do not contain a positive number. Check your picks")
                    return redirect('game:game_predict', kwargs['pk'])
        # Loops through the dictionary of form response again and saves/updates Prediction records
        for x, y in post.items():
            # If the prediction already exists, then we update the Prediction record. We check the name of the key.
            # Form fields are called "exist_home_22" or "new_away_11" for example
            # The digits in exist relate to a Prediction ID, the digits in new relate to a Fixture ID
            if "exist" in x:
                # Gets the pick ID from the end of x after the underscore
                pick_id =int(x.split("_")[-1])
                # Gets the pick object
                pick = Prediction.objects.get(pk=pick_id)
                # Gets the fixture string to be used in comparisons
                fixture = pick.fixture
                # Checks the pick fixture hasn't started yet.
                if not pick.locked and fixture.status() == "Upcoming":
                    # Saves the home prediction value
                    if "home" in x:
                        # Only saves the value if it has changed
                        if pick.home_score != int(y):
                            pick.home_score = int(y)
                            pick.last_changed = datetime.now()
                            # msgs_success.append(f"{pick.fixture} prediction updated")
                            changed = True
                    else:  # Saves the away prediction value
                        if pick.away_score != int(y):
                            pick.away_score = int(y)
                            # msgs_success.append(f"{pick.fixture} prediction updated")
                            changed = True
                    print(pick.fixture.fixture, joker, pick.joker)
                    # Saves the joker boolean if the pick was selected as the new joker
                    if pick.fixture.fixture == joker and not pick.joker:
                        pick.joker = True
                        # msgs_success.append(f"{pick.fixture} prediction updated")
                        changed = True
                    # Removes the fixture as a joker if the joker has changed to another pick
                    elif pick.fixture.fixture != joker and pick.joker:
                        pick.joker = False
                        changed = True
                    # Saves the pick with the changes if the changed boolean is True
                    if changed:
                        pick.last_changed = datetime.now()
                        pick.save()
                        msgs_success.append(f"{pick.fixture.fixture} prediction updated")
                        changed = False
                        print('saved')
                else:  # Pick fixture has started, so block the changes.
                    print('not saved')
                    msgs_warnings.append(f"{pick.fixture.fixture} prediction not updated. Fixture locked")
            # Pick is new, so create the object
            elif "new" in x:
                # Gets the fixture ID from the end of x after the underscore and then the Fixture object
                fixture_id = int(x.split("_")[-1])
                fixture = Fixture.objects.get(pk=fixture_id)
                # Checks the fixture hasn't started yet
                if fixture.status() == "Upcoming":
                    # Creates the new Prediction record and saves the home_score, with a placeholder for away_score
                    if "home" in x:
                        new_pick = Prediction(player=request.user.player,
                                              fixture=fixture,
                                              home_score=int(y),
                                              away_score=0,
                                              )
                        msgs_success.append(f"{fixture.fixture} prediction added")
                    elif "away" in x:  # updates the away_score value
                        new_pick = Prediction.objects.filter(player=request.user.player,
                                                             fixture=fixture_id,
                                                             )[0]
                        new_pick.away_score = int(y)
                    # Updates the joker boolean if the pick was selected as a joker
                    if fixture == joker:
                        new_pick.joker = True

                    # Creates a fee transaction if one hasn't been created yet.
                    if not player_gameweek.payment:
                        # TODO check again the player's balance. Picks stay invalid if insufficient funds
                        fee = Transaction.objects.create(player=request.user.player,
                                                         type="F",
                                                         amount=player_gameweek.gameweek.mini_league.gameweek_fee,
                                                         pending=False,
                                                         confirmed_date=datetime.now(),
                                                         note=player_gameweek.gameweek,
                                                         )
                        player_gameweek.payment = fee
                        # Saves the player_gameweek record
                        player_gameweek.save()
                    # saves the pick record
                    new_pick.last_changed = datetime.now()
                    new_pick.save()
                    player_gameweek.predictions.add(new_pick)
                    print('created')
                else:  # Fixture has already started so block the prediction
                    messages.warning(self.request, f"{fixture.fixture} is {fixture.status}. Pick not submitted")

        # Sends list of messages to the request to notify user of successes/failures
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
        # TODO stop making PGs or figure out how to discount empty ones
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


# Player Views (move to own app eventually)
class PlayerDetail(DetailView):
    model = Player
    template_name = 'game/pages/player_detail.html'
    context_object_name = 'player'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['cleared_transactions'] = self.object.transaction_balances(pending=False)
        context['pending_transactions'] = self.object.transaction_balances(pending=True)
        all_transactions = self.object.all_transactions()
        context['all_transactions'] = all_transactions[5][:10]
        context['balances'] = all_transactions
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
    fields = None
    form_class = TransactionCreateForm

    def get_form_kwargs(self):
        kwargs = super(PlayerTransactionCreate, self).get_form_kwargs()
        player = self.request.user.player
        kwargs.update({'player': player})
        kwargs.update({'max_outgoing': player.transaction_balances(pending=False)[1]})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Transaction'
        context['subtitle'] = 'Transaction Details'
        context['additional_html'] = f"<h3>Current Balance</h3><strong>&pound;{self.get_form_kwargs()['max_outgoing']}</strong>"
        return context

    def form_valid(self, form):
        form_cleaned = form.save(commit=False)
        req_amount = form_cleaned.amount
        print(req_amount, self.get_form_kwargs()['max_outgoing'], form_cleaned.type)
        if req_amount > self.get_form_kwargs()['max_outgoing'] and form_cleaned.type == "O":
            messages.error(self.request, "Requested amount exceeds cleared balance")
            return redirect('game:player_transaction_new')
        return super().form_valid(form)


class PlayerTransactionEdit(LoginRequiredMixin, UpdateTemplate):
    model = Transaction

    def get_form_kwargs(self):
        kwargs = super(PlayerTransactionEdit, self).get_form_kwargs()
        kwargs.update({'player': self.request.user.player})
        return kwargs

class PlayerTransactionList(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'game/pages/transaction_list.html'

    def get_queryset(self, *args, **kwargs):
        player = self.request.user.player
        qs = super(PlayerTransactionList, self).get_queryset(*args, **kwargs)
        qs = qs.filter(player=player)
        print(qs)
        return qs.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.request.user.player
        all_transactions = player.all_transactions()
        context['balances'] = all_transactions
        return context
