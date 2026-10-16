from django.urls import path

from . import views

app_name = "alertas"

urlpatterns = [
    path("", views.AlertaListView.as_view(), name="lista"),
    path("<int:pk>/atendida/", views.MarcarAtendidaView.as_view(), name="atendida"),
]
