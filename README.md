# The Team
| Name | CCID | Email |
| ----| ----- | ------|
Azim | imukith | imukith@ualberta.ca
Roshan | banisett | banisett@ualberta.ca
Bhuvan | bhuvanac | bhuvanac@ualberta.ca
Byungkook | byungkoo | byungkoo@ualberta.ca
Liam | lhouston | lhouston@ualberta.ca
Tanmay | tlad | tlad@ualberta.ca
Uday | udaymeht | udaymeht@ualberta.ca

[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/etkNZkSE)
CMPUT404-project-socialdistribution
===================================

CMPUT404-project-socialdistribution

See [the web page](https://uofa-cmput404.github.io/general/project.html) for a description of the project.

Make a distributed social network!

## Running the Project Locally

Follow these steps to set up and run the development server. It is recommended to run these commands within an activated virtual environment.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Apply Database Migrations:**
    This command creates and updates the database schema.
    ```bash
    python manage.py migrate
    ```

3.  **Create a Superuser (for Admin Access):**
    ```bash
    python manage.py createsuperuser
    ```

4.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```
    The server will be running at `http://127.0.0.1:8000/`.

## Running Tests

To run the project tests, use the following command:

```bash
python3 manage.py test authors.tests
```

This will execute all tests within the authors application.

## License

* Choose an OSI approved license, name it here, and copy the license text to a file called `LICENSE`.

## Copyright

The authors claiming copyright, if they wish to be known, can list their names here...

* 

## Security Features

This application implements several security measures to protect user data and prevent common web vulnerabilities:

### API Access Control
- **Visibility-Based Access:** API endpoints respect post visibility settings:
  - PUBLIC posts: Accessible to all users
  - PUBLIC_UNLISTED posts: Accessible to all users
  - FRIENDS posts: Accessible only to post author and mutual friends
- **Authentication Requirements:** Sensitive endpoints require proper user authentication
- **Authorization Checks:** Users can only modify their own content

### CSRF Protection
- All forms include CSRF tokens to prevent cross-site request forgery attacks
- API endpoints follow Django's built-in CSRF protection mechanisms
- Session-based authentication ensures only legitimate users can access protected resources

### XSS Prevention
- UI and API endpoints communicate through the same server domain
- Proper input sanitization and output encoding for all user-generated content
- Content Security Policy implemented via Django's security middleware

### Distributed System Security
- Local API endpoints properly validate cross-node requests
- Visibility rules are enforced consistently across UI and API layers
- Proper authentication for both local UI interactions and distributed node communications

## GitHub Activity Integration

This application supports automatically fetching and converting public GitHub activity to posts.

### Fetch GitHub Activity

To manually fetch GitHub activity for all authors with GitHub profiles, run:

```bash
python manage.py fetch_github_activity
```

This command will:
- Fetch public GitHub events for all authors who have a GitHub URL set in their profile
- Convert new GitHub activities to public posts
- Track the last processed event to avoid duplicates
- Only create posts for new activity since the last command run

### Automatic GitHub Activity Fetching

For automatic fetching, you can set up a scheduled task (cron job) to run the command periodically:

```bash
# Run every 10 minutes
*/10 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py fetch_github_activity
```

### Supported GitHub Event Types

The system currently supports conversion of these GitHub event types to posts:
- PushEvent (commits pushed to repositories)
- PullRequestEvent (pull requests opened, closed, merged)
- IssuesEvent (issues opened, closed, etc.)
- WatchEvent (starring repositories)
- ForkEvent (forking repositories)
- CreateEvent (creating repositories, branches, tags)
- DeleteEvent (deleting branches, tags)
- Other event types (with generic handling)

---

## API Documentation

This section details the REST API endpoints for the Social Distribution project.

---

### Get a Single Author's Profile

Retrieves the public profile information of a single author.

*   **URL:** `/api/authors/{AUTHOR_ID}/`
*   **Method:** `GET`
*   **URL Params:**
    *   `AUTHOR_ID` (required): The UUID of the author to retrieve.
*   **Authentication Required:** Yes (local session auth or HTTP Basic Auth for remote)
*   **Access Level:** [local]

#### Example Request:

```bash
curl http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
```

#### Example Response:

*   **Code:** `200 OK`
*   **Content:**

```json
{
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
    "host": "http://127.0.0.1:8000",
    "displayName": "Roshan123",
    "github": "http://github.com/Roshan2",
    "profileImage": "https://example.com/path/to/image.png",
    "web": "http://127.0.0.1:8000/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/"
}
```

#### Example Request
```bash
curl \
  https://darkblue-xxxxxxxxxxxx.herokuapp.com/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
```

#### Example Response:
*  **Code:** `401 Unauthorized`
```json
{
    "detail": "Authentication required"
}
```

#### Example Request
```bash
curl -u username:password \
  https://darkblue-xxxxxxxxxxxx.herokuapp.com/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
```
#### Example Response:
*  **Code:** `404 Not Found`
```json
{
    "error": "Author not found."
}
```

#### Response Fields:

| Field          | Type   | Description                                                                 | Example                                                              |
|----------------|--------|-----------------------------------------------------------------------------|----------------------------------------------------------------------|
| `type`         | string | The type of the object. Always "author".                                    | `"author"`                                                           |
| `id`           | URL    | The fully qualified API URL for this author. This is their unique identifier. | `"http://127.0.0.1:8000/api/authors/..."`                             |
| `host`         | URL    | The hostname of the node where the author is registered.                    | `"http://127.0.0.1:8000"`                                            |
| `displayName`  | string | The author's preferred display name.                                        | `"Roshan123"`                                                         |
| `github`       | URL    | The URL to the author's GitHub profile. Can be null.                        | `"http://github.com/Roshan2"`                                        |
| `profileImage` | URL    | A URL to an image for the author's profile picture. Can be null.            | `"https://example.com/path/to/image.png"`                            |
| `web`          | URL    | The fully qualified URL to the author's web-based profile page.             | `"http://127.0.0.1:8000/authors/..."`                                 |

### Get Author by Fully Qualified ID (FQID)

Retrieves author information using their Fully Qualified ID (FQID), which is the complete URL of the author's profile on any node.

*  **URL:** `/api/authors/{AUTHOR_FQID}/`
*  **Method:** `GET`
*  **URL Params:**
    *  `AUTHOR_FQID` (required): The percent-encoded full URL of the author to retrieve.
*  **Authentication Required:** Yes (HTTP Basic Auth required)
*  **Access Level:** [remote]

**Example Request - Bash:**
```bash
# URL encoding: http://other-node.com/api/authors/abc123/
# becomes: http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fabc123%2F

curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fabc123%2F/"
```

**Response:** Same format as UUID-based single author request

**Notes:**
- FQID must be properly percent-encoded
- Returns 404 if the FQID doesn't match any author on this node

---

### Get All Author Profiles
Retrieves the public profile information of all authors.

*   **URL:** `/api/authors/`
*   **Method:** `GET`
*   **Autentication Required:** Yes (HTTP Basic Auth for remote access, session auth or HTTP Basic for local)
*   **Access Level:** [local, remote]

#### Example Request:

```bash
curl -u username:password \
  https://darkblue-xxxxxxxxxxxx.herokuapp.com/api/authors/
```
#### Example Response:

*   **Code:** `200 OK`
*   **Content:**
```json
[
  {
    "type": "author",
    "id": "http://127.0.0.1:8000/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "host": null,
    "displayName": "Dark Blue",
    "github": null,
    "profileImage": "user_images/me_voCfOw7.jpg",
    "web": "http://127.0.0.1:8000/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
  },
  {
    "type": "author",
    "id": "http://127.0.0.1:8000/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
    "host": "http://127.0.0.1:8000",
    "displayName": "Liam Houston",
    "github": "https://www.github.com/liamhouston",
    "profileImage": "user_images/profile_pic.jpg",
    "web": "http://127.0.0.1:8000/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/"
  }
]
```

#### Example Request
```bash
curl https://darkblue-xxxxxxxxxxxx.herokuapp.com/api/authors/
```
#### Example Response:
*  **Code:** `401 Unauthorized`
```
"Authentication required"
```

#### Response Fields:
Response returns an array of JSON objects.

| Field          | Type   | Description                                                                 | Example                                                              |
|----------------|--------|-----------------------------------------------------------------------------|----------------------------------------------------------------------|
| `type`         | string | The type of the object. Always "author".                                    | `"author"`                                                           |
| `id`           | URL    | The fully qualified API URL for this author. This is their unique identifier. | `"http://127.0.0.1:8000/api/authors/..."`                             |
| `host`         | URL    | The hostname of the node where the author is registered.                    | `"http://127.0.0.1:8000"`                                            |
| `displayName`  | string | The author's preferred display name.                                        | `"Liam Houston"`                                                         |
| `github`       | URL    | The URL to the author's GitHub profile. Can be null.                        | `"http://github.com/liamhouston"`                                        |
| `profileImage` | URL    | A URL to an image for the author's profile picture. Can be null.            | `"https://example.com/path/to/image.png"`                            |
| `web`          | URL    | The fully qualified URL to the author's web-based profile page.             | `"http://127.0.0.1:8000/authors/..."`                                 |


### Create a New Post

Creates a new post for an authenticated author.

*   **URL:** `/api/posts/`
*   **Method:** `POST`
*   **Authorization:** Required (user must be logged in)
*   **Content-Type:** `application/json`
*   **Request Body:**
    *   `title` (required): The title of the post
    *   `description` (optional): Short description or summary of the post
    *   `content` (required): The actual content of the post
    *   `contentType` (required): The type of content ('text/plain', 'text/markdown', 'image/png', etc.)
    *   `visibility` (required): The visibility of the post ('PUBLIC', 'PUBLIC_UNLISTED', 'FRIENDS')
    
    *   `image` (optional): URL to an image if the post includes one

#### Example Request:

```bash
curl -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "My New Post",
    "description": "A short description",
    "content": "Hello world!",
    "contentType": "text/plain",
    "visibility": "PUBLIC",
    
  }'
```

#### Example Response:

*   **Code:** `201 Created`
*   **Content:**

```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
    "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
        "host": "http://127.0.0.1:8000",
        "displayName": "Roshan123",
        "url": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
        "github": "http://github.com/Roshan2",
        "profileImage": "https://example.com/path/to/image.png"
    },
    "title": "My New Post",
    "description": "A short description",
    "content": "Hello world!",
    "contentType": "text/plain",
    "visibility": "PUBLIC",
    "published": "2023-01-01T00:00:00Z",
    "updated": "2023-01-01T00:00:00Z"
}
```

### Get a Single Post

Retrieves the details of a single post by its ID with appropriate visibility-based access controls.

*   **URL:** `/api/posts/{POST_ID}/`
*   **Method:** `GET`
*   **URL Params:**
    *   `POST_ID` (required): The UUID of the post to retrieve.
*   **Access Controls:**
    *   **PUBLIC posts:** Accessible to all users
    *   **PUBLIC_UNLISTED posts:** Accessible to all users 
    *   **FRIENDS posts:** Accessible only to the post author and mutual friends (both authors must follow each other)

#### Example Request:

```bash
curl http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
```

#### Example Response: 
*   **Code:** `200 OK`
*   **Content:**
```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
    "author": {
        "type": "author",
        "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
        "host": "http://127.0.0.1:8000",
        "displayName": "Roshan123",
        "url": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
        "github": "http://github.com/Roshan2",
        "profileImage": "https://example.com/path/to/image.png"
    },
    "title": "My Post",
    "description": "A short description",
    "content": "Hello world!",
    "contentType": "text/plain",
    "visibility": "PUBLIC",
    "published": "2023-01-01T00:00:00Z",
    "updated": "2023-01-01T00:00:00Z"
}
```

#### Example Response (Access Denied):
*   **Code:** `403 Forbidden` - When trying to access a FRIENDS post without proper permissions

#### Post Response Fields:

| Field          | Type   | Description                                                                 | Example                                                              |
|----------------|--------|-----------------------------------------------------------------------------|----------------------------------------------------------------------|
| `type`         | string | The type of the object. Always "post".                                     | `"post"`                                                             |
| `id`           | URL    | The fully qualified API URL for this post. This is the unique identifier.    | `"http://127.0.0.1:8000/api/posts/..."`                             |
| `author`       | object | The author object containing information about the post creator.            | See author response format above                                     |
| `title`        | string | The title of the post.                                                      | `"My New Post"`                                                      |
| `description`  | string | A short description or summary of the post. Can be null.                    | `"A short description"`                                              |
| `content`      | string | The actual content of the post.                                             | `"Hello world!"`                                                     |
| `contentType`  | string | The content type of the post.                                               | `"text/plain"`, `"text/markdown"`, `"image/png"`, etc.              |
| `visibility`   | string | The visibility setting of the post.                                         | `"PUBLIC"`, `"PUBLIC_UNLISTED"`, `"FRIENDS"`                         |
| `published`    | datetime | When the post was published (ISO 8601 format).                              | `"2023-01-01T00:00:00Z"`                                            |
| `updated`      | datetime | When the post was last updated (ISO 8601 format).                           | `"2023-01-01T00:00:00Z"`                                            |
| `image`        | URL    | URL to the post image (if applicable). Can be null.                         | `"http://127.0.0.1:8000/media/post_images/post_image.png"`          |

### Edit a Post

Allows an authenticated author to edit their own post.

*   **URL:** `/api/posts/{POST_ID}/edit/`
*   **Method:** `PUT` or `PATCH`
*   **Authorization:** Required (user must be logged in and be the post author)
*   **Content-Type:** `application/json`
*   **URL Params:**
    *   `POST_ID` (required): The UUID of the post to edit.
    *   `AUTHOR_ID` (Required): UUID of author required)

