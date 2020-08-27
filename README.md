# Contact Backend
 ![](https://github.com/fedorgrab/contact-native/blob/master/static/contact-logo.svg)

## Local deployment
#### Overall project structure:
```
contact-backend # <--- Project Root Directory
│
└───conf
│   │   redis  #  Redis config file
│   │   secrets  # Secret keys file
│
└───python
|   │   ...  # Python interpeter and its virtual environment
|
└───repo
│   │  # <--- Clone Project here
│
└───database.db # File with sqlite3 database (will be created automatically after you first time launch the server).
```

1. Create virtual environment for python 3.8 (It is necessary to have python 3.8 installed on your local machine). In the project root directory:
    ```
    python3 -m venv python
    ```

2. Clone project repository:
    ```
    git clone https://github.com/fedorgrab/contact-backend.git repo
    ```

3. [Install Redis](https://medium.com/@petehouston/install-and-config-redis-on-mac-os-x-via-homebrew-eb8df9a4f298)

4. In the conf directory create 2 config files:

    secrets:
    ```
    SECRET_KEY = {randomly generated secret key}
    ```
    redis:
    ```
    REDIS_HOST = 127.0.0.1
    REDIS_PORT = 6379
    REDIS_DB = 1
    REDIS_PASSWORD =
    ```
    (In the example above default values are provided. If you did not apply any extra settings it should work fine)

5. Activate local environment from the root directory:
    ```
    source python/bin/activate
    ```
6. While launching the server first time it is necessary to migrate a database. Run from the repo directory:
    ```
    python manage.py migrate
    ```
8. Create superuser:
    ```commandline
    python manage.py createsuperuser
    ```
7. Launch django server from repo directory:
    ```
    python manage.py runserver 0.0.0.0:8000
    ```
8. Go to the web-browser and check `localhost:8000/admin`


