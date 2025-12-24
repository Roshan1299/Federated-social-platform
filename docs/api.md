# API Documentation

This document details the REST API endpoints for the Federated Social Platform project.

## Authentication

The API supports two authentication methods:
- **Session Authentication**: For local UI access
- **HTTP Basic Authentication**: For node-to-node communication

## Core Endpoints

### Authors API

#### Get All Authors
Retrieves a paginated list of all authors.

- **URL:** `/api/authors/`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote access, session auth or HTTP Basic for local)
- **Access Level:** [local, remote]
- **Pagination:** Yes (1-based indexing)

**Query Parameters:**

| Parameter | Type | Required | Default | Description | Example |
|-----------|------|----------|---------|-------------|---------|
| `page` | integer | No | 1 | Page number to retrieve (1-indexed) | `page=2` |
| `size` | integer | No | 10 | Number of entries per page | `size=20` |

**Example Request:**
```bash
curl -u username:password \
  https://darkblue-xxxxxxxxxxxx.herokuapp.com/api/authors/
```

**Example Response:**
- **Code:** `200 OK`
- **Content:**
```json
{
  "type": "authors",
  "authors": [
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
  ],
  "page": 1,
  "size": 10,
  "count": 25,
  "num_pages": 3
}
```

#### Get a Single Author's Profile
Retrieves the public profile information of a single author.

- **URL:** `/api/authors/{AUTHOR_ID}/`
- **Method:** `GET`
- **URL Params:**
  - `AUTHOR_ID` (required): The UUID of the author to retrieve.
- **Authentication Required:** Yes (local session auth or HTTP Basic Auth for remote)
- **Access Level:** [local]

**Example Request:**
```bash
curl http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/
```

**Example Response:**
- **Code:** `200 OK`
- **Content:**
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

#### Get Author by Fully Qualified ID (FQID)
Retrieves author information using their Fully Qualified ID (FQID), which is the complete URL of the author's profile on any node.

- **URL:** `/api/authors/{AUTHOR_FQID}/`
- **Method:** `GET`
- **URL Params:**
  - `AUTHOR_FQID` (required): The percent-encoded full URL of the author to retrieve.
- **Authentication Required:** Yes (HTTP Basic Auth required)
- **Access Level:** [remote]

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

### Posts API

#### Create a New Post
Creates a new post for an authenticated author.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/`
- **Method:** `POST`
- **Authorization:** Required (user must be logged in and be the author)
- **Content-Type:** `application/json`
- **URL Params:**
  - `AUTHOR_ID` (required): The UUID of the author creating the post.
- **Request Body:**
  - `title` (required): The title of the post
  - `description` (optional): Short description or summary of the post
  - `content` (required): The actual content of the post
  - `contentType` (required): The type of content ('text/plain', 'text/markdown', 'image/png', etc.)
  - `visibility` (required): The visibility of the post ('PUBLIC', 'PUBLIC_UNLISTED', 'FRIENDS')
  - `image` (optional): URL to an image if the post includes one

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "My New Post",
    "description": "A short description",
    "content": "Hello world!",
    "contentType": "text/plain",
    "visibility": "PUBLIC"
  }'
```

**Example Response:**
- **Code:** `201 Created`
- **Content:**
```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/",
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

#### Get Author's Posts
Retrieves a paginated list of recent posts/entries created by a specific author.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)
- **Access Level:** [local, remote]
- **Pagination:** Yes (1-based indexing)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_ID` | UUID | Yes | UUID of the author whose posts to retrieve | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |

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

