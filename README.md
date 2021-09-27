# slackbot
simple slack bot that listens to all messages in a channel and reacts on yubikey

# requirements to run
- slack token
- cookie (if needed by your account)

### getting the token

from wee-slack: https://github.com/wee-slack/wee-slack

> Get a session token
> Open and sign into the Slack customization page. Check that you end up on the correct team.
> Open the developer console (Ctrl+Shift+J/Cmd+Opt+J in Chrome and Ctrl+Shift+K/Cmd+Opt+K in Firefox).
> Paste and run this code: window.prompt("Session token:", TS.boot_data.api_token)
> A prompt with the token will appear. Copy the token

Then just export it as SLACK_BOT_TOKEN or run the python app with the variable set in the same commandline
