from django import forms
from django.utils.safestring import mark_safe

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



class LeagueForm(forms.Form):
    pass

class GameweekForm(forms.Form):
    pass

class GameweekLeaderboardForm(forms.Form):
    pass