#### Example Request:

```bash
curl -X PUT http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/edit/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Updated Title",
    "description": "Updated Description",
    "content": "Updated post content",
    "contentType": "text/plain",
    "visibility": "FRIENDS"
  }'
```


#### Example Response:

*   **Code:** `201 Created`
*   **Content:**
```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
    "title": "Updated Title",
    "description": "Updated Description",
    "content": "Updated post content",
    "contentType": "text/plain",
    "visibility": "FRIENDS",
    "updated": "2025-10-17T00:00:00Z"
}
```


### Delete a Post

Deletes an existing post. Only the post's author can delete it.

*   **URL:** `/api/posts/{POST_ID}/delete/`
*   **Method:** `POST`
*   **Authorization:** Required (user must be logged in as the author of the post
*   **URL Params:** 
    * `POST_ID` (required): The UUID of the post to edit.
    * `AUTHOR_ID` (Required): UUID of author required)

#### Example Rquest:
```bash
curl -X DELETE http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/delete/ \
  -H "Authorization: Bearer <token>"
```

#### Example Response:
*  **Code:** 204 No Content


### Follow Request
Sends a follow request from one author to another (must be approve/denied by follow receiver - NEXT SECTION)

*   **URL:** `/api/authors/{AUTHOR_ID}/follow/`
*   **Method:** `POST`
*   **Authorization:** Required (user must be logged in)
*   **URL Params:** AUTHOR_ID (UUID of author required)

#### Example Rquest:
```bash
curl -X POST http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/follow/ \
  -H "Authorization: Bearer <token>"
```

#### Example Response:
*  **Code:** 201 Created
*  **Content:**
```json
{
    "type": "followRequest",
    "sender": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
    "receiver": "http://127.0.0.1:8000/api/authors/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
    "status": "PENDING"
}
```


### Approve/Deny a Follow Request
Allows an author to approve or deny a pending follow request.

*   **URL:** `/api/follow-requests/{REQUEST_ID}/`
*   **Method:** `PATCH`
*   **Authorization:** Required (receiver must be logged in)
*   **Content-Type:** application/json
*   **URL Params:** REQUEST_ID (UUID of the follow request required)

#### APPROVE Example Rquest:
```bash
curl -X PATCH http://127.0.0.1:8000/api/follow-requests/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{ "status": "APPROVED" }'
```

#### DENY Example Rquest:
```bash
curl -X PATCH http://127.0.0.1:8000/api/follow-requests/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{ "status": "DENIED" }'
```

#### Example Response:
*  **Code:** 200 OK
*  **Content:**
```json
{
    "type": "followRequest",
    "sender": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
    "receiver": "http://127.0.0.1:8000/api/authors/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
    "status": "APPROVED"
}
```
### Like or Unlike a Post
Toggles a like on a post by the authenticated user.

*   **URL:** `/api/posts/{POST_ID}/like/`
*   **Method:** `POST`
*   **Authorization:** Required (user must be logged in)
*   **URL Params:**
    *   `POST_ID` (required): The UUID of the post to like or unlike.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/like/ \
  -H "Authorization: Bearer <token>"
