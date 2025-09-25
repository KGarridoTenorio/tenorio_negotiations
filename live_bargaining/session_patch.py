import asyncio
import time
from typing import List, Dict

import requests
from otree.database import db
from otree.models import Session
from requests.auth import HTTPBasicAuth

from .constants import C
from .models import SessionCounter

LLM_HOSTS: Dict[str, asyncio.Queue] = {}


class Queues:
    @classmethod
    async def create_queues(cls, code: str, llm_hosts: List[str]):
        print()
        print(f"Adding {len(llm_hosts)}")
        for llm_host in llm_hosts:
            print(llm_host)
        print()

        for round_number in range(1, C.NUM_ROUNDS + 1):
            key = f"{code}_{round_number}"
            LLM_HOSTS[key] = asyncio.Queue()
            for llm_host in llm_hosts:
                LLM_HOSTS[key].put_nowait(llm_host)

    @classmethod
    def add_hosts(cls, code: str, round_number: int):
        session = db.query(Session).filter_by(code=code).one()
        key = f"{code}_{round_number}"
        for llm_host in session.llm_hosts:
            LLM_HOSTS[key].put_nowait(llm_host)

    @classmethod
    async def acquire(cls, code: str, round_number: int):
        key = f"{code}_{round_number}"

        if key not in LLM_HOSTS:
            LLM_HOSTS[key] = asyncio.Queue()
            cls.add_hosts(code, round_number)

        llm_host = None
        end_time = time.time() + 90
        while time.time() <= end_time and llm_host is None:
            try:
                llm_host = LLM_HOSTS[key].get_nowait()
            except asyncio.QueueEmpty:
                await asyncio.sleep(.5)

        return llm_host

    @classmethod
    async def release(cls, code: str, round_number: int, llm_host: str):
        key = f"{code}_{round_number}"
        try:
            prev = LLM_HOSTS[key].qsize()
            LLM_HOSTS[key].put_nowait(llm_host)
            assert LLM_HOSTS[key].qsize() == prev + 1
        except Exception as e:
            print()
            print('RELEASE ERROR', e)


class SessionPatch:
    def __init__(self):
        # Only here to get rid of annoying PyCharm errors
        self.code = None
        self.config = None
        self.debug_log = None
        self.llm_hosts = None
        raise RuntimeError

    def initialize(self):
        SessionCounter.add_code(self.code)
        self.debug_log = {i: [] for i in range(C.NUM_ROUNDS + 1)}
        llm_hosts = [llm_host for llm_host, enabled in self.config.items()
                     if llm_host.startswith(("http://", "https://")) and
                     enabled is True and self.test_host(llm_host)]
        if not llm_hosts:
            raise NoServersException("\n\nNo LLM hosts available!\n")

        self.llm_hosts = llm_hosts

    def test_host(self, llm_host: str) -> bool:
        if not llm_host:
            return False

        basic = HTTPBasicAuth(self.config['llm_user'], self.config['llm_pass'])
        try:
            response = requests.get(llm_host, auth=basic, timeout=5)
            available = response.ok and response.text == 'Ollama is running'
        except Exception as e:
            print()
            print('TEST HOST ERROR', e)
            available = False

        if available:
            self.debug_log[0].append(f"LLM server available     {llm_host}")
        else:
            self.debug_log[0].append(f"LLM server NOT available {llm_host}")

        return available


def patch_session():
    Session.initialize = SessionPatch.initialize
    Session.test_host = SessionPatch.test_host


class NoServersException(Exception):
    pass
