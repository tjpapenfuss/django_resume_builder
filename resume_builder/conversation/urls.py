"""
URL configuration for conversation app
"""

from django.urls import path
from . import views

app_name = 'conversation'

urlpatterns = [
    # API Endpoints
    path('start/', views.start_conversation, name='start_conversation'),
    path('<uuid:conversation_id>/message/', views.send_message, name='send_message'),
    path('<uuid:conversation_id>/history/', views.get_conversation_history, name='get_history'),
    path('<uuid:conversation_id>/complete/', views.complete_conversation, name='complete_conversation'),
    path('<uuid:conversation_id>/status/', views.get_conversation_status, name='get_status'),
    path('<uuid:conversation_id>/pause/', views.pause_conversation, name='pause_conversation'),
    path('', views.list_user_conversations, name='list_conversations'),
    
    # Test page
    path('test/', views.conversation_test_page, name='test_page'),
]