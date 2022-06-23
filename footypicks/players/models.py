from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.db.models import Count, Sum, Avg, Max, Min

class Player(models.Model):
    #Uses out of the box Django user for auth etc
    # This model extends the user model to allow additional fields like display pics etc
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    thumbnail = models.ImageField(upload_to='player-pics/', blank=True, null=True, default='')

    def __str__(self):
        return self.user.username

    def username(self):
        return self.user.username

    def real_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def all_transactions(self):
        all = self.transaction_set.all().order_by('-date')
        # out = self.transaction_set.outgoings().order_by('-date')
        # inc = self.transaction_set.incomings().order_by('-date')
        out = all.filter(type="O") | all.filter(type="TT") | all.filter(type="F")
        inc = all.filter(type="I") | all.filter(type="TF") | all.filter(type="P")
        out_total = out.aggregate(total_amount=Sum('amount'))['total_amount']
        inc_total = inc.aggregate(total_amount=Sum('amount'))['total_amount']
        if not out:
            out_total = 0
        if not inc:
            inc_total = 0
        total = inc_total - out_total
        return inc, out, total, inc_total, out_total, all

    def transaction_balances(self, pending):
        all = self.transaction_set.all().order_by('-date')
        outg = all.filter(type="O") | all.filter(type="TT") | all.filter(type="F")
        inc = all.filter(type="I") | all.filter(type="TF") | all.filter(type="P")
        # outg = self.transaction_set.outgoings().order_by('-date')
        out_total = outg.filter(pending=pending).aggregate(total_amount=Sum('amount'))['total_amount']
        # inc = self.transaction_set.incomings().order_by('-date')
        inc_total = inc.filter(pending=pending).aggregate(total_amount=Sum('amount'))['total_amount']
        if not out_total:

            out_total = 0
        if not inc_total:
            inc_total = 0
        total = inc_total - out_total
        trans = inc | outg
        return trans, total, inc_total, out_total


    def prize_transactions(self, league=None):
        trans = self.transaction_set.filter(type="P")
        total = trans.aggregate(total=Sum('amount'))['total']
        return trans, total

    def get_trophies(self):
        return self.trophy_set.all()

class Trophy(models.Model):
    TROPHY_TYPES = (
        ("CHA", "Champion"),
        ("ONE", "1st Place"),
        ("SEC", "Second Place"),
        ("THI", "Third Place"),
        ("MON", "Highest Earner"),
    )


    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    type = models.CharField(max_length=3, choices=TROPHY_TYPES)
    description = models.CharField(max_length=30, null=True, blank=True)
    date = models.DateTimeField()

    class Meta:
        verbose_name = "Trophy"
        verbose_name_plural = "Trophies"

    def __str__(self):
        return f"{self.player} | {self.get_type_display()} | {self.description}"

class TransactionManager(models.Manager):
    def outgoings(self):
        qs = super().get_queryset().filter(type="O") | super().get_queryset().filter(type="TT") | super().get_queryset().filter(type="F")
        return qs

    def incomings(self):
        qs = super().get_queryset().filter(type="I") | super().get_queryset().filter(type="TF") | super().get_queryset().filter(type="P")
        return qs

class Transaction(models.Model):

    TRANSACTION_TYPES = (
        ("I", "Incoming from player"),
        ("O", "Outgoing to player"),
        ("TT", "Transfer to another player"),
        ("TF", "Transfer from another player"),
        ("P", "Prize income"),
        ("F", "Game Fee"),
        ("X", "Other"),
    )

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    type = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    pending = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=100, null=True, blank=True)
    objects = TransactionManager()

    def __str__(self):
        return f"{self.player} | {self.date} | {self.get_type_display()} | {self.amount}"

    def confirm_transaction(self, user, new_date=None, new_amount=None, new_type=None, new_player=None):
        if user.is_staff():
            self.confirmed_date = datetime.now()
            self.pending = False
            if new_date:
                self.date = new_date
            if new_amount:
                self.amount = new_amount
            if new_type:
                self.type = new_type
            if new_player:
                self.player = new_player
            self.save()
            return "Transaction confirmed"
        return "User must be Staff to confirm transaction"