```
#### Example Response:
*  **Code:** 200 OK
*  **Content:**
```json
{
  "liked": true,
  "count": 5
}
```

### View Post Likes

Returns a list of authors who liked a given post.

* **URL:** `/api/posts/{POST_ID}/likes/`
* **Method:** `GET`
* **Authorization:** Required (only post author and followers can view likes on friends-only posts)
* **URL Params:**
  * `POST_ID` (required): The UUID of the post to retrieve likes for.

#### Example Request:
```bash
curl http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/likes/ \
  -H "Authorization: Bearer <token>"
```
#### Example Response:
*  **Code:** 200 OK
*  **Content:**
```json
{
  "type": "likes",
  "post": "http://127.0.0.1:8000/api/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
  "total_likes": 2,
  "items": [
    {
      "type": "like",
      "author": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
      "displayName": "DarkBlue",
      "created_at": "2025-10-18T01:30:00Z"
    },
    {
      "type": "like",
      "author": "http://127.0.0.1:8000/api/authors/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
      "displayName": "DarkBlue2",
      "created_at": "2025-10-18T01:32:00Z"
    }
  ]
}

```

### Add a Comment to a Post

Creates a comment on a specific post.

* **URL:** `/api/posts/{POST_ID}/comments/add/`  
* **Method:** `POST`  
* **Authorization:** Required (user must be logged in)  
* **URL Params:**  
  * `POST_ID` (required): The UUID of the post to comment on.  
* **Form Data:**  
  * `content` (string, required): Text of the comment.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/posts/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/comments/add/ \
  -H "Authorization: Bearer <token>" \
  -F "content=Nice post! 👏"
```
#### Example Response:
*  **Code:** 302 Found
*  **Content:**
```json
{
  "type": "comment",
  "id": "http://127.0.0.1:8000/api/comments/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
  "author": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
  "post": "http://127.0.0.1:8000/api/posts/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
  "content": "Nice post! 👏",
  "created_at": "2025-10-18T03:25:00Z",
  "like_count": 0
}
```

### Like or Unlike a Comment

Toggles a like on a specific comment.

* **URL:** `/api/comments/{COMMENT_ID}/like/`  
* **Method:** `POST`  
* **Authorization:** Required (user must be logged in)  
* **URL Params:**  
  * `COMMENT_ID` (required): The UUID of the comment to like or unlike.

#### Example Request:
```bash
curl -X POST http://127.0.0.1:8000/comments/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/like/ \
  -H "Authorization: Bearer <token>"
```
#### Example Response:
*  **Code:** 302 Found
*  **Content:**
```json
{
  "type": "commentLike",
  "author": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
  "comment": "http://127.0.0.1:8000/api/comments/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
  "liked": true,
  "like_count": 3,
  "created_at": "2025-10-18T03:40:00Z"
}
```

### Followers API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/followers`

**Purpose:** Retrieve a list of all authors who are following a specific author.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author whose followers you want | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Example Request - Bash:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/followers
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "followers" | `"followers"` |
| `followers` | array | Yes | Array of author objects representing followers | See Author Object fields |

**Follower Author Object Fields (within `followers` array):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "author" | `"author"` |
| `id` | string (URL) | Yes | No | Follower's FQID | `"https://other-node.com/api/authors/xyz789/"` |
| `host` | string (URL) | Yes | No | Follower's home node URL | `"https://other-node.com"` |
| `displayName` | string | Yes | No | Follower's display name | `"Jane Doe"` |
| `url` | string (URL) | Yes | No | Follower's API URL | `"https://other-node.com/api/authors/xyz789/"` |
| `github` | string (URL) | No | Yes | Follower's GitHub URL | `"https://github.com/janedoe"` |
| `profileImage` | string (URL) | No | Yes | Follower's profile image URL | `"https://other-node.com/media/jane.jpg"` |
| `web` | string (URL) | Yes | No | Follower's web profile URL | `"https://other-node.com/authors/xyz789/"` |

**Success Response - Example (200 OK):**
```json
{
  "type": "followers",
  "followers": [
    {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Liam Houston",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
      "github": "https://github.com/liamhouston",
      "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/liam.jpg",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/"
    },
    {
      "type": "author",
      "id": "https://other-node.herokuapp.com/api/authors/abc-def-123/",
      "host": "https://other-node.herokuapp.com",
      "displayName": "Remote User",
      "url": "https://other-node.herokuapp.com/api/authors/abc-def-123/",
      "github": null,
      "profileImage": "https://other-node.herokuapp.com/media/remote.jpg",
      "web": "https://other-node.herokuapp.com/authors/abc-def-123/"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 401 Unauthorized | No authentication provided or invalid credentials | `{"detail": "Authentication required"}` |
| 404 Not Found | Author with specified UUID does not exist | `{"detail": "Not found."}` |

**Notes:**
- Followers can be from the same node or different nodes
- Useful for determining who should receive posts in the inbox model

---

### Following API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/following`

**Purpose:** Retrieve a list of authors that a local author is following.

**Authentication Required:** Yes (session auth — only the local author may call this endpoint)

**Access Level:** [local]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author whose following list you want | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Success Response - Example (200 OK):**
```json
{
  "type": "following",
  "items": [ /* array of author objects (same shape as Author object in Followers response) */ ]
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 401 Unauthorized | No authentication provided or invalid credentials |
| 403 Forbidden | Requesting user is not the local author |

---

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID}`

**Purpose:** Check if the local author is following a given foreign author. The `FOREIGN_AUTHOR_FQID` must be percent-encoded.

**Authentication Required:** Yes (session auth — only the local author may call this endpoint)

**Success Response:**
- `200 OK` with the author object if the local author follows the target
- `404 Not Found` if not following or target not resolvable

---

#### URL: `PUT /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID}`

**Purpose:** Create a follow request from the local author to the specified target author. Behavior differs for local vs remote targets:
- If the target resolves to a local author on this node and is not already followed, a local `FollowRequest` is created with status `PENDING`.
- If the target resolves to a remote author (different host), the server sends a `follow` activity to the remote author's inbox. The activity's `actor` is the local author object and the `object` is the target author object (full author JSON). On success the local node records a `Follow` immediately referencing the remote author record.

**Authentication Required:** Yes (session auth — only the local author may call this endpoint)

**Success Responses:**
- `201 Created` when a new follow request is created or successfully delivered to remote inbox
- `200 OK` when a follow request already exists

**Error Responses:**
- `401 Unauthorized` when not authenticated
- `403 Forbidden` when acting as a different author
- `404 Not Found` when the FQID cannot be resolved locally
- `502 Bad Gateway` when a network error occurs while sending to a remote inbox
- Any non-2xx response returned from the remote inbox will be forwarded (same status code)

---

#### URL: `DELETE /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID}`

**Purpose:** Unfollow a target author. Only the local author may call this endpoint.

**Authentication Required:** Yes (session auth — only the local author may call this endpoint)

**Success Responses:**
- `204 No Content` when an existing follow relationship is removed

**Error Responses:**
- `401 Unauthorized` when not authenticated
- `403 Forbidden` when acting as a different author
- `404 Not Found` when there is no follow relationship to remove

---

### Follow Requests API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/follow_requests`

**Purpose:** Return pending follow requests targeting the specified local author.

**Authentication Required:** Yes (session auth — only the local author may call this endpoint)

**Access Level:** [local]

**Success Response - Example (200 OK):**
```json
{
  "type": "follow_requests",
  "items": [
    {
      "id": "<follow-request-id>",
      "sender": { /* author object for the requester */ },
      "status": "PENDING",
      "created_at": "2025-10-17T03:40:00Z"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 401 Unauthorized | No authentication provided or invalid credentials |
| 403 Forbidden | Requesting user is not the local author |


#### URL: `GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}`

**Purpose:** Check if a specific foreign author is following another author.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author being followed | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `FOREIGN_AUTHOR_FQID` | string (URL-encoded) | Yes | Percent-encoded FQID of the potential follower | `http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fxyz789%2F` |

**Example Request 1 - Check if Following:**
```bash
# Checking if http://other-node.com/api/authors/xyz789/ follows local author
# URL encode the FQID: http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fxyz789%2F

curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/followers/http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fxyz789%2F"
```

**Response Fields (if following):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "author" | `"author"` |
| `id` | string (URL) | Yes | No | Follower's FQID | `"http://other-node.com/api/authors/xyz789/"` |
| `host` | string (URL) | Yes | No | Follower's home node | `"http://other-node.com"` |
| `displayName` | string | Yes | No | Follower's display name | `"Remote User"` |
| `url` | string (URL) | Yes | No | Follower's API URL | `"http://other-node.com/api/authors/xyz789/"` |
| `github` | string (URL) | No | Yes | Follower's GitHub URL | `"https://github.com/remoteuser"` |
| `profileImage` | string (URL) | No | Yes | Follower's profile image | `"http://other-node.com/media/remote.jpg"` |
| `web` | string (URL) | Yes | No | Follower's web profile | `"http://other-node.com/authors/xyz789/"` |

**Success Response - Is Following (200 OK):**
```json
{
  "type": "author",
  "id": "http://other-node.com/api/authors/xyz789/",
  "host": "http://other-node.com",
  "displayName": "Remote User",
  "url": "http://other-node.com/api/authors/xyz789/",
  "github": "https://github.com/remoteuser",
  "profileImage": "http://other-node.com/media/remote.jpg",
  "web": "http://other-node.com/authors/xyz789/"
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 404 Not Found | Foreign author is NOT following | No follow relationship or author doesn't exist |
| 401 Unauthorized | Authentication required | No/invalid credentials |

**Notes:**
- This is the recommended way to check if a follow request was accepted
- Useful for implementing friends detection (check both directions)

---

### Follow Request API

#### URL: `POST /api/authors/{AUTHOR_SERIAL}/inbox`

**Purpose:** Send a follow request from one author to another through the inbox mechanism.

**Authentication Required:** Yes (HTTP Basic Auth for remote access)

**Access Level:** [remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author being followed (receives the request) | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Request Body - Follow Object:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, must be "follow" | `"follow"` |
| `summary` | string | No | Yes | Human-readable description of the follow request | `"Greg wants to follow Lara"` |
| `actor` | object | Yes | No | Author object of the person initiating the follow (follower) | See Actor Object fields |
| `object` | object | Yes | No | Author object of the person being followed | See Object fields |

**Actor/Object Author Fields:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "author" | `"author"` |
| `id` | string (URL) | Yes | No | Author's FQID | `"https://node-a.com/api/authors/111/"` |
| `host` | string (URL) | Yes | No | Author's home node URL | `"https://node-a.com"` |
| `displayName` | string | Yes | No | Author's display name | `"Greg Johnson"` |
| `url` | string (URL) | Yes | No | Author's API URL (same as id) | `"https://node-a.com/api/authors/111/"` |
| `github` | string (URL) | No | Yes | Author's GitHub profile URL | `"https://github.com/gjohnson"` |
| `profileImage` | string (URL) | No | Yes | Author's profile image URL | `"https://i.imgur.com/k7XVwpB.jpeg"` |
| `web` | string (URL) | Yes | No | Author's HTML profile page URL | `"https://node-a.com/authors/111/"` |

**Example Request 1 - Basic Follow Request:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "follow",
    "summary": "Greg wants to follow Lara",
    "actor": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29c12e8f97bcbbd34cc908f1baba40658e/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29c12e8f97bcbbd34cc908f1baba40658e/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "object": {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Lara Croft",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "github": "https://github.com/laracroft",
      "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/lara"
    }
  }'
```

**Example Request 2 - Minimal Follow Request:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "follow",
    "actor": {
      "type": "author",
      "id": "https://remote-node.com/api/authors/abc123/",
      "host": "https://remote-node.com",
      "displayName": "Remote User",
      "url": "https://remote-node.com/api/authors/abc123/",
      "web": "https://remote-node.com/authors/abc123/"
    },
    "object": {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Liam Houston",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/"
    }
  }'
```

**Success Response (201 Created):**
```json
{
  "status": "Follow request received",
  "message": "Follow request has been added to the inbox"
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 400 Bad Request | Invalid request format | Missing required fields or incorrect JSON structure |
| 401 Unauthorized | Authentication required | No/invalid credentials provided |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist on this node |

**Notes:**
- The `summary` field is optional but helpful for logging/debugging

**Checking if Follow Was Accepted:**
- Use the Followers API: `GET /api/authors/{AUTHOR_ID}/followers/{FOLLOWER_FQID}`
- Returns 200 if following, 404 if not following

---

### Entries API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/entries/`

**Purpose:** Retrieve a paginated list of recent posts/entries created by a specific author.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**Pagination:** Yes (1-based indexing)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author whose posts to retrieve | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Query Parameters:**

| Parameter | Type | Required | Default | Description | Example |
|-----------|------|----------|---------|-------------|---------|
| `page` | integer | No | 1 | Page number to retrieve (1-indexed) | `page=2` |
| `size` | integer | No | 10 | Number of entries per page | `size=20` |

**Visibility Rules:**

| User Type | Can See |
|-----------|---------|
| Not authenticated | Only PUBLIC entries |
| Authenticated as the author | All entries (PUBLIC, FRIENDS, PUBLIC_UNLISTED) |
| Authenticated as follower | PUBLIC + PUBLIC_UNLISTED entries |
| Authenticated as friend (mutual follow) | All entries (PUBLIC, FRIENDS, PUBLIC_UNLISTED) |
| Authenticated as remote node | Should not typically happen (nodes push to inbox instead) |

**Example Request 1 - Basic:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/
```

**Example Request 2 - With Pagination:**
```bash
curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/?page=2&size=5"
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "posts" | `"posts"` |
| `page` | integer | Yes | Current page number | `1` |
| `size` | integer | Yes | Number of items per page | `10` |
| `count` | integer | Yes | Total number of entries available | `42` |
| `src` | array | Yes | Array of post objects | See Post Object fields |

**Post Object Fields (within `src` array):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "post" | `"post"` |
| `id` | string (URL) | Yes | No | Post's FQID (unique identifier across all nodes) | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/.../entries/abc123"` |
| `author` | object | Yes | No | Author object who created the post | See Author Object fields |
| `title` | string | Yes | No | Post title | `"My First Post"` |
| `source` | string (URL) | Yes | No | Where the post originally came from | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/.../entries/abc123"` |
| `origin` | string (URL) | Yes | No | Original source if post was shared | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/.../entries/abc123"` |
| `description` | string | No | No | Brief description or summary | `"This is my first post about web development"` |
| `contentType` | string | Yes | No | Content type of the post | `"text/plain"`, `"text/markdown"`, `"image/png;base64"` |
| `content` | string | Yes | No | The actual content of the post | `"Hello world!"` or base64 image data |
| `visibility` | string | Yes | No | Who can see this post | `"PUBLIC"`, `"FRIENDS"`, `"PUBLIC_UNLISTED"` |
| `published` | string (ISO 8601) | Yes | No | When the post was first published | `"2025-10-31T14:30:00Z"` |
| `count` | integer | Yes | No | Number of comments on this post | `5` |
| `comments` | string (URL) | Yes | No | URL to get comments for this post | `"https://.../api/authors/.../entries/abc123/comments"` |
| `commentsSrc` | object | No | No | Embedded comments data (first page) | See CommentsSrc Object |
| `image` | string (URL) | No | Yes | URL to image if post has one | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/post_images/img.jpg"` |

**Success Response - Example (200 OK):**
```json
{
  "type": "posts",
  "page": 1,
  "size": 10,
  "count": 25,
  "src": [
    {
      "type": "post",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Dark Blue",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "github": "https://github.com/darkblue",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
      },
      "title": "An entry title about web dev",
      "source": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "origin": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "description": "This post discusses web development",
      "contentType": "text/plain",
      "content": "Hello everyone! This is my first post about web development.",
      "visibility": "PUBLIC",
      "published": "2025-10-31T14:30:00Z",
      "count": 3,
      "comments": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments",
      "commentsSrc": {
        "type": "comments",
        "page": 1,
        "size": 5,
        "post": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments",
        "comments": []
      }
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | No/invalid credentials |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist |

**Pagination Behavior:**
- If `page` exceeds available pages, returns empty `src` array
- Default page size is 10 entries
- Maximum recommended page size is 50 entries
- Posts are ordered by `published` date (newest first)

**Content Type Notes:**

| ContentType | Description | Content Field Contains |
|-------------|-------------|------------------------|
| `text/plain` | Plain text | UTF-8 text, newlines preserved |
| `text/markdown` | CommonMark markdown | Markdown-formatted text |
| `image/png;base64` | PNG image | Base64-encoded PNG data |
| `image/jpeg;base64` | JPEG image | Base64-encoded JPEG data |
| `application/base64` | Generic binary | Base64-encoded binary data |

**Notes:**
- Only non-deleted posts are returned
- Visibility filtering is automatic based on authentication
- Posts include embedded author information for efficiency
- The `commentsSrc` provides first page of comments inline (reduces API calls)
- For image posts, the `content` field contains base64-encoded image data
- The `image` field (if present) provides a direct URL to the image file

---

#### URL: `POST /api/authors/{AUTHOR_SERIAL}/entries/`

**Purpose:** Create a new post/entry for a specific author.

**Authentication Required:** Yes (MUST be authenticated as the author)

**Access Level:** [local]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author creating the post | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Request Body Fields:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `title` | string | Yes | No | Post title | `"My New Post"` |
| `description` | string | No | Yes | Brief description | `"A post about web dev"` |
| `content` | string | Yes | No | Post content (text or base64 image) | `"Hello world!"` |
| `contentType` | string | Yes | No | Content MIME type | `"text/plain"`, `"text/markdown"`, `"image/png;base64"` |
| `visibility` | string | Yes | No | Who can see this post | `"PUBLIC"`, `"FRIENDS"`, `"PUBLIC_UNLISTED"` |
| `image` | file | No | Yes | Image file (if uploading via multipart) | Binary image data |

**Example Request 1 - Text Post:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "description": "An introduction",
    "content": "Hello everyone! This is my first post.",
    "contentType": "text/plain",
    "visibility": "PUBLIC"
  }'
```

**Example Request 2 - Markdown Post:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tutorial: Getting Started",
    "content": "# Introduction\n\nThis is a **markdown** post with *formatting*.\n\n- Item 1\n- Item 2",
    "contentType": "text/markdown",
    "visibility": "PUBLIC"
  }'
