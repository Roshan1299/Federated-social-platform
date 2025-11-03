from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from authors.models import Author, Post, Follow, Like, Comment, CommentLike


class Command(BaseCommand):
    help = 'Seed the database with 5 authors, posts, follows, comments and likes for local development'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing seeded users before creating')

    def handle(self, *args, **options):
        # support clearing existing seeded users/data
        if options.get('clear'):
            self.stdout.write('Clearing existing seeded users and related data...')
            names = ['admin', 'alice', 'bob', 'carol', 'dave']
            Author.objects.filter(username__in=names).delete()
            self.stdout.write('Cleared')

        base = getattr(settings, 'BASE_URL', None) or getattr(settings, 'SITE_URL', None) or 'http://localhost:8000'

        # Create 5 authors (idempotent)
        self.stdout.write('Creating authors...')
        authors = {}
        names = ['admin', 'alice', 'bob', 'carol', 'dave']
        for name in names:
            if name == 'admin':
                user, created = Author.objects.get_or_create(username='admin', defaults={'displayName': 'Admin User'})
                if created:
                    user.set_password('admin')
                user.is_active = True
                user.is_staff = True
                user.is_superuser = True
                user.save()
            else:
                user, created = Author.objects.get_or_create(username=name, defaults={'displayName': name.capitalize()})
                if created:
                    user.set_password('password')
                    user.save()
            # populate host and url
            user.host = base
            user.url = f"{base}/api/authors/{user.id}/"
            user.save()
            authors[name] = user
            self.stdout.write(f'  - {name} ({user.id})')

        admin = authors['admin']
        alice = authors['alice']
        bob = authors['bob']
        carol = authors['carol']
        dave = authors['dave']

        # Create follow relationships
        self.stdout.write('Creating follow relationships...')
        # Admin should be friends with all, but one user (exclude dave)
        for other in [alice, bob, carol]:
            Follow.objects.get_or_create(follower=admin, following=other)
            Follow.objects.get_or_create(follower=other, following=admin)

        # One user followed by everyone -> alice
        for follower in [admin, bob, carol, dave]:
            Follow.objects.get_or_create(follower=follower, following=alice)

        # One user follows everyone -> bob
        for following in [admin, alice, carol, dave]:
            Follow.objects.get_or_create(follower=bob, following=following)

        # Additional link: carol follows bob
        Follow.objects.get_or_create(follower=carol, following=bob)

        # Create posts for each author (public, unlisted, friends)
        self.stdout.write('Creating posts...')
        posts = {}
        for key, author in authors.items():
            posts[key] = {}
            p_public, _ = Post.objects.get_or_create(author=author, title=f'{author.displayName} Public', defaults={'content':'Public content', 'contentType':'text/plain', 'visibility':'PUBLIC', 'published': timezone.now()})
            p_public.source = f"{base}/api/authors/{author.id}/entries/{p_public.id}"
            p_public.origin = p_public.source
            p_public.save()
            posts[key]['public'] = p_public

            p_unlisted, _ = Post.objects.get_or_create(author=author, title=f'{author.displayName} Unlisted', defaults={'content':'Unlisted content', 'contentType':'text/plain', 'visibility':'PUBLIC_UNLISTED', 'published': timezone.now()})
            p_unlisted.source = f"{base}/api/authors/{author.id}/entries/{p_unlisted.id}"
            p_unlisted.origin = p_unlisted.source
            p_unlisted.save()
            posts[key]['unlisted'] = p_unlisted

            p_friends, _ = Post.objects.get_or_create(author=author, title=f'{author.displayName} Friends', defaults={'content':'Friends-only content', 'contentType':'text/plain', 'visibility':'FRIENDS', 'published': timezone.now()})
            p_friends.source = f"{base}/api/authors/{author.id}/entries/{p_friends.id}"
            p_friends.origin = p_friends.source
            p_friends.save()
            posts[key]['friends'] = p_friends

        # Create likes for public posts by everyone
        self.stdout.write('Creating likes for public posts by everyone...')
        all_authors = list(authors.values())
        for key, author_posts in posts.items():
            pub = author_posts['public']
            for liker in all_authors:
                Like.objects.get_or_create(author=liker, post=pub)

        # Create comments for public posts by everyone and like each comment by everyone
        self.stdout.write('Creating comments for public posts by everyone and liking them...')
        for key, author_posts in posts.items():
            pub = author_posts['public']
            for commenter in all_authors:
                c, _ = Comment.objects.get_or_create(post=pub, author=commenter, content=f'Comment by {commenter.username} on {pub.title}')
                for liker in all_authors:
                    CommentLike.objects.get_or_create(author=liker, comment=c)

        # Friends-only posts liked only by mutual friends
        self.stdout.write('Creating likes for friends-only posts by mutual friends...')
        for key, author_posts in posts.items():
            author = authors[key]
            friends_post = author_posts['friends']
            potential_friends = Follow.objects.filter(follower__in=all_authors, following=author)
            for f in potential_friends:
                if Follow.objects.filter(follower=author, following=f.follower).exists():
                    Like.objects.get_or_create(author=f.follower, post=friends_post)

        # Friends-only posts: comments only by mutual friends and comment-likes by mutual friends
        self.stdout.write('Creating comments for friends-only posts by mutual friends and liking them by mutual friends...')
        for key, author_posts in posts.items():
            author = authors[key]
            friends_post = author_posts['friends']
            potential_friends = Follow.objects.filter(follower__in=all_authors, following=author)
            mutual_followers = [f.follower for f in potential_friends if Follow.objects.filter(follower=author, following=f.follower).exists()]
            for commenter in mutual_followers:
                c, _ = Comment.objects.get_or_create(post=friends_post, author=commenter, content=f'Friend comment by {commenter.username} on {friends_post.title}')
                for liker in mutual_followers:
                    CommentLike.objects.get_or_create(author=liker, comment=c)

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
