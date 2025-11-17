# Django shell script to test FQID routes using django.test.Client
# Run with: python3 manage.py shell < scripts/test_fqid_routes.py
import base64
import urllib.parse
from django.test import Client
from django.conf import settings
from authors.models import Comment, Like

client = Client()
# Use admin:admin credentials (change if different)
basic = 'Basic ' + base64.b64encode(b'admin:admin').decode()
headers = {'HTTP_AUTHORIZATION': basic}

base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
print('Using base_url=', base_url)

# Helper to print result
def do_get(path):
    full = path
    print('\nGET', full)
    resp = client.get(full, **headers)
    print('Status:', resp.status_code)
    # Print small snippet of response body (decoded)
    content = resp.content.decode('utf-8', errors='replace')
    snippet = content[:1000]
    print('Body snippet:', snippet)
    return resp

# Grab sample comment and like
c = Comment.objects.first()
l = Like.objects.first()
if not c:
    print('No Comment objects found; aborting tests')
else:
    print('Sample Comment:', c.id, 'origin=', c.origin)
if not l:
    print('No Like objects found; aborting tests')
else:
    print('Sample Like:', l.id, 'origin=', l.origin)

if c:
    enc_comment = urllib.parse.quote(c.origin, safe='')
    # Test /api/commented/{COMMENT_FQID}
    do_get(f'/api/commented/{enc_comment}')

    # Test /api/authors/<author_id>/entries/<entry_id>/comment/{COMMENT_FQID}
    post = c.post
    do_get(f'/api/authors/{post.author.id}/entries/{post.id}/comment/{enc_comment}')

    # Test /api/authors/<author_id>/entries/<entry_id>/comments/{COMMENT_FQID}/likes
    do_get(f'/api/authors/{post.author.id}/entries/{post.id}/comments/{enc_comment}/likes')

if l:
    enc_like = urllib.parse.quote(l.origin, safe='')
    # Test /api/liked/{LIKE_FQID}
    do_get(f'/api/liked/{enc_like}')

print('\nFinished FQID route tests')
