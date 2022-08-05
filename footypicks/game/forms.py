from django import forms
from django.utils.safestring import mark_safe
from .models import MiniLeague, Gameweek, Fixture, AggregatedGame
from django.forms.widgets import NumberInput, DateInput
from django.contrib.admin import widgets
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column


DEAD_STATUSES = ("E", "D", )

class ImagePreviewWidget(forms.widgets.FileInput):
    # Widget creates an image preview for form fields that allow users to change an image.
    # E.g. Profile Display Pic
    def render(self, name, value, attrs=None, **kwargs):
        input_html = super().render(name, value, attrs=None, **kwargs)
        if value:
            img_html = mark_safe(
                f'<br><br><img src="{value.url}" width="200" />')
            return f'{input_html}{img_html}'
        return input_html


class DummyPredictionForm(forms.Form):
    # Dummy form for predictions_create.html. Logic was too complicated at the time to create in here, so the form
    # itself is actually created in the template and evaluated in views.py. Because we use a FormMixin, a form_class is
    # required in views, so we provide this dummy that never gets used.
    fld1 = forms.CharField()


class JoinLeagueForm(forms.Form):
    # Simply form for new players to enter a password to join a Mini-League
    league_password = forms.CharField(max_length=100,
                                      label="Enter the Mini-League password",)


class PlayerDetailsForm(forms.Form):
    # Form for Players to update certain parts of their personal details. Updates both User and Player models
    email_address = forms.EmailField()
    username = forms.CharField(label='Username',
                               min_length=3,
                               max_length=25)
    display_pic = forms.ImageField(label='Display Pic',
                                   widget=ImagePreviewWidget,
                                   help_text='Current Display Pic',
                                   required=False)


class MiniLeagueEditForm(forms.ModelForm):
    # Form to edit a Mini-League. Not in use.
    class Meta:
        model = MiniLeague
        fields = ['name', 'password', 'status', 'score_structure', 'gameweek_fee', ]


