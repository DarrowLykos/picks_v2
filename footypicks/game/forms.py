from django import forms

class DummyPredictionForm(forms.Form):
    fld1 = forms.CharField()

    def send_email(self):
        # send email using the self.cleaned_data dictionary
        pass