# The Team
| Name | CCID | Email |
| ----| ----- | ------|
Azim | imukith | imukith@ualberta.ca
Roshan | banisett | banisett@ualberta.ca
Bhuvan | bhuvanac | bhuvanac@ualberta.ca
Byungkook | byungkoo | byungkoo@ualberta.ca
Liam | lhouston | lhouston@ualberta.ca
Tanmay | tlad | tlad@ualberta.ca

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
