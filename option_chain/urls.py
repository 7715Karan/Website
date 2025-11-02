from django.urls import path
from . import views

app_name = 'option_chain'



urlpatterns = [
    path('', views.home, name='home'),  # Main page
    path('derivatives/', views.option_chain_dashboard, name='option_chain_dashboard'),
    path('api/option-chain/<str:symbol>/', views.option_chain_api, name='option_chain_api'),
    path('view/option-chain/<str:symbol>/', views.option_chain_view, name='option_chain_view'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    ]