from django import forms
from django.utils.safestring import mark_safe
from .models import Player, Transaction

class TransactionCreateForm(forms.ModelForm):

    class Meta:
        model = Transaction
        fields = ['player', 'type', 'amount', 'note', ]

        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Pop additional kwargs before the super function
        self.player = kwargs.pop('player', None)
        self.max_outgoing = kwargs.pop('max_outgoing', None)
        super(TransactionCreateForm, self).__init__(*args, **kwargs)
        # Player tweaks
        self.fields['player'].initial = self.player
        self.fields['player'].disabled = True
        self.fields['amount'].widget.attrs['min'] = 0
        self.fields['type'].initial = "I"
        self.fields['type'].choices = (("I", "Incoming from player"),
                                       ("O", "Outgoing to player"),
                                       )
        self.fields['amount'].help_text = ""
