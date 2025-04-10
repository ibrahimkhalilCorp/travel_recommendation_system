from django.urls import path
from .views import IndexView, TravelRecommendationView, TopDistrictsView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('top-districts/', TopDistrictsView.as_view(), name='top_districts'),
    path('travel-recommendation/', TravelRecommendationView.as_view(), name='travel_recommendation'),
]