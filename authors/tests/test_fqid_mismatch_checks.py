# Django shell script to test FQID mismatch cases
# Run with: python3 manage.py shell < authors/tests/test_fqid_mismatch_checks.py
import base64
import urllib.parse
from django.test import Client
from django.conf import settings
from authors.models import Comment, Like, Author, Post

client = Client()
basic = 'Basic ' + base64.b64encode(b'admin:admin').decode()
headers = {'HTTP_AUTHORIZATION': basic}

print('Using base_url=', getattr(settings, 'BASE_URL', 'http://localhost:8000'))


def do_get(path):
    print('\nGET', path)
    resp = client.get(path, **headers)
    print('Status:', resp.status_code)
    content = resp.content.decode('utf-8', errors='replace')
    print('Body snippet:', content[:800])
    return resp

c = Comment.objects.first()
l = Like.objects.first()

if not c:
    print('No Comment objects found; aborting mismatch tests')
else:
    print('Sample Comment:', c.id, 'origin=', c.origin)

if not l:
    print('No Like objects found; aborting mismatch tests')
else:
    print('Sample Like:', l.id, 'origin=', l.origin)

if c:
    enc_comment = urllib.parse.quote(c.origin, safe='')
    post = c.post
    correct_author_id = post.author.id
    correct_entry_id = post.id

    # find a different author (for mismatch) or use a fake uuid
    wrong_author = Author.objects.exclude(id=correct_author_id).first()
    wrong_author_id = wrong_author.id if wrong_author else '00000000-0000-0000-0000-000000000000'

    # find a different post (for mismatch)
    wrong_entry = Post.objects.exclude(id=correct_entry_id).first()
    wrong_entry_id = wrong_entry.id if wrong_entry else '00000000-0000-0000-0000-000000000000'

    print('\n-- Correct comment FQID under matching author/entry (expect 200)')
    do_get(f'/api/authors/{correct_author_id}/entries/{correct_entry_id}/comment/{enc_comment}')

    print('\n-- Mismatch: same comment FQID but wrong author (expect 404)')
    do_get(f'/api/authors/{wrong_author_id}/entries/{correct_entry_id}/comment/{enc_comment}')

    print('\n-- Mismatch: same comment FQID but wrong entry (expect 404)')
    do_get(f'/api/authors/{correct_author_id}/entries/{wrong_entry_id}/comment/{enc_comment}')

if l:
    # test like UUID under wrong author (single-like-by-uuid route)
    print('\n-- Correct like UUID under matching author (expect 200)')
    do_get(f'/api/authors/{l.author.id}/liked/{l.id}')

    wrong_author_for_like = Author.objects.exclude(id=l.author.id).first()
    wrong_author_for_like_id = wrong_author_for_like.id if wrong_author_for_like else '00000000-0000-0000-0000-000000000000'

    print('\n-- Mismatch: like UUID requested under different author (expect 404)')
    do_get(f'/api/authors/{wrong_author_for_like_id}/liked/{l.id}')

print('\nFinished FQID mismatch tests')
