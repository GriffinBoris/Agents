from django.urls import path
from item.views.item import views

urlpatterns = [
	path('list/', views.ItemListView.as_view(), name='item-list'),
	path('create/', views.ItemCreateView.as_view(), name='item-create'),
	path('<int:item_id>/', views.ItemDetailView.as_view(), name='item-detail'),
	path('<int:item_id>/archive/', views.ItemArchiveView.as_view(), name='item-archive'),
]
