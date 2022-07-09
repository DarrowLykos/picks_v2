from django.urls import path

from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='index'),
    path('minileague/<int:pk>/', views.MiniLeagueDetail.as_view(), name='minileague_detail'),
    path('minileague/<int:pk>/join/', views.MiniLeagueJoin.as_view(), name='minileague_join'),
    path('minileague/<int:pk>/invite/', views.MiniLeagueInvite.as_view(), name='minileague_invite'),
    path('minileague/<int:pk>/edit/', views.MiniLeagueEdit.as_view(), name='minileague_edit'),
    path('minileague/<int:pk>/end/', views.MiniLeagueEnd.as_view(), name='minileague_end'),
    path('minileague/<int:pk>/games/', views.GameweekList.as_view(), name='gameweek_list'),
    path('profile/<int:pk>/', views.PlayerDetail.as_view(), name='player_detail'),
    path('profile/<int:pk>/transactions/', views.PlayerTransactionList.as_view(), name='player_transactions_by_id'),
    path('profile/edit_details/', views.PlayerEdit.as_view(), name='player_edit'),
    path('profile/transactions/', views.PlayerTransactionList.as_view(), name='player_transactions'),
    path('profile/new_transaction/', views.PlayerTransactionCreate.as_view(), name='player_transaction_new'),
    path('profile/edit_transaction/<int:pk>/', views.PlayerTransactionEdit.as_view(), name='player_transaction_edit'),
    path('game/<int:pk>/', views.GameweekDetail.as_view(), name='game_detail'),
    path('game/<int:pk>/edit/', views.GameweekEdit.as_view(), name='game_edit'),
    path('game/create/', views.GameweekCreate.as_view(), name='game_create'),
    path('game/<int:pk>/end/', views.GameweekEnd.as_view(), name='game_end'),
    path('game/<int:pk>/predict/', views.EditPredictions.as_view(), name='game_predict'),
    path('leaderboard/<int:pk>/', views.GameweekLeaderboardDetail.as_view(), name='leaderboard_detail'),
    path('leaderboard/<int:pk>/edit/', views.GameweekLeaderboardEdit.as_view(), name='leaderboard_edit'),
    path('leaderboard/create/', views.GameweekLeaderboardCreate.as_view(), name='leaderboard_create'),
    path('leaderboard/<int:pk>/end/', views.GameweekLeaderboardEnd.as_view(), name='leaderboard_end'),
    path("signup/", views.PlayerSignUp.as_view(), name="signup"),
    path("about/", views.AboutView.as_view(), name="about")
]
