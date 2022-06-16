from django import forms

class DummyPredictionForm(forms.Form):
    fld1 = forms.CharField()

    def send_email(self):
        # send email using the self.cleaned_data dictionary
        pass


class JoinLeagueForm(forms.Form):
    league_password = forms.CharField(max_length=100, label="Enter the Mini-League password",)

class LeagueForm(forms.Form):
    pass

class GameweekForm(forms.Form):
    pass

class GameweekLeaderboardForm(forms.Form):
    pass