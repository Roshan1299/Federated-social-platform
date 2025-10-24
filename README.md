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

## API Documentation

This section details the REST API endpoints for the Social Distribution project.

---

### Get a Single Author's Profile

Retrieves the public profile information of a single author.

*   **URL:** `/api/authors/{AUTHOR_ID}/`
*   **Method:** `GET`
*   **URL Params:**
    *   `AUTHOR_ID` (required): The UUID of the author to retrieve.

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

### Get All Author Profiles

Retrieves the public profile information of all authors.

*   **URL:** `/api/authors/`
*   **Method:** `GET`

#### Example Request:

```bash
curl http://127.0.0.1:8000/api/authors/
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

Retrieves the details of a single post by its ID.

*   **URL:** `/api/posts/{POST_ID}/`
*   **Method:** `GET`
*   **URL Params:**
    *   `POST_ID` (required): The UUID of the post to retrieve.

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
*   **URL Params:** UUId of post required

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
