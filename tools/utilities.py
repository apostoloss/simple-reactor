from slack_sdk.web.client import WebClient


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def isYubikey(string):
    modhex = "cbdefghijklnrtuv"
    if len(string) != 44:
        return False
    for i in string:
        if i not in modhex:
            return False
    return True


def react_with(payload, emoji):
    """
    Adds an `emoji` reaction.
    It uses the `payload` to pull out the webclient part
    so that it can be used in clients with multiple workspaces
    """
    webclient: WebClient = payload.get("web_client")
    result = webclient.reactions_add(
        channel=payload.get("data").get("channel"),
        timestamp=payload.get("data").get("ts"),
        name=emoji,
    )
    return result
