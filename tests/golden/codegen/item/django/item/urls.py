from django.urls import include, path

app_name = 'item'

urlpatterns = [
	path('', include('item.views.item.urls')),
]
