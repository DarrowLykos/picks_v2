from django import forms
from django.utils.safestring import mark_safe
from .models import MiniLeague, Gameweek
from players.models import Player
from django.forms.widgets import NumberInput

class ImagePreviewWidget(forms.widgets.FileInput):
    def render(self, name, value, attrs=None, **kwargs):
        input_html = super().render(name, value, attrs=None, **kwargs)
        if value:
            img_html = mark_safe(
                f'<br><br><img src="{value.url}" width="200" />')
            return f'{input_html}{img_html}'
        return input_html

class DummyPredictionForm(forms.Form):
    fld1 = forms.CharField()

    def send_email(self):
        # send email using the self.cleaned_data dictionary
        pass


class JoinLeagueForm(forms.Form):
    league_password = forms.CharField(max_length=100,
                                      label="Enter the Mini-League password",)

class PlayerDetailsForm(forms.Form):
    username = forms.CharField(label='Username',
                               min_length=3,
                               max_length=25)
    display_pic = forms.ImageField(label='Display Pic',
                                   widget=ImagePreviewWidget,
                                   help_text='Current Display Pic',
                                   required=False)


class MiniLeagueEditForm(forms.ModelForm):

    class Meta:
        model = MiniLeague
        fields = ['name', 'password', 'status', 'score_structure', 'gameweek_fee', ]


class GameweekCreateForm(forms.ModelForm):
    start_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}))
    mini_league = forms.ModelChoiceField(
        queryset=MiniLeague.objects.all(),

    )
    created_by = forms.ModelChoiceField(
        queryset=Player.objects.all(),
        disabled=True,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop('player', None)
        minileague = kwargs.pop('minileague', None)
        print(minileague)
        super(GameweekCreateForm, self).__init__(*args, **kwargs)
        self.fields['created_by'].initial = self.player
        if minileague:
            self.fields['mini_league'].initial = MiniLeague.objects.get(pk=minileague)
            self.fields['mini_league'].disabled = True
        ended = ["E", "D",]
        self.fields['mini_league'].queryset = MiniLeague.objects.filter(owner=self.player).exclude(status__in=ended)





    class Meta:
        model = Gameweek
        fields = ['name', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split', 'mini_league', 'created_by', ]


class GameweekEditForm(GameweekCreateForm):

    class Meta:
        model = Gameweek
        fields = ['name', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split', ]

class GameweekLeaderboardForm(forms.Form):
    pass