class GameweekCreateForm(forms.ModelForm):
    # Form to create a new Game. Uses the Game model but with one additional parameter.

    # Automatically add the new Game to the Primary Leaderboard of the Mini-League
    add_to_primary_ag = forms.CheckboxInput(attrs={'style': 'width:20px;height:20px;'})

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        super(GameweekCreateForm, self).__init__(*args, **kwargs)
        # Player tweaks
        self.fields['created_by'].initial = self.player
        self.fields['created_by'].disabled = True
        self.fields['created_by'].widget = forms.HiddenInput()
        # date tweaks
        help_text = 'Specified date will filter fixtures'
        self.fields['start_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        self.fields['start_date'].help_text = help_text
        self.fields['end_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        self.fields['end_date'].help_text = help_text
        # Gameweek Fee Tweaks
        self.fields['split_of_gameweek_fee'].help_text = "As GBP. Double check this value doesn't " \
                                                         "exceed Mini League's Gameweek Fee"
        self.fields['split_of_gameweek_fee'].widget.attrs['step'] = 0.05
        # Mini League tweaks
        if minileague:
            # Lock down the Mini League select box and assign the provided ML to the field
            ml = MiniLeague.objects.get(pk=minileague)
            self.fields['mini_league'].initial = ml
            self.fields['mini_league'].disabled = True
            # Set the min/max of the split gameweek fee field
            self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
            self.fields['split_of_gameweek_fee'].widget.attrs['max'] = ml.gameweek_fee
        self.fields['mini_league'].queryset = MiniLeague.objects.filter(
            owner=self.player).exclude(status__in=DEAD_STATUSES) #  Don't include dead leagues

    class Meta:
        model = Gameweek
        fields = ['name', 'mini_league', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split', 'created_by',
                  ]
        widgets = {
            'start_date': forms.SelectDateWidget(),
            'end_date': forms.SelectDateWidget(),
        }


class GameweekEditForm(GameweekCreateForm):

    class Meta:
        model = Gameweek
        fields = ['name', 'status', 'mini_league', 'start_date', 'end_date',
                  'split_of_gameweek_fee', 'prize_split', 'fixtures', 'created_by',
                  ]
        widgets = {
            'start_date': forms.DateInput(),
            'end_date': forms.DateInput(),

        }

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        super(GameweekEditForm, self).__init__(*args, **kwargs)
        # Mini League disable
        self.fields['mini_league'].disabled = True
        self.fields['mini_league'].queryset = MiniLeague.objects.all()
        # self.fields['mini_league'].initial = self.instance.mini_league
        # Date fields
        # Set the min/max of the split gameweek fee field
        self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
        self.fields['split_of_gameweek_fee'].widget.attrs['max'] = self.instance.mini_league.gameweek_fee
        # Filter Fixtures options based on start/end dates
        self.fields['fixtures'].queryset = Fixture.objects.filter(ko_date__gte=self.instance.start_date,
                                                                  ko_date__lte=self.instance.end_date, )
        self.fields['fixtures'].widget.attrs['size'] = 10
        self.fields['fixtures'].help_text = "To expand list, edit dates above and Save"
        # self.fields['fixtures'].widget = forms.CheckboxSelectMultiple
        '''self.fields['fixtures'] = CustomMMCF(
            queryset=Fixture.objects.filter(ko_date__gte=self.instance.start_date,
                                            ko_date__lte=self.instance.end_date,),
            widget=forms.CheckboxSelectMultiple,
        )'''


class GameweekEndForm(GameweekEditForm):

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        super(GameweekEndForm, self).__init__(*args, **kwargs)
        self.fields['name'].disabled = True
        self.fields['mini_league'].disabled = True
        self.fields['start_date'].disabled = True
        self.fields['end_date'].disabled = True
        self.fields['split_of_gameweek_fee'].disabled = True
        self.fields['prize_split'].disabled = True
        self.fields['fixtures'].disabled = True
        self.fields['fixtures'].queryset = self.instance.fixtures
        self.fields['winner'].initial = self.instance.leader().player.id
        self.fields['winner'].queryset = self.instance.mini_league.players.all()
        self.fields['winner'].required = True
        self.fields['winner'].help_text = "Select outright winner of the game. For split pots, leave blank and " \
                                          "manually create prize transactions in Admin"
        print(self.instance.leader().player)


    class Meta(GameweekEditForm.Meta):
        fields = ['winner'] + GameweekEditForm.Meta.fields


class LeaderboardCreateForm(forms.ModelForm):

    class Meta:
        model = AggregatedGame
        fields = ['name', 'mini_league', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split',
                  'created_by', 'primary_ag']
        widgets = {
            'start_date': forms.SelectDateWidget(),
            'end_date': forms.SelectDateWidget(),
        }

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        super(LeaderboardCreateForm, self).__init__(*args, **kwargs)
        # Player tweaks
        self.fields['created_by'].initial = self.player
        self.fields['created_by'].disabled = True
        self.fields['created_by'].widget = forms.HiddenInput()
        # date tweaks
        help_text = 'Specified date will filter Games'
        self.fields['start_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        # self.fields['start_date'].widget = DateInput()
        self.fields['start_date'].help_text = help_text
        self.fields['end_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        self.fields['end_date'].help_text = help_text
        # Gameweek Fee Tweaks
        self.fields[
            'split_of_gameweek_fee'].help_text = "As GBP. Double check this value doesn't exceed Mini League's " \
                                                 "Gameweek Fee"
        self.fields['split_of_gameweek_fee'].widget.attrs['step'] = 0.05
        # Mini League tweaks
        if minileague:
            # Lock down the Mini League select box and assign the provided ML to the field
            ml = MiniLeague.objects.get(pk=minileague)
            self.fields['mini_league'].initial = ml
            self.fields['mini_league'].disabled = True
            # Set the min/max of the split gameweek fee field
            self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
            self.fields['split_of_gameweek_fee'].widget.attrs['max'] = ml.gameweek_fee
        self.fields['mini_league'].queryset = MiniLeague.objects.filter(
            owner=self.player).exclude(status__in=DEAD_STATUSES)


class LeaderboardEditForm(LeaderboardCreateForm):

    class Meta:
        model = AggregatedGame
        fields = ['name', 'mini_league', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split',
                  'created_by', 'gameweeks', 'primary_ag', ]
        widgets = {
            'start_date': forms.DateInput(),
            'end_date': forms.DateInput(),
            'primary_ag': forms.CheckboxInput(attrs={'style': 'width:20px;height:20px;'})
        }

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        super(LeaderboardEditForm, self).__init__(*args, **kwargs)
        # Gameweek select tweaks
        self.fields['gameweeks'].queryset = Gameweek.objects.filter(mini_league=self.instance.mini_league,
                                                                    start_date__gte=self.instance.start_date,
                                                                    end_date__lte=self.instance.end_date,
                                                                    )
        self.fields['gameweeks'].widget.attrs['size'] = 10
        self.fields['gameweeks'].help_text = "To expand list, edit dates above and Save"
        # Primary AG tweaks
        self.fields['primary_ag'].help_text = "Only one Primary Ag per Mini League"
        # self.fields['primary_ag'].widget.attrs['class'] = 'form-switch'
        # Mini League disable
        self.fields['mini_league'].disabled = True
        self.fields['mini_league'].queryset = MiniLeague.objects.all()
        # self.fields['mini_league'].initial = self.instance.mini_league
        # Date fields
        # Set the min/max of the split gameweek fee field
        self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
        self.fields['split_of_gameweek_fee'].widget.attrs['max'] = self.instance.mini_league.gameweek_fee


class LeaderboardEndForm(LeaderboardEditForm):

    class Meta(LeaderboardEditForm.Meta):
        fields = ['winner'] + LeaderboardEditForm.Meta.fields
        exclude = ['primary_ag', ]

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        super(LeaderboardEditForm, self).__init__(*args, **kwargs)
        self.fields['name'].disabled = True
        self.fields['mini_league'].disabled = True
        self.fields['start_date'].disabled = True
        self.fields['end_date'].disabled = True
        self.fields['split_of_gameweek_fee'].disabled = True
        self.fields['prize_split'].disabled = True
        self.fields['gameweeks'].disabled = True
        self.fields['winner'].queryset = self.instance.mini_league.players.all()
        self.fields['gameweeks'].queryset = self.instance.gameweeks
        self.fields['winner'].help_text = "Select outright winner of the game. For split pots, leave blank and " \
                                          "manually create prize"
        self.fields['mini_league'].queryset = MiniLeague.objects.all()
        self.fields['gameweeks'].widget.attrs['size'] = 10
