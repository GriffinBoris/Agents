from contact import views
from django.urls import path

app_name = 'contact'

urlpatterns = [
	path('list/', views.ContactListView.as_view(), name='contact-list'),
	path('create/', views.ContactCreateView.as_view(), name='contact-create'),
	path('<int:contact_id>/', views.ContactDetailView.as_view(), name='contact-detail'),
]
