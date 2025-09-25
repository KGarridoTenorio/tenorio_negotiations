import re
import socket
from typing import Any, Dict

from settings import LOCAL_NAMES
from live_bargaining.utils import now_datetime

################################################################################
# These should all be removed before production
################################################################################
ALLOW_LOG = socket.gethostname() in LOCAL_NAMES
BASE = "./test/logs/"


def start() -> str:
    return f"[{now_datetime()}] "


def log_llm_response(response: Dict[str, Any]):
    if not ALLOW_LOG:
        return
    with open(BASE + 'llm.log', 'a') as f:
        f.write(f"{start()} {response}\n\n")


def log_constraints(message: str, llm_output: str,
                    match: re.Match = None, constraint: int = None):
    if not ALLOW_LOG:
        return
    llm_output = llm_output.replace('\n\n', '\n')
    log = f"{start()} {message}\n{llm_output} ||\n"
    if match is not None:
        log += f"M {match.group(0)} ||\n"
    if constraint is not None:
        log += f"C {constraint} ||\n"
    with open(BASE + 'constraints.log', 'a') as f:
        f.write(log + "\n")


def log_interpret(message: str, llm_output: str,
                  matches: str, price: int, quality: int):
    if not ALLOW_LOG:
        return
    llm_output = llm_output.replace('\n\n', '\n')
    log = f"{start()} (msg) {message}\n(llm) {llm_output} ||\n"
    if matches:
        log += f"{matches} ||\n"
    log += f"Price + quality | {price} + {quality} ||\n"
    with open(BASE + 'interpret.log', 'a') as f:
        f.write(log + "\n")


def log_removed(org: str, final: str, removed: str):
    if not ALLOW_LOG:
        return
    with open(BASE + 'removed.log', 'a') as f:
        f.write(f"ORG     {org}\n")
        f.write(f"FINAL   {final}\n")
        f.write(f"REMOVED {removed}\n\n")


def reset_logs():
    with open(BASE + 'test.log', 'a') as f:
        f.write("\n" * 3 + "#" * 80 + "\n")
    with open(BASE + 'llm.log', 'a') as f:
        f.write("\n" * 3 + "#" * 80 + "\n")
    with open(BASE + 'interpret.log', 'a') as f:
        f.write("\n" * 3 + "#" * 80 + "\n")
    with open(BASE + 'constraints.log', 'a') as f:
        f.write("\n" * 3 + "#" * 80 + "\n")
    with open(BASE + 'removed.log', 'a') as f:
        f.write("\n" * 3 + "#" * 80 + "\n")
