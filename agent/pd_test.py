#!/usr/bin/env python3
"""Throwaway probe: can this Arcade account execute Pagerduty.Whoami?

Run: python agent/pd_test.py [--user <arcade_user_id>]
"""

import argparse
import os

from arcadepy import Arcade
from dotenv import load_dotenv

load_dotenv()

# Must be a real Arcade account: persona user_ids fail Arcade's user verification.
parser = argparse.ArgumentParser(description="PagerDuty Whoami probe")
parser.add_argument("--user", default="elisa.bellagamba@gmail.com")
ARCADE_USER_ID = parser.parse_args().user
TOOL = "Pagerduty.Whoami"

arcade = Arcade(api_key=os.environ["ARCADE_API_KEY"])

print(f"Authorizing {TOOL} for {ARCADE_USER_ID} ...")
auth = arcade.tools.authorize(tool_name=TOOL, user_id=ARCADE_USER_ID)
if auth.status != "completed":
    print(f"Authorization required. Visit: {auth.url}")
    print("Waiting for completion ...")
    arcade.auth.wait_for_completion(auth)
    print("Authorization completed.")
else:
    print("Already authorized.")

print(f"Executing {TOOL} ...")
try:
    response = arcade.tools.execute(tool_name=TOOL, input={}, user_id=ARCADE_USER_ID)
    print("--- raw response ---")
    print(response.model_dump_json(indent=2))
except Exception as err:
    print(f"--- error ({type(err).__name__}) ---")
    print(err)
