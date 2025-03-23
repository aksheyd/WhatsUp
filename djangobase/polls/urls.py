from django.urls import path

from . import views

app_name = "polls"
urlpatterns = [
    # path("", views.IndexView.as_view(), name="index"),
    
    path("states/", views.StateListView.as_view(), name="state"),
    path("states/<int:state_id>/", views.CountyListView.as_view(), name="county"),
    path("states/<int:state_id>/<int:pk>/", views.CountyDetailView.as_view(), name="county_detail"),
    
    path("states/<int:state_id>/<int:pk>/questions/", views.QuestionView.as_view(), name="question"),
    path("states/<int:state_id>/<int:pk>/questions/generate", views.generate_question, name="generate_question"),

    path("states/<int:state_id>/<int:pk>/questions/<int:pk2>/", views.DetailView.as_view(), name="detail"),
    
    path("states/<int:state_id>/<int:pk>/questions/<int:pk2>/vote/", views.vote, name="vote"),
    path("states/<int:state_id>/<int:pk>/questions/<int:pk2>/results/", views.ResultsView.as_view(), name="results"),
]