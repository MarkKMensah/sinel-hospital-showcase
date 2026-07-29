from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import View

from .models import Post


class PostsView(View):
    template_name = "blog/posts.html"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()[:100]
        posts = (
            Post.objects.filter(visible=True)
            .select_related("by")
            .order_by("-created_at", "-id")
        )
        if query:
            posts = posts.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(tags__icontains=query)
            )

        featured_post = None
        if not query:
            featured_post = posts.first()
            if featured_post:
                posts = posts.exclude(pk=featured_post.pk)
            if request.GET.get("page"):
                featured_post = None

        paginator = Paginator(posts, 6)
        page_obj = paginator.get_page(request.GET.get("page"))
        context = {
            "featured_post": featured_post,
            "posts": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "result_count": paginator.count,
        }
        return render(request, self.template_name, context)


class PostDetail(View):
    template_name = "blog/post_detail.html"

    def get(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(
            Post.objects.select_related("by"),
            id=post_id,
            visible=True,
        )
        context = {
            "post": post,
            "related_posts": (
                Post.objects.filter(visible=True)
                .exclude(pk=post.pk)
                .select_related("by")
                .order_by("-created_at", "-id")[:3]
            ),
        }
        return render(request, self.template_name, context)
