# Heroku Setup Guide

## Set up Heroku CLI
```heroku --version```
Use this command to make sure heroku is installed.

```heroku login```
Use this command to log in to your Heroku account from the command line.

```source venv/bin/activate```
Run your virtual environment if you have one set up:

```pip install -r requirements.txt```
Install the required dependencies for your project.

## Create a Heroku App
Create the app on the Heroku dashboard. Choose a unique name for your app (dark-blue).

```heroku list```
Use this command to see a list of your Heroku apps. Should include the one you just created.

```heroku addons:create heroku-postgresql:essential-0 --app dark-blue```
Add a PostgreSQL database to your Heroku app.

```heroku run "env" --app dark-blue```
Check the environment variables for your Heroku app to confirm the database was added.
Should see something like DATABASE_URL=postgres://...

```heroku git:remote -a dark-blue```
Link your local git repository to the Heroku app you just created.