```

**Example Request 3 - Friends-Only Post:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Private thoughts",
    "content": "This is only for my friends to see.",
    "contentType": "text/plain",
    "visibility": "FRIENDS"
  }'
```

**Success Response (201 Created):**
```json
{
  "type": "post",
  "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/abc-def-123/",
  "author": {
    "type": "author",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
    "displayName": "Dark Blue",
    "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "github": "https://github.com/darkblue",
    "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
    "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
  },
  "title": "My First Post",
  "source": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/abc-def-123/",
  "origin": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/abc-def-123/",
  "description": "An introduction",
  "contentType": "text/plain",
  "content": "Hello everyone! This is my first post.",
  "visibility": "PUBLIC",
  "published": "2025-10-31T15:45:00Z",
  "count": 0,
  "comments": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/abc-def-123/comments"
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 400 Bad Request | Invalid request data | Missing required fields or invalid data |
| 401 Unauthorized | Authentication required | Not authenticated |
| 403 Forbidden | Not authorized to post as this author | Authenticated but not as the specified author |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist |

**Notes:**
- After creation, the node should push PUBLIC posts to all followers' inboxes
- After creation, the node should push FRIENDS posts to all friends' inboxes
- PUBLIC_UNLISTED posts are NOT pushed to inboxes automatically

---

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}`

**Purpose:** Retrieve a single specific post/entry by its ID.

**Authentication Required:** 
  - Conditional (login required for FRIENDS-only posts)
  - HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local