**Example Request:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/
```

**Example Request with Pagination:**
```bash
curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/?page=2&size=5"
```

**Example Response:**
- **Code:** `200 OK`
- **Content:**
```json
{
  "type": "posts",
  "page": 1,
  "size": 10,
  "count": 25,
  "items": [
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

#### Get a Single Post
Retrieves the details of a single post by its ID with appropriate visibility-based access controls.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/` or `/api/entries/{ENTRY_FQID}/`
- **Method:** `GET`
- **URL Params:**
  - `AUTHOR_ID` (required for UUID-based): The UUID of the author who created the post
  - `ENTRY_ID` (required for UUID-based): The UUID of the post to retrieve
  - `ENTRY_FQID` (required for FQID-based): The Fully Qualified ID of the post
- **Access Controls:**
  - **PUBLIC posts:** Accessible to all users
  - **PUBLIC_UNLISTED posts:** Accessible to all users
  - **FRIENDS posts:** Accessible only to the post author and mutual friends (both authors must follow each other)

**Example Request:**
```bash
curl http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/
```

**Example Response:**
- **Code:** `200 OK`
- **Content:**
```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/",
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

#### Edit a Post
Allows an authenticated author to edit their own post.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/` (PUT/PATCH)
- **Method:** `PUT` or `PATCH`
- **Authorization:** Required (user must be logged in and be the post author)
- **Content-Type:** `application/json`
- **URL Params:**
  - `AUTHOR_ID` (required): The UUID of the author
  - `ENTRY_ID` (required): The UUID of the post to edit

**Example Request:**
```bash
curl -X PUT http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/ \
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

**Example Response:**
- **Code:** `200 OK` (for successful update)
- **Content:**
```json
{
    "type": "post",
    "id": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/",
    "title": "Updated Title",
    "description": "Updated Description",
    "content": "Updated post content",
    "contentType": "text/plain",
    "visibility": "FRIENDS",
    "updated": "2025-10-17T00:00:00Z",
    "published": "2023-01-01T00:00:00Z"
}
```

#### Delete a Post
Deletes an existing post. Only the post's author can delete it.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/` (DELETE)
- **Method:** `DELETE`
- **Authorization:** Required (user must be logged in as the author of the post)
- **URL Params:**
  - `AUTHOR_ID` (required): The UUID of the author
  - `ENTRY_ID` (required): The UUID of the post to delete

**Example Request:**
```bash
curl -X DELETE http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 204 No Content

### Inbox API

#### Post to Author's Inbox
The inbox is the central hub for receiving objects from other nodes in the distributed network. This endpoint implements the ActivityPub-like push model for federation.

- **URL:** `/api/authors/{AUTHOR_ID}/inbox`
- **Method:** `POST`
- **Authentication Required:** Yes (HTTP Basic Auth)
- **Access Level:** [remote]

**When to Use:**
- **From Remote Nodes:** When sending any activity to an author on this node
- **For Follow Requests:** When an author wants to follow someone on this node
- **For Sharing Posts:** When pushing a public/friends post to followers' inboxes
- **For Likes:** When liking a post or comment from this node
- **For Comments:** When commenting on a post from this node

**Supported Object Types:**
- `follow` - Follow request
- `post` - Share post/entry
- `like` - Like notification
- `comment` - Comment notification
- `unfollow` - Unfollow notification

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

**Example Response:**
- **Code:** 201 Created
- **Content:**
```json
{
  "status": "Follow request received",
  "message": "Follow request has been added to the inbox"
}
```

### Follow Requests API

#### Send Follow Request
Sends a follow request from one author to another (must be approve/denied by follow receiver).

- **URL:** `/api/authors/{AUTHOR_ID}/following/{FOREIGN_AUTHOR_FQID}`
- **Method:** `PUT`
- **Authorization:** Required (user must be logged in)
- **URL Params:** 
  - `AUTHOR_ID` (UUID of author making request)
  - `FOREIGN_AUTHOR_FQID` (percent-encoded URL of author to follow)

**Example Request:**
```bash
curl -X PUT http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/following/http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fyyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy%2F/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 201 Created
- **Content:**
```json
{
    "type": "followRequest",
    "sender": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
    "receiver": "http://127.0.0.1:8000/api/authors/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
    "status": "PENDING"
}
```

#### Get Follow Requests
Returns pending follow requests targeting the specified local author.

- **URL:** `/api/authors/{AUTHOR_ID}/follow_requests`
- **Method:** `GET`
- **Authorization:** Required (session auth — only the local author may call this endpoint)
- **URL Params:** `AUTHOR_ID` (UUID of author receiving requests)

**Example Request:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/follow_requests
```

**Example Response:**
- **Code:** 200 OK
- **Content:**
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

#### Approve/Deny Follow Request
Allows an author to approve or deny a pending follow request.

- **URL:** `/api/authors/{AUTHOR_ID}/followers/{FOREIGN_AUTHOR_FQID}` (PUT for approve, DELETE for deny)
- **Method:** `PUT` (approve) or `DELETE` (deny)
- **Authorization:** Required (receiver must be logged in)
- **URL Params:**
  - `AUTHOR_ID` (UUID of author receiving request)
  - `FOREIGN_AUTHOR_FQID` (percent-encoded URL of sender)

**Example Approve Request:**
```bash
curl -X PUT http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/followers/http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fyyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy%2F/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 200 OK
- **Content:**
```json
{
    "type": "followRequest",
    "sender": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
    "receiver": "http://127.0.0.1:8000/api/authors/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/",
    "status": "APPROVED"
}
```

### Likes API

#### Like or Unlike a Post
Toggles a like on a post by the authenticated user.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/likes/`
- **Method:** `POST`
- **Authorization:** Required (user must be logged in)
- **URL Params:**
  - `AUTHOR_ID` (UUID of author making the like)
  - `ENTRY_ID` (UUID of the post to like)

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/likes/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 200 OK
- **Content:**
```json
{
  "liked": true,
  "count": 5
}
```

#### View Post Likes
Returns a list of authors who liked a given post.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/likes/`
- **Method:** `GET`
- **Authorization:** Required (only post author and followers can view likes on friends-only posts)
- **URL Params:**
  - `AUTHOR_ID` (UUID of post author)
  - `ENTRY_ID` (UUID of the post)

**Example Request:**
```bash
curl http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/likes/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 200 OK
- **Content:**
```json
{
  "type": "likes",
  "post": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/",
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

### Comments API

#### Add a Comment to a Post
Creates a comment on a specific post.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments/`
- **Method:** `POST`
- **Authorization:** Required (user must be logged in)
- **URL Params:**
  - `AUTHOR_ID` (UUID of post author)
  - `ENTRY_ID` (UUID of the post to comment on)
- **Form Data:**
  - `content` (string, required): Text of the comment.

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/comments/ \
  -H "Authorization: Bearer <token>" \
  -F "content=Nice post! 👏"
```

**Example Response:**
- **Code:** 201 Created
- **Content:**
```json
{
  "type": "comment",
  "id": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/commented/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/",
  "author": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
  "post": "http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/",
  "content": "Nice post! 👏",
  "created_at": "2025-10-18T03:25:00Z",
  "like_count": 0
}
```

#### Get Post Comments
Retrieve paginated comments on a specific post/entry.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments`
- **Method:** `GET`
- **Authentication Required:** Conditional (based on post visibility)
- **Access Level:** [local, remote]
- **Pagination:** Yes (1-based indexing)

**URL Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `AUTHOR_ID` | UUID | Yes | UUID of the post's author | `bb89f943-bd11-475d-9e1e-71ef9f7a914a` |
| `ENTRY_ID` | UUID | Yes | UUID of the post | `9de17f29-c12e-8f97-bcbb-d34cc908f1ba` |

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

**Example Request:**
```bash
curl https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments
```

**Example Request with Pagination:**
```bash
curl "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/entries/9de17f29-c12e-8f97-bcbb-d34cc908f1ba/comments?page=2&size=10"
```

### Followers API

#### Get Author's Followers
Retrieve a list of all authors who are following a specific author.

- **URL:** `/api/authors/{AUTHOR_ID}/followers`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)
- **Access Level:** [local, remote]
- **URL Params:** `AUTHOR_ID` (UUID of the author whose followers you want)

**Example Request:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/followers
```

**Response Fields:**

| Field | Type | Required | Description | Example Value |
|-------|------|----------|-------------|---------------|
| `type` | string | Yes | Object type, always "followers" | `"followers"` |
| `followers` | array | Yes | Array of author objects representing followers | See Author Object fields |

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

#### Check if Following
Check if a specific foreign author is following another author.

- **URL:** `/api/authors/{AUTHOR_ID}/followers/{FOREIGN_AUTHOR_FQID}`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)
- **Access Level:** [local, remote]
- **URL Params:**
  - `AUTHOR_ID` (UUID of the author being followed)
  - `FOREIGN_AUTHOR_FQID` (percent-encoded FQID of the potential follower)

**Example Request:**
```bash
curl -u username:password \
  "https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/followers/http%3A%2F%2Fother-node.com%2Fapi%2Fauthors%2Fxyz789%2F"
```

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

### Following API

#### Get Authors a User is Following
Retrieve a list of authors that a local author is following.

- **URL:** `/api/authors/{AUTHOR_ID}/following`
- **Method:** `GET`
- **Authentication Required:** Yes (session auth — only the local author may call this endpoint)
- **Access Level:** [local]
- **URL Params:** `AUTHOR_ID` (UUID of the author whose following list you want)

**Success Response - Example (200 OK):**
```json
{
  "type": "following",
  "items": [ /* array of author objects (same shape as Author object in Followers response) */ ]
}
```

#### Follow/Unfollow Foreign Author
Create or delete a follow relationship with a foreign author.

- **URL:** `/api/authors/{AUTHOR_ID}/following/{FOREIGN_AUTHOR_FQID}`
- **Method:** `PUT` (follow) or `DELETE` (unfollow)
- **Authentication Required:** Yes (session auth — only the local author may call this endpoint)
- **URL Params:**
  - `AUTHOR_ID` (UUID of the local author)
  - `FOREIGN_AUTHOR_FQID` (percent-encoded FQID of the target author)

**Success Responses:**
- `201 Created` when a new follow request is created or successfully delivered to remote inbox
- `200 OK` when a follow request already exists
- `204 No Content` when an existing follow relationship is removed

### Comment Likes API

#### Like or Unlike a Comment
Toggles a like on a specific comment.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments/{COMMENT_ID}/likes/`
- **Method:** `POST`
- **Authorization:** Required (user must be logged in)
- **URL Params:**
  - `AUTHOR_ID` (UUID of post author)
  - `ENTRY_ID` (UUID of post containing comment)
  - `COMMENT_ID` (UUID of the comment to like)

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/authors/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/entries/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy/comments/zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz/likes/ \
  -H "Authorization: Bearer <token>"
```

**Example Response:**
- **Code:** 200 OK
- **Content:**
```json
{
  "type": "commentLike",
  "author": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/",
  "comment": "http://127.0.0.1:8000/api/authors/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/commented/zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz/",
  "liked": true,
  "like_count": 3,
  "created_at": "2025-10-18T03:40:00Z"
}
```

### Liked API

#### Get Author's Liked Items
Retrieve all posts and comments that a specific author has liked.

- **URL:** `/api/authors/{AUTHOR_ID}/liked`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)
- **Access Level:** [local, remote]
- **Pagination:** No (returns all likes by the author)
- **URL Params:** `AUTHOR_ID` (UUID of the author whose likes to retrieve)

**Example Request:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/liked
```

**Success Response - Example (200 OK):**
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
    }
  ]
}
```

### Commented API

#### Get Author's Comments
Retrieve all comments made by a specific author.

- **URL:** `/api/authors/{AUTHOR_ID}/commented`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote, session auth or HTTP Basic Auth for local)
- **Access Level:** [local, remote]
- **Pagination:** No (returns all comments by the author)
- **URL Params:** `AUTHOR_ID` (UUID of the author whose comments to retrieve)

