from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    path("posts", views.PostsView.as_view(), name="posts"),
    path("post_detail/<str:post_id>", views.PostDetail.as_view(), name="post_detail"),
]
