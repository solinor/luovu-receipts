# Luovu receipts checking

This simple service matches rows from invoice and receipts uploaded to [Luovu](https://www.luovu.com/) to show what information is missing or incorrect.

The service is internal-only for Solinor Ltd. You are free to take whatever is useful for you - the code is under [MIT license](LICENSE.md). Taking this service into use in a different environment will require code changes.


* [Luovu API integration](#luovu-api-integration)
* [G Suite integration](#g-suite-integration)
* [Slack integration](#slack-integration)
* [Recommended Heroku setup](#recommended-heroku-setup)
* [Syncing data](#syncing-data)


## Luovu API integration

To set up Luovu integration, you need to ask partner token from Luovu. This is a 40 character random string with a-z0-9. Set to `LUOVU_PARTNER_TOKEN` variable.

You also need a real user. Store username (email) and password (`LUOVU_USERNAME`, and `LUOVU_PASSWORD`).

Finally, `LUOVU_BUSINESS_ID` is your business ID (in Finland, typically "Y-tunnus").

## G Suite integration

G Suite is used for signing in. Steps to setup:

- Go to https://console.cloud.google.com/
- Create a new project
- Go to "APIs & Services", enable "Google+ API". No need to configure Google+.
- Go to "APIs & Services -> Credentials". Create OAuth Client ID. Select Web Application. Don't set "Authorised JavaScript origins". Set "Authorised redirect URIs" to your application's install address.
- Copy access key, secret key. Set to `GOOGLEAUTH_CLIENT_ID` and `GOOGLEAUTH_CLIENT_SECRET` variables.
- Set `GOOGLEAUTH_CALLBACK_DOMAIN` to one of the addresses you entered to "Authorized redirect URIs".
- Set `GOOGLEAUTH_APPS_DOMAIN` to your G Suite domain to restrict others from signing in.

## Slack integration

- Go to https://api.slack.com/apps
- Register a new simple app (not workspace app)
- Add a new bot user. Enable "Always Show My Bot as Online".
- Go to "Install app", and install to your workspace.
- Copy "Bot User OAuth Access Token" (one that starts with `xoxb-`) to `SLACK_BOT_ACCESS_TOKEN`.

- Set `SLACK_ADMIN_EMAIL` to a valid email address for the user who should receive a copy of notifications. This will be used to lookup Slack ID.
- Run `python manage.py refresh_slack_users` regularly (daily?) to have up-to-date information for notifications.


## Recommended Heroku setup

- Sentry (free tier) for error reporting. Does not require configuring this app - when enabled, all errors will be sent automatically.
- Deploy hook to send new deploys to Sentry. Follow instructions in Sentry.
- Papertrail (Fixa, $7/month) for logging. Follow Papertrail instructions for setting up Heroku syslog destination. No configuration options in this app.
- Heroku Postgres (Hobby basic, $9/month)
- Heroku scheduler (free) for syncing and cleaning up.

*Heroku scheduler configuration*:

- `python manage.py refresh_all_receipts` - hourly. Refresh all receipts from all users.
- `python manage.py clearsessions` - daily. Clean up expired sessions from Django session storage.
- `python manage.py refresh_slack_users` - daily. Sync user IDs from Slack to local database.

*Heroku buildpacks*

- heroku/python
- https://github.com/ojarva/django-compressor-heroku-buildpack.git

## Syncing data

Data is synced from three different places:

- Hourly heroku scheduler task: `python manage.py refresh_all_receipts` - syncs all receipts for all users.
- Whenever user clicks "Luovu" link, outgoing ID is recorded, and automatically synced when user comes back. This also means additional delay on the next pageload, as this is synchronous operation.
- Whenever user clicks "Update data from Luovu" button, receipts around current month are synchronously reloaded, before page is returned to the user.
