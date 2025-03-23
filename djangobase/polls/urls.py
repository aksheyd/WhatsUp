from django.urls import path

from . import views

app_name = "polls"
urlpatterns = [
    # path("", views.IndexView.as_view(), name="index"),
    
    path("states/", views.StateListView.as_view(), name="state"),
    path("states/<int:state_id>/", views.CountyListView.as_view(), name="county"),
    path("states/<int:state_id>/<int:pk>/", views.CountyDetailView.as_view(), name="county_detail"),
    
    path("questions/", views.QuestionView.as_view(), name="question"),
    path("questions/<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("questions/<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    path("questions/<int:question_id>/vote/", views.vote, name="vote"),
]