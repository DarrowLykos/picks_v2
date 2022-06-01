from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Competition)
admin.site.register(Team)
admin.site.register(Fixture)
admin.site.register(MiniLeague)
admin.site.register(Gameweek)
admin.site.register(PlayerGameweek)
admin.site.register(Prediction)
admin.site.register(Score)