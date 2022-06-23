from django import forms
from django.utils.safestring import mark_safe
from .models import MiniLeague, Gameweek, Fixture, AggregatedGame
from django.forms.widgets import NumberInput, DateInput
from django.contrib.admin import widgets
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

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
    '''start_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}),
                                 help_text='Specified date will filter fixtures',)
    end_date = forms.DateField(widget=NumberInput(attrs={'type': 'date'}),
                               help_text='Specified date will filter fixtures',)'''

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
        #self.fields['start_date'].widget = NumberInput(attrs={'type': 'date'})
        self.fields['start_date'].help_text = help_text
        self.fields['end_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        self.fields['end_date'].help_text = help_text
        # Gameweek Fee Tweaks
        self.fields['split_of_gameweek_fee'].help_text = "As GBP. Double check this value doesn't exceed Mini League's Gameweek Fee"
        self.fields['split_of_gameweek_fee'].widget.attrs['step'] = 0.05
        #Mini League tweaks
        if minileague:
            # Lock down the Mini League select box and assign the provided ML to the field
            ml = MiniLeague.objects.get(pk=minileague)
            self.fields['mini_league'].initial = ml
            self.fields['mini_league'].disabled = True
            # Set the min/max of the split gameweek fee field
            self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
            self.fields['split_of_gameweek_fee'].widget.attrs['max'] = ml.gameweek_fee
        ended = ["E", "D", ]
        self.fields['mini_league'].queryset = MiniLeague.objects.filter(owner=self.player).exclude(status__in=ended)


    class Meta:
        model = Gameweek
        fields = ['name', 'mini_league', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split', 'created_by',
                  ]
        widgets = {
            'start_date': forms.SelectDateWidget(),
            'end_date': forms.SelectDateWidget(),
        }


'''class CustomMMCF(forms.ModelMultipleChoiceField):
    def label_from_instance(self, choice):
        return choice.full_desc'''


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
        #Mini League disable
        self.fields['mini_league'].disabled = True
        self.fields['mini_league'].queryset = MiniLeague.objects.all()
        #self.fields['mini_league'].initial = self.instance.mini_league
        # Date fields
        # Set the min/max of the split gameweek fee field
        self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
        self.fields['split_of_gameweek_fee'].widget.attrs['max'] = self.instance.mini_league.gameweek_fee
        # Filter Fixtures options based on start/end dates
        self.fields['fixtures'].queryset = Fixture.objects.filter(ko_date__gte=self.instance.start_date,
                                                                   ko_date__lte=self.instance.end_date, )
        self.fields['fixtures'].widget.attrs['size'] = 10
        self.fields['fixtures'].help_text = "To expand list, edit dates above and Save"
        #self.fields['fixtures'].widget = forms.CheckboxSelectMultiple
        '''self.fields['fixtures'] = CustomMMCF(
            queryset=Fixture.objects.filter(ko_date__gte=self.instance.start_date,
                                            ko_date__lte=self.instance.end_date,),
            widget=forms.CheckboxSelectMultiple,
        )'''


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
        #self.fields['start_date'].widget = DateInput()
        self.fields['start_date'].help_text = help_text
        self.fields['end_date'].widget.attrs['placeholder'] = "dd/mm/yyyy"
        self.fields['end_date'].help_text = help_text
        # Gameweek Fee Tweaks
        self.fields[
            'split_of_gameweek_fee'].help_text = "As GBP. Double check this value doesn't exceed Mini League's Gameweek Fee"
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
        ended = ["E", "D", ]
        self.fields['mini_league'].queryset = MiniLeague.objects.filter(owner=self.player).exclude(status__in=ended)


class LeaderboardEditForm(LeaderboardCreateForm):

    class Meta:
        model = AggregatedGame
        fields = ['name', 'mini_league', 'start_date', 'end_date', 'split_of_gameweek_fee', 'prize_split',
                  'created_by', 'gameweeks', 'primary_ag', ]
        widgets = {
            'start_date': forms.SelectDateWidget(),
            'end_date': forms.SelectDateWidget(),
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
        #self.fields['primary_ag'].widget.attrs['class'] = 'form-switch'
        # Mini League disable
        self.fields['mini_league'].disabled = True
        self.fields['mini_league'].queryset = MiniLeague.objects.all()
        # self.fields['mini_league'].initial = self.instance.mini_league
        # Date fields
        # Set the min/max of the split gameweek fee field
        self.fields['split_of_gameweek_fee'].widget.attrs['min'] = 0
        self.fields['split_of_gameweek_fee'].widget.attrs['max'] = self.instance.mini_league.gameweek_fee


