from django.urls import path

from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='index'),
    path('minileague/<int:pk>/', views.MiniLeagueDetail.as_view(), name='minileague_detail'),
    path('game/<int:pk>/', views.GameweekDetail.as_view(), name='game_detail'),
    path('game/<int:pk>/predict/', views.EditPredictions.as_view(), name='game_predict'),
    path('leaderboard/<int:pk>/', views.GameweekLeaderboardDetail.as_view(), name='leaderboard_detail'),

    ]