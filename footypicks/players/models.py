from django.db import models
from django.contrib.auth.models import User

class Player(models.Model):
    #Uses out of the box Django user for auth etc
    # This model extends the user model to allow additional fields like display pics etc
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

    def username(self):
        return self.user.username

    def real_name(self):
        return f"{self.user.first_name} {self.user.last_name}"