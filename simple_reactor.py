"""
Simple slack client that uses rtm client and reacts on specific messages
"""

from dataclasses import dataclass
import json
import logging
import os
from functools import lru_cache
import time
import datetime
import re

import threading
from flask import Flask

from slack_sdk import WebClient
from slack_sdk.rtm import RTMClient

# from slack_sdk.web.slack_response import SlackResponse
from slack_sdk.errors import SlackClientError

from tools.utilities import bcolors, isYubikey, react_with


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("slackbot.log")
fh.setLevel(logging.DEBUG)
FORMAT = (
    "%(asctime)s - [%(name)s:%(lineno)s - %(funcName)s] - %(levelname)s - %(message)s"
)
fh.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(fh)
logger.info("Log level set: %s", logging.getLevelName(logger.getEffectiveLevel()))


def unescape(string: str):
    """
    Replaces &lt, &gt and &amp with respective characters
    """
    string = string.replace("&lt;", "<")
    string = string.replace("&gt;", ">")
    # this has to be last:
    string = string.replace("&amp;", "&")
    return string


def user_replace(string: str):
    """
    get a string (normally a message) that contains a slack user id from a mention
    and replace it with the correct username (example of a string containing one is: <@U1T3Y4BEK>)
    """
    pattern = re.compile(
        r"<@U\w+>"
    )  # maybe need to restrict the size of it by replacing '+' with {x} multiplier
    mentions = pattern.findall(string)
    if len(mentions) > 0:
        for user in mentions:
            string = string.replace(user, get_user(user[2:-1]))
    return string


@lru_cache()
def get_user(user_id):
    """
    call users_info via webclient and return the username
    """
    logger.debug("searching userid: %s", user_id)
    response = WebClient(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        headers={"cookie": os.environ.get("SLACK_COOKIE", "")},
    ).users_info(user=user_id)
    if response.data.get("ok"):
        username = (
            response.data.get("user").get("profile").get("display_name_normalized")
        )
        if username == "":
            username = response.data.get("user").get("name")
            # some members had the field empty, so use real_name instead
            if username == "":
                username = (
                    response.data.get("user").get("profile").get("real_name_normalized")
                )
        logger.debug("Found userid: %s = %s", user_id, username)
    else:
        logger.debug("Could not find userid: %s", user_id)

    logger.info("LRU Cache statistics for users: %s", get_user.cache_info())
    return username


@lru_cache()
def get_channel_name(channel_id):
    """
    Return a channel name from a channel_id
    """
    logger.debug("searching channelid: %s", channel_id)
    response = WebClient(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        headers={"cookie": os.environ.get("SLACK_COOKIE", "")},
    ).conversations_info(channel=channel_id)
    if response.data.get("ok"):
        channelname = response.data.get("channel").get("name")
    logger.info("LRU Cache statistics for channels: %s", get_channel_name.cache_info())
    return channelname


def ts_print(message, time_format="%Y-%m-%d %H:%M:%S"):
    """
    adds a timestamp in the beggining of a string and then prints it
    """
    logger.debug(str(message))
    now = time.time()
    time_format = "%m-%d %H:%M:%S"
    timestamp = datetime.datetime.fromtimestamp(now).strftime(time_format)
    # TODO: move the string manipulation somewhere else
    message = unescape(message)
    message = user_replace(message)
    print(f"{timestamp} {message}")


@RTMClient.run_on(event="message")
def text_print(**payload):
    """
    Prints every message that comes in (careful, this is also valid for private messages)
    Also adds the timestamp on the output and replaces user and channel ids with the respactive
    human recognisable counterparts.
    """
    data: dict = payload["data"]
    logger.debug(str(data))
    if data.get("subtype") in ["message_changed", "bot_message"]:
        logger.warning("Unhandled type: %s", data.get("subtype", "no subtype "))
        logger.debug("payload data: %s", payload["data"])
        # do nothing
        return

    if data.get("subtype") in ["message_replied"]:
        logger.info(
            "message reply: %s", data.get("message", "-- no message in payload --")
        )

    # logger.info("user :" + str(data.get("user")))
    user_id = data.get("user", "-- no user in message.user")
    logger.info("userid: %s", user_id)

    if user_id:
        user = get_user(user_id)
        logger.debug("Got user: %s", str(user))
    else:
        logger.debug("payload: %s", str(payload))
        user = "missing user"

    channel_id = data.get("channel")
    if channel_id:
        channel = get_channel_name(channel_id)
        logger.debug("Got channel: %s", str(channel))
    else:
        logger.debug(payload["data"])
        channel = "missing channel"

    text = data.get("text", "--missing text--")
    if text == "--missing text--":
        logger.debug("Data: %s", str(data))
        if "message" in data.items:
            text = data["message"].get("text")
    else:
        logger.debug("Data: %s", str(data))
        # text = data.get("text", "--missing text--")
    data["channelname"] = channel
    data["username"] = user
    data["timestamp"] = float(data.get("ts"))
    logger.info("message timestamp: %s", str(data["timestamp"]))

    if isYubikey(text):
        text = bcolors.FAIL + text + bcolors.ENDC
        try:
            result = react_with(payload=payload, emoji="scream")
            logger.debug("Reaction result: %s", str(result))
            ts_print(f"{user}@{channel}: {text}")
        except (SlackClientError) as error:
            logger.error("Add reaction on message failed due to %s", str(error))

        try:
            webclient: WebClient = payload.get("web_client")
            authenticated_user = webclient.auth_test().get("user_id")
            ts_print(f"{get_user(authenticated_user)} is going to do an update")
            if user_id == authenticated_user:
                resp = webclient.chat_update(
                    channel=payload.get("data").get("channel"),
                    ts=payload.get("data").get("ts"),
                    text="ooops",
                )
        except SlackClientError as error:
            logger.error("Change message failed due to %s", str(error))


def main():
    """
    Initializing slack client.
    """
    try:
        token = os.environ.get("SLACK_BOT_TOKEN")
        slack_cookie = os.environ.get("SLACK_COOKIE", "")
        rtm_client = RTMClient(token=token, headers={"cookie": slack_cookie})
        web_client = WebClient(token=token, headers={"cookie": slack_cookie})
        connection_test = web_client.auth_test().data
        if connection_test.get("ok"):
            space = connection_test.get("team")
            print(
                f"Auth successful. Bot/client connected.\n"
                f"Starting RTM on {bcolors.BOLD}{space}{bcolors.ENDC} workspace!"
            )
            rtm_client.start()
        else:
            print("Connection failed: " + str(json.dumps(connection_test)))
    except SlackClientError as err:
        print(err)


# host_name = "0.0.0.0"
# port = 23336
# app = Flask(__name__)

# @app.route("/")
# def stats():
#     return str(get_user.cache_info())


def thread_cache_webAPP():
    app = Flask(__name__)

    @app.route("/")
    def user_stats():
        return str(get_user.cache_info())

    app.run(debug=True, use_reloader=False)


if __name__ == "__main__":
    # threading.Thread(target=lambda: app.run(host=host_name, port=port, debug=True, use_reloader=False)).start()
    t_c_webApp = threading.Thread(name='Web App', target=thread_cache_webAPP)
    t_c_webApp.setDaemon(True)
    t_c_webApp.start()
    main()