**Example Request:**
```bash
curl -u username:password \
  https://dark-blue-t-6ce3d0bd82d3.herokuapp.com/api/authors/bb89f943-bd11-475d-9e1e-71ef9f7a914a/commented
```

**Success Response - Example (200 OK):**
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
  }
]
```

### Image API

#### Get Author Profile Image
Retrieve the profile image for an author as binary data.

- **URL:** `/api/authors/{AUTHOR_ID}/image`
- **Method:** `GET`
- **Authentication Required:** Conditional (based on post visibility for entries)
- **URL Params:** `AUTHOR_ID` (UUID of the author)

#### Get Post Image
Retrieve the image from an image post as binary data.

- **URL:** `/api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/image`
- **Method:** `GET`
- **Authentication Required:** Conditional (based on post visibility)
- **URL Params:**
  - `AUTHOR_ID` (UUID of post author)
  - `ENTRY_ID` (UUID of the post)

## Error Responses

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid request data or missing required fields |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - User does not have permission to perform the action |
| 404 | Not Found - Requested resource does not exist |
| 415 | Unsupported Media Type - When image format is not supported |
| 500 | Internal Server Error - Server error occurred |

## Content Types

### Supported Content Types

| Content Type | Description |
|--------------|-------------|
| `text/plain` | Plain text content |
| `text/markdown` | Markdown-formatted content |
| `image/png;base64` | PNG image in base64 encoding |
| `image/jpeg;base64` | JPEG image in base64 encoding |
| `application/base64` | Generic binary content in base64 encoding |

## Visibility Levels

### Post Visibility Options

| Visibility | Description |
|------------|-------------|
| `PUBLIC` | Visible to all users |
| `PUBLIC_UNLISTED` | Visible to all users but not listed in public feeds |
| `FRIENDS` | Visible only to mutual followers |
| `DELETED` | Post has been deleted |

## Federation Endpoints

### Remote Author Endpoints

#### Get Remote Author by FQID
Retrieve author information from a remote node using their Fully Qualified ID.

- **URL:** `/api/authors/{AUTHOR_FQID}/`
- **Method:** `GET`
- **Authentication Required:** Yes (HTTP Basic Auth for remote access)
- **Access Level:** [remote]

### Remote Post Endpoints

#### Get Remote Post by FQID
Retrieve a post from a remote node using its Fully Qualified ID.

- **URL:** `/api/entries/{ENTRY_FQID}`
- **Method:** `GET`
- **Authentication Required:** Conditional (based on post visibility)
- **Access Level:** [local, remote]

## Additional Endpoints

### Legacy API Routes

#### Direct Post Access
- **URL:** `/api/posts/{POST_ID}/`
- **Method:** `GET`
- **Purpose:** Legacy endpoint for accessing posts directly by ID

### Image Upload/Receive Endpoints

#### Receive Remote Images
- **URL:** `/api/images/`
- **Method:** `POST`
- **Authentication:** HTTP Basic Auth
- **Purpose:** Receive images pushed from remote nodes