**Access Level:** [local, remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author who created the post | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `ENTRY_SERIAL` | UUID | Yes | UUID of the specific post | `9de17f29-c12e-8f97-bcbb-d34cc908f1ba` |

**Visibility Access Rules:**

| Post Visibility | Access Requirements |
|-----------------|-------------------|
| PUBLIC | Anyone can access (no auth required) |
| PUBLIC_UNLISTED | Anyone with the link can access (no auth required) |
| FRIENDS | MUST be authenticated as author or mutual friend |

**Example Request 1 - Public Post:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/
```

**Example Request 2 - Friends-Only Post (Requires Auth):**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/abc-friends-only-123/
```

**Example Request 3 - Unlisted Post:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/unlisted-post-456/
```

**Success Response (200 OK):**
```json
{
  "type": "post",
  "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
  "author": {
    "type": "author",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
    "displayName": "Dark Blue",
    "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "github": "https://github.com/darkblue",
    "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
    "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
  },
  "title": "An entry title about web dev",
  "source": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
  "origin": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
  "description": "This post discusses web development",
  "contentType": "text/markdown",
  "content": "# Web Development\n\nThis is a **great** post about *web development*.",
  "visibility": "PUBLIC",
  "published": "2025-10-31T14:30:00Z",
  "count": 5,
  "comments": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments",
  "commentsSrc": {
    "type": "comments",
    "page": 1,
    "size": 5,
    "post": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments",
    "comments": []
  }
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | Friends-only post accessed without auth |
| 403 Forbidden | Access denied | Friends-only post but user is not a friend |
| 404 Not Found | Post not found | ENTRY_SERIAL doesn't exist or post is deleted |

**Notes:**
- PUBLIC and PUBLIC_UNLISTED posts can be accessed without authentication
- FRIENDS-only posts require authentication as the author or a mutual friend
- Deleted posts return 404 (not accessible via API)
- The response includes the `commentsSrc` object with first page of comments
- For image posts, `content` contains base64-encoded image data
- The `count` field shows total number of comments

---

### Comments API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments`

**Purpose:** Retrieve paginated comments on a specific post/entry.

**Authentication Required:** 
    - Conditional (based on post visibility)
    - HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local

**Access Level:** [local, remote]

**Pagination:** Yes (1-based indexing)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the post's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `ENTRY_SERIAL` | UUID | Yes | UUID of the post | `9de17f29-c12e-8f97-bcbb-d34cc908f1ba` |

**Query Parameters:**

| Parameter | Type | Required | Default | Description | Example |
|-----------|------|----------|---------|-------------|---------|
| `page` | integer | No | 1 | Page number (1-indexed) | `page=2` |
| `size` | integer | No | 5 | Comments per page | `size=10` |

**Access Rules Based on Post Visibility:**

| Post Visibility | Who Can Access Comments |
|-----------------|------------------------|
| PUBLIC | Anyone |
| PUBLIC_UNLISTED | Anyone with the link |
| FRIENDS | Only the author and their friends (requires auth) |

**Example Request 1 - Basic:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments
```

**Example Request 2 - With Pagination:**
```bash
curl "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments?page=2&size=10"
```

**Example Request 3 - Friends-Only Post Comments (Requires Auth):**
```bash
curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/friends-post-123/comments"
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "comments" | `"comments"` |
| `page` | integer | Yes | Current page number | `1` |
| `size` | integer | Yes | Number of comments per page | `5` |
| `post` | string (URL) | Yes | FQID of the post these comments belong to | `"https://.../api/authors/.../entries/abc123"` |
| `id` | string (URL) | Yes | URL to this comments collection | `"https://.../api/authors/.../entries/abc123/comments"` |
| `count` | integer | Yes | Total number of comments on this post | `23` |
| `comments` | array | Yes | Array of comment objects | See Comment Object fields |

**Comment Object Fields (within `comments` array):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "comment" | `"comment"` |
| `id` | string (URL) | Yes | No | Comment's FQID | `"https://node-a.com/api/authors/111/commented/456"` |
| `author` | object | Yes | No | Author who made the comment | See Author Object fields |
| `comment` | string | Yes | No | The actual comment text | `"Great post!"` |
| `contentType` | string | Yes | No | Content type of comment | `"text/plain"`, `"text/markdown"` |
| `published` | string (ISO 8601) | Yes | No | When comment was created | `"2025-10-31T15:30:00Z"` |
| `entry` | string (URL) | Yes | No | FQID of the post being commented on | `"https://.../api/authors/.../entries/abc123"` |

**Success Response (200 OK):**
```json
{
  "type": "comments",
  "page": 1,
  "size": 5,
  "post": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
  "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments",
  "count": 12,
  "comments": [
    {
      "type": "comment",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/commented/comment-789/",
      "author": {
        "type": "author",
        "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
        "host": "https://node-a.herokuapp.com",
        "displayName": "Greg Johnson",
        "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
        "github": "https://github.com/gjohnson",
        "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
        "web": "https://node-a.herokuapp.com/authors/greg"
      },
      "comment": "Excellent post! Very informative.",
      "contentType": "text/plain",
      "published": "2025-10-31T15:30:00Z",
      "entry": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/"
    },
    {
      "type": "comment",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/commented/comment-456/",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Liam Houston",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/",
        "github": "https://github.com/liamhouston",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/liam.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/"
      },
      "comment": "Thanks for sharing!",
      "contentType": "text/plain",
      "published": "2025-10-31T14:45:00Z",
      "entry": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | Friends-only post accessed without auth |
| 403 Forbidden | Access denied | Friends-only post but user is not a friend |
| 404 Not Found | Post not found | ENTRY_SERIAL doesn't exist or post is deleted |

**Pagination Behavior:**
- First page is page 1 (not page 0)
- If `page` exceeds available pages, returns empty `comments` array
- Default page size is 5 comments
- Recommended maximum page size is 50 comments
- Comments are sorted by `published` date (newest first)

**Notes:**
- Comments can come from authors on any node (local or remote)
- Each comment includes full author information
- Comments on PUBLIC/PUBLIC_UNLISTED posts are visible to anyone
- Comments on FRIENDS-only posts are only visible to the post author and friends
- The `count` field shows total comments across all pages
- Empty `comments` array if no comments exist

---

### Commented API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/commented`

**Purpose:** Retrieve all comments made by a specific author.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**Pagination:** Yes (1-based indexing, though not explicitly in spec)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author whose comments to retrieve | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Access Rules:**

| Requestor Type | Can See Comments On |
|----------------|-------------------|
| Local authenticated | Any entry (public, unlisted, friends-only) |
| Remote node | Public and unlisted entries only |

**Example Request 1 - Basic:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented
```

**Example Request 2 - Remote Author's Comments:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/commented
```

**Response Format:**

The response is an array of comment objects (not wrapped in a container object).

**Comment Object Fields:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "comment" | `"comment"` |
| `id` | string (URL) | Yes | No | Comment's FQID | `"https://.../api/authors/111/commented/456"` |
| `author` | object | Yes | No | Author who made the comment | See Author Object fields |
| `comment` | string | Yes | No | The comment text | `"Great post!"` |
| `contentType` | string | Yes | No | Content type | `"text/plain"`, `"text/markdown"` |
| `published` | string (ISO 8601) | Yes | No | When comment was created | `"2025-10-31T15:30:00Z"` |
| `entry` | string (URL) | Yes | No | FQID of the post commented on | `"https://.../api/authors/.../entries/abc123"` |
| `web` | string (URL) | No | Yes | HTML page URL for viewing comment | `"https://.../authors/.../entries/abc123"` |

**Success Response (200 OK):**
```json
[
  {
    "type": "comment",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented/comment-789/",
    "author": {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Dark Blue",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "github": "https://github.com/darkblue",
      "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
    },
    "comment": "This is a great article!",
    "contentType": "text/plain",
    "published": "2025-10-31T15:30:00Z",
    "entry": "https://node-b.herokuapp.com/api/authors/xyz/entries/post123/",
    "web": "https://node-b.herokuapp.com/authors/xyz/entries/post123/"
  },
  {
    "type": "comment",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented/comment-456/",
    "author": {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Dark Blue",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "github": "https://github.com/darkblue",
      "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
    },
    "comment": "Thanks for sharing!",
    "contentType": "text/plain",
    "published": "2025-10-31T14:20:00Z",
    "entry": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/post456/",
    "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/post456/"
  }
]
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | No/invalid credentials |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist |

**Notes:**
- Returns comments in reverse chronological order (newest first)
- Comments can be on posts from any author (local or remote)
- Each comment includes the `entry` field pointing to the post it's on
- For local requests, includes comments on all post types
- For remote requests, only includes comments on PUBLIC and PUBLIC_UNLISTED posts
- Empty array `[]` if author has made no comments
- The `web` field provides a link to view the comment in a browser

---

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}`

**Purpose:** Retrieve a single specific comment by its ID.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the comment's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `COMMENT_SERIAL` | UUID | Yes | UUID of the specific comment | `comment-789-abc-def` |

**Example Request 1 - Basic:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented/comment-789/
```

**Example Request 2 - Remote Comment:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/commented/abc-def-456/
```

**Success Response (200 OK):**
```json
{
  "type": "comment",
  "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented/comment-789/",
  "author": {
    "type": "author",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
    "displayName": "Dark Blue",
    "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "github": "https://github.com/darkblue",
    "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/me.jpg",
    "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
  },
  "comment": "This is a great article! Very well written.",
  "contentType": "text/plain",
  "published": "2025-10-31T15:30:00Z",
  "entry": "https://node-b.herokuapp.com/api/authors/xyz/entries/post123/",
  "web": "https://node-b.herokuapp.com/authors/xyz/entries/post123/"
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | No/invalid credentials |
| 404 Not Found | Comment not found | COMMENT_SERIAL doesn't exist or author doesn't match |

**Notes:**
- The comment must belong to the specified author (AUTHOR_SERIAL)
- Returns 404 if comment exists but belongs to a different author
- The `entry` field points to the post the comment is on
- Works for comments on both local and remote posts
- Includes full author information in the response

---

### Likes API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes`

**Purpose:** Retrieve all likes on a specific post/entry.

**Authentication Required:** 
    - Conditional (based on post visibility)
    - HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local

**Access Level:** [local, remote]

**Pagination:** No (returns all likes)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the post's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `ENTRY_SERIAL` | UUID | Yes | UUID of the post | `9de17f29-c12e-8f97-bcbb-d34cc908f1ba` |

**Access Rules Based on Post Visibility:**

| Post Visibility | Who Can See Likes |
|-----------------|-------------------|
| PUBLIC | Anyone |
| PUBLIC_UNLISTED | Anyone with the link |
| FRIENDS | Only the author and their friends (requires auth) |

**Example Request 1 - Basic:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/likes
```

**Example Request 2 - Friends-Only Post (Requires Auth):**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/friends-post-123/likes
```

**Example Request 3 - Remote Post:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/abc-def-456/likes
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "likes" | `"likes"` |
| `items` | array | Yes | Array of like objects | See Like Object fields |

**Like Object Fields (within `items` array):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "like" | `"like"` |
| `@context` | string | Yes | No | JSON-LD context, always "https://www.w3.org/ns/activitystreams" | `"https://www.w3.org/ns/activitystreams"` |
| `summary` | string | No | Yes | Human-readable summary of the like | `"Lara Croft likes your post"` |
| `author` | object | Yes | No | Author who created the like | See Author Object fields |
| `object` | string (URL) | Yes | No | FQID of the post being liked | `"https://.../api/authors/.../entries/abc123"` |
| `published` | string (ISO 8601) | No | Yes | When the like was created | `"2025-10-31T16:00:00Z"` |

**Author Object Fields (within like):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "author" | `"author"` |
| `id` | string (URL) | Yes | No | Author's FQID | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"` |
| `host` | string (URL) | Yes | No | Author's home node URL | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com"` |
| `displayName` | string | Yes | No | Author's display name | `"Lara Croft"` |
| `url` | string (URL) | Yes | No | Author's API URL (same as id) | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"` |
| `github` | string (URL) | No | Yes | Author's GitHub profile URL | `"https://github.com/laracroft"` |
| `profileImage` | string (URL) | No | Yes | Author's profile image URL | `"https://i.imgur.com/k7XVwpB.jpeg"` |
| `web` | string (URL) | Yes | No | Author's HTML profile page URL | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"` |

**Success Response (200 OK):**
```json
{
  "type": "likes",
  "items": [
    {
      "type": "like",
      "@context": "https://www.w3.org/ns/activitystreams",
      "summary": "Lara Croft likes your post",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Lara Croft",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "github": "https://github.com/laracroft",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
      },
      "object": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "published": "2025-10-31T16:00:00Z"
    },
    {
      "type": "like",
      "@context": "https://www.w3.org/ns/activitystreams",
      "summary": "Greg Johnson likes your post",
      "author": {
        "type": "author",
        "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
        "host": "https://node-a.herokuapp.com",
        "displayName": "Greg Johnson",
        "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
        "github": "https://github.com/gjohnson",
        "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
        "web": "https://node-a.herokuapp.com/authors/greg"
      },
      "object": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "published": "2025-10-31T15:45:00Z"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | Friends-only post accessed without auth |
| 403 Forbidden | Access denied | Friends-only post but user is not a friend |
| 404 Not Found | Post not found | ENTRY_SERIAL doesn't exist or post is deleted |

**Notes:**
- Likes are returned in reverse chronological order (newest first)
- Includes likes from both local and remote authors
- Each like includes complete author information for display
- Empty `items` array if post has no likes
- The `@context` field is required for ActivityPub compatibility
- Likes on PUBLIC/PUBLIC_UNLISTED posts are visible to anyone
- Likes on FRIENDS-only posts require authentication as author or friend

---

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_ID}/likes`

**Purpose:** Retrieve all likes on a specific comment.

**Authentication Required:** Conditional (based on post visibility)

**Access Level:** [local, remote]

**Pagination:** No (returns all likes on the comment)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the post's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `ENTRY_SERIAL` | UUID | Yes | UUID of the post | `9de17f29-c12e-8f97-bcbb-d34cc908f1ba` |
| `COMMENT_ID` | UUID or FQID | Yes | UUID or FQID (percent-encoded) of the comment | `comment-123` or `https%3A%2F%2F...` |

**COMMENT_ID Format Options:**

| Format | Description | Example | When to Use |
|--------|-------------|---------|-------------|
| UUID | Simple comment UUID | `abc-def-123-456` | For local comments |
| FQID (percent-encoded) | Full comment URL, percent-encoded | `https%3A%2F%2Fnode-a.com%2Fapi%2Fauthors%2F...%2Fcommented%2F123` | For remote comments |

**Example Request 1 - Local Comment by UUID:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments/comment-abc-123/likes
```

**Example Request 2 - Remote Comment by FQID:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/post-123/comments/https%3A%2F%2Fnode-a.herokuapp.com%2Fapi%2Fauthors%2Fxyz%2Fcommented%2Fcomment-456/likes
```

**Example Request 3 - With Authentication:**
```bash
curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/friends-post-123/comments/comment-789/likes"
```

**Response Format:**

Same as post likes response - returns a `likes` object with `items` array containing like objects.

**Success Response (200 OK):**
```json
{
  "type": "likes",
  "items": [
    {
      "type": "like",
      "@context": "https://www.w3.org/ns/activitystreams",
      "summary": "Lara Croft likes your comment",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Lara Croft",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "github": "https://github.com/laracroft",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
      },
      "object": "https://node-a.herokuapp.com/api/authors/xyz/commented/comment-456/",
      "published": "2025-10-31T16:30:00Z"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | Friends-only post's comment accessed without auth |
| 403 Forbidden | Access denied | Friends-only post but user is not a friend |
| 404 Not Found | Comment or post not found | COMMENT_ID doesn't exist or post is deleted |

**Notes:**
- Access follows the parent post's visibility rules
- If post is FRIENDS-only, comment likes also require authentication
- Supports both UUID and FQID (percent-encoded) for COMMENT_ID
- FQID must be properly URL-encoded (percent-encoded)
- Empty `items` array if comment has no likes
- Includes likes from both local and remote authors

---

### Liked API

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/liked`

**Purpose:** Retrieve all posts and comments that a specific author has liked.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)

**Access Level:** [local, remote]

**Pagination:** No (returns all likes by the author)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author whose likes to retrieve | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Example Request 1 - Basic:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/liked
```

**Example Request 2 - Remote Author:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/liked
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "liked" | `"liked"` |
| `items` | array | Yes | Array of like objects created by this author | See Like Object fields |

**Like Object Fields (within `items` array):**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Object type, always "like" | `"like"` |
| `@context` | string | Yes | No | JSON-LD context | `"https://www.w3.org/ns/activitystreams"` |
| `summary` | string | No | Yes | Human-readable summary | `"Lara Croft likes your post"` |
| `author` | object | Yes | No | Author who created the like (same as requested author) | See Author Object fields |
| `object` | string (URL) | Yes | No | FQID of the post or comment being liked | `"https://.../api/authors/.../entries/abc123"` or `"https://.../commented/xyz"` |
| `published` | string (ISO 8601) | No | Yes | When the like was created | `"2025-10-31T16:00:00Z"` |

**Success Response (200 OK):**
```json
{
  "type": "liked",
  "items": [
    {
      "type": "like",
      "@context": "https://www.w3.org/ns/activitystreams",
      "summary": "Lara Croft likes a post",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Lara Croft",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "github": "https://github.com/laracroft",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
      },
      "object": "https://node-b.herokuapp.com/api/authors/xyz/entries/post123/",
      "published": "2025-10-31T16:00:00Z"
    },
    {
      "type": "like",
      "@context": "https://www.w3.org/ns/activitystreams",
      "summary": "Lara Croft likes a comment",
      "author": {
        "type": "author",
        "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
        "displayName": "Lara Croft",
        "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
        "github": "https://github.com/laracroft",
        "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
        "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
      },
      "object": "https://node-a.herokuapp.com/api/authors/abc/commented/comment456/",
      "published": "2025-10-31T15:30:00Z"
    }
  ]
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | No/invalid credentials |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist |

**Notes:**
- Returns likes in reverse chronological order (newest first)
- Includes likes on both posts and comments
- The `object` field can point to posts or comments (identified by URL pattern)
- Includes likes on objects from any node (local or remote)
- Empty `items` array if author has not liked anything
- All likes will have the same `author` (the requested author)

---

#### URL: `GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}`

**Purpose:** Retrieve a single specific like object by its ID.

**Authentication Required:** Yes (HTTP Basic Auth for remote, session auth for local)

**Access Level:** [local, remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the like's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `LIKE_SERIAL` | UUID | Yes | UUID of the specific like | `like-abc-123-def` |

**Example Request 1 - Basic:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/liked/like-789/
```

**Example Request 2 - Remote Like:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/2cabd0b3-4cc7-49da-9b42-65bc9c5e6f56/liked/abc-def-456/
```

**Success Response (200 OK):**
```json
{
  "type": "like",
  "@context": "https://www.w3.org/ns/activitystreams",
  "summary": "Lara Croft likes a post",
  "author": {
    "type": "author",
    "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
    "displayName": "Lara Croft",
    "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
    "github": "https://github.com/laracroft",
    "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
    "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/"
  },
  "object": "https://node-b.herokuapp.com/api/authors/xyz/entries/post123/",
  "published": "2025-10-31T16:00:00Z"
}
```

**Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 401 Unauthorized | Authentication required | No/invalid credentials |
| 404 Not Found | Like not found | LIKE_SERIAL doesn't exist or author doesn't match |

**Notes:**
- The like must belong to the specified author (AUTHOR_SERIAL)
- Returns 404 if like exists but belongs to a different author
- The `object` field can point to either a post or a comment
- Includes full author information in the response
- Useful for verifying like authenticity

---

### Inbox API

#### URL: `POST /api/authors/{AUTHOR_SERIAL}/inbox`

**Purpose:** The inbox is the central hub for receiving objects from other nodes in the distributed network. This endpoint implements the ActivityPub-like push model for federation.

**When to Use:**
- **From Remote Nodes:** When sending any activity to an author on this node
- **For Follow Requests:** When an author wants to follow someone on this node
- **For Sharing Posts:** When pushing a public/friends post to followers' inboxes
- **For Likes:** When liking a post or comment from this node
- **For Comments:** When commenting on a post from this node

**Why Use This:**
- **Asynchronous Processing:** Receiving node can process activities at its own pace
- **Activity Stream Compatible:** Follows ActivityPub/ActivityStreams patterns
- **Single Endpoint:** One endpoint handles all activity types (follow, post, like, comment)

**Authentication Required:** Yes (HTTP Basic Auth)

**Access Level:** [remote]

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_SERIAL` | UUID | Yes | UUID of the author receiving the object | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

**Supported Object Types:**

| Type | Purpose | When Sent | Processing |
|------|---------|-----------|------------|
| `follow` | Follow request | When author A wants to follow author B | Creates pending follow request for approval |
| `post` | Share post/entry | When sharing public/friends posts with followers | Stores post copy in recipient's inbox |
| `like` | Like notification | When liking a post or comment | Records like on the object |
| `comment` | Comment notification | When commenting on a post | Stores comment on the post |

---

#### Inbox Object Type: Follow Request

**When to Send:**
- When an author on your node wants to follow an author on another node
- Initiated by "Follow" button in UI
- Send to the target author's inbox

**Request Body - Follow Object:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "follow" | `"follow"` |
| `summary` | string | No | Yes | Human-readable description | `"Greg wants to follow Lara"` |
| `actor` | object | Yes | No | Author initiating the follow (follower) | See Actor Object fields |
| `object` | object | Yes | No | Author being followed | See Object fields |

**Actor/Object Author Fields:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "author" | `"author"` |
| `id` | string (URL) | Yes | No | Author's FQID | `"https://node-a.com/api/authors/111/"` |
| `host` | string (URL) | Yes | No | Author's home node URL | `"https://node-a.com"` |
| `displayName` | string | Yes | No | Author's display name | `"Greg Johnson"` |
| `url` | string (URL) | Yes | No | Author's API URL (same as id) | `"https://node-a.com/api/authors/111/"` |
| `github` | string (URL) | No | Yes | Author's GitHub profile URL | `"https://github.com/gjohnson"` |
| `profileImage` | string (URL) | No | Yes | Author's profile image URL | `"https://i.imgur.com/k7XVwpB.jpeg"` |
| `web` | string (URL) | Yes | No | Author's HTML profile page URL | `"https://node-a.com/authors/111/"` |

**Example Request - Follow:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "follow",
    "summary": "Greg wants to follow Lara",
    "actor": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "object": {
      "type": "author",
      "id": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "host": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com",
      "displayName": "Lara Croft",
      "url": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/",
      "github": "https://github.com/laracroft",
      "profileImage": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/media/user_images/lara.jpg",
      "web": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/authors/lara"
    }
  }'
```

**Success Response (201 Created):**
```json
{
  "status": "Follow request received",
  "message": "Follow request has been added to the inbox"
}
```

**Processing Notes:**
- Creates a PENDING follow request in the database
- Receiving author can approve/deny later via UI
- Follow is NOT automatically accepted
- Check follower status with: `GET /api/authors/{id}/followers/{follower_fqid}`

---

#### Inbox Object Type: Post/Entry

**When to Send:**
- When an author on your node creates a PUBLIC post (send to all followers)
- When an author on your node creates a FRIENDS post (send to all friends)
- When sharing/redistributing a post
- Do NOT send for PUBLIC_UNLISTED posts (they're not pushed to inboxes)

**Request Body - Post Object:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "post" | `"post"` |
| `id` | string (URL) | Yes | No | Post's FQID | `"https://node-a.com/api/authors/.../entries/abc123"` |
| `author` | object | Yes | No | Author who created the post | See Author Object fields |
| `title` | string | Yes | No | Post title | `"My First Post"` |
| `source` | string (URL) | Yes | No | Where the post came from | `"https://node-a.com/api/authors/.../entries/abc123"` |
| `origin` | string (URL) | Yes | No | Original source if reshared | `"https://node-a.com/api/authors/.../entries/abc123"` |
| `description` | string | No | Yes | Brief description | `"A post about web dev"` |
| `contentType` | string | Yes | No | Content MIME type | `"text/plain"`, `"text/markdown"`, `"image/png;base64"` |
| `content` | string | Yes | No | Post content (text or base64 image) | `"Hello world!"` |
| `visibility` | string | Yes | No | Who can see this | `"PUBLIC"`, `"FRIENDS"` |
| `published` | string (ISO 8601) | Yes | No | When published | `"2025-10-31T14:30:00Z"` |
| `count` | integer | Yes | No | Number of comments | `5` |
| `comments` | string (URL) | Yes | No | URL to comments | `"https://.../entries/abc123/comments"` |
| `commentsSrc` | object | No | Yes | Embedded comments | See CommentsSrc Object |
| `image` | string (URL) | No | Yes | Image URL if applicable | `"https://node-a.com/media/img.jpg"` |

**Example Request - Post:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "post",
    "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/",
    "author": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "title": "My First Post",
    "source": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/",
    "origin": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/",
    "description": "A post about web development",
    "contentType": "text/plain",
    "content": "Hello everyone! This is my first post.",
    "visibility": "PUBLIC",
    "published": "2025-10-31T14:30:00Z",
    "count": 0,
    "comments": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/comments",
    "commentsSrc": {
      "type": "comments",
      "page": 1,
      "size": 5,
      "post": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/entries/abc123/comments",
      "comments": []
    }
  }'
```

**Success Response (201 Created):**
```json
{
  "status": "Post received",
  "message": "Post has been added to the inbox"
}
```

**Processing Notes:**
- Receiving node stores a copy of the post
- Post appears in recipient's stream/inbox
- `visibility` must be PUBLIC or FRIENDS
- PUBLIC_UNLISTED posts should not be sent to inboxes

---

#### Inbox Object Type: Like

**When to Send:**
- When an author on your node likes a post from another node
- When an author on your node likes a comment from another node
- Send to the author of the post/comment being liked

**Request Body - Like Object:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "like" | `"like"` |
| `@context` | string | Yes | No | ActivityStreams context | `"https://www.w3.org/ns/activitystreams"` |
| `summary` | string | No | Yes | Human-readable summary | `"Greg likes your post"` |
| `author` | object | Yes | No | Author creating the like | See Author Object fields |
| `object` | string (URL) | Yes | No | FQID of post or comment being liked | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/.../entries/abc123"` |
| `published` | string (ISO 8601) | No | Yes | When the like was created | `"2025-10-31T16:00:00Z"` |

**Example Request - Like on Post:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "like",
    "@context": "https://www.w3.org/ns/activitystreams",
    "summary": "Greg likes your post",
    "author": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "object": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/post123/",
    "published": "2025-10-31T16:00:00Z"
  }'
```

**Example Request - Like on Comment:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "like",
    "@context": "https://www.w3.org/ns/activitystreams",
    "summary": "Greg likes your comment",
    "author": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "object": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented/comment456/",
    "published": "2025-10-31T16:00:00Z"
  }'
```

**Success Response (201 Created):**
```json
{
  "status": "Like received",
  "message": "Like has been recorded"
}
```

**Processing Notes:**
- Receiving node records the like on the specified object
- `object` can be a post URL or comment URL
- The like appears in the object's likes list
- Duplicate likes should be handled idempotently (don't create duplicates)

---

#### Inbox Object Type: Comment

**When to Send:**
- When an author on your node comments on a post from another node
- Send to the author of the post being commented on

**Request Body - Comment Object:**

| Field | Type | Required | Nullable | Description | Example Value |
|-------|------|----------|----------|-------------|---------------|
| `type` | string | Yes | No | Must be "comment" | `"comment"` |
| `id` | string (URL) | Yes | No | Comment's FQID | `"https://node-a.com/api/authors/.../commented/abc123"` |
| `author` | object | Yes | No | Author who made the comment | See Author Object fields |
| `comment` | string | Yes | No | The comment text | `"Great post!"` |
| `contentType` | string | Yes | No | Content type | `"text/plain"`, `"text/markdown"` |
| `published` | string (ISO 8601) | Yes | No | When comment was created | `"2025-10-31T15:30:00Z"` |
| `entry` | string (URL) | Yes | No | FQID of post being commented on | `"https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/.../entries/post123"` |

**Example Request - Comment:**
```bash
curl -u username:password -X POST \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/inbox \
  -H "Content-Type: application/json" \
  -d '{
    "type": "comment",
    "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/commented/comment789/",
    "author": {
      "type": "author",
      "id": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "host": "https://node-a.herokuapp.com",
      "displayName": "Greg Johnson",
      "url": "https://node-a.herokuapp.com/api/authors/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/",
      "github": "https://github.com/gjohnson",
      "profileImage": "https://i.imgur.com/k7XVwpB.jpeg",
      "web": "https://node-a.herokuapp.com/authors/greg"
    },
    "comment": "Excellent post! Very informative.",
    "contentType": "text/plain",
    "published": "2025-10-31T15:30:00Z",
    "entry": "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/post123/"
  }'
```

**Success Response (201 Created):**
```json
{
  "status": "Comment received",
  "message": "Comment has been added to the post"
}
```

**Processing Notes:**
- Receiving node stores the comment on the specified post
- Comment appears in the post's comments list
- The `entry` field must point to a valid post on the receiving node
- Comment count on the post is automatically incremented

---

**General Inbox Error Responses:**

| Status Code | Description | When This Occurs |
|-------------|-------------|------------------|
| 400 Bad Request | Invalid request format | Missing required fields, invalid JSON, or unsupported object type |
| 401 Unauthorized | Authentication required | No/invalid credentials provided |
| 404 Not Found | Author not found | AUTHOR_SERIAL doesn't exist on this node |
| 500 Internal Server Error | Processing error | Server failed to process the object |