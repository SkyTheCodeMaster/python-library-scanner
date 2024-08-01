from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import asyncssh

from .dataclasses import Key, Machine

if TYPE_CHECKING:
  from typing import Any

  from asyncssh import SSHClientConnection as Connection

LOG = logging.getLogger(__name__)


def _get_machine(name: str, sources: list[dict]) -> dict:
  for machine_entry in sources:
    if name == machine_entry["name"]:
      return machine_entry
  return None


class SelfResult:
  stdout: str
  stderr: str


class SelfConnection:
  async def run(self, *args: list[str]) -> SelfResult:
    merged = " ".join(args)
    LOG.debug(f"[SelfConn] Running command {merged}")
    try:
      proc = await asyncio.create_subprocess_shell(
        merged, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
      )
    except Exception:
      LOG.exception("[SelfConn] Failed making process!")
    LOG.debug(f"[SelfConn] Made process {proc}")
    stdout, stderr = await proc.communicate()
    LOG.debug("[SelfConn] Command finished.")
    res = SelfResult()
    res.stdout = stdout.decode()
    res.stderr = stderr.decode()
    return res


async def connect(machine_name: str, config: dict[str, Any]) -> Machine:
  machine_entry: dict[str, str] = _get_machine(
    machine_name, config["sources"]["targets"]
  )

  default_key = config["sources"]["default_key"]

  host = machine_entry.get("host")
  user = machine_entry.get("user", ())

  key = machine_entry.get("key", default_key)

  key_data: dict[str, str] = config["keys"][key]

  opts = asyncssh.SSHClientConnectionOptions()
  machine_key = Key(key)
  if "key_file" in key_data:
    opts.client_host_keys = [key_data["key_file"]]
    machine_key.file = key_data["key_file"]
    if "passphrase" in key_data:
      machine_key.passphrase = key_data["passphrase"]
      opts.passphrase = key_data["passphrase"]
  elif "passwd" in key_data:
    opts.password = key_data["passwd"]
    machine_key.passwd = key_data["passwd"]
  else:
    raise ValueError(f"No authentication provided for {key}!")

  # Allow self connections without ssh via asyncio
  if host == "self":
    conn = SelfConnection()
  else:
    conn: Connection = await asyncssh.connect(
      host=host, options=opts, username=user
    )
  machine = Machine(conn, machine_entry, key, machine_name)

  return machine
