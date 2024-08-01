from __future__ import annotations

import asyncio
import logging
import tomllib
from typing import TYPE_CHECKING

import aiocron
import aiofiles.os
import aiohttp

from utils.check import check_versions, invalidate_cache
from utils.create import connect
from utils.gather import gather_python_libs
from utils.write import pretty_name, write_log

if TYPE_CHECKING:
  from aiohttp import ClientSession

with open("config.toml") as f:
  config = tomllib.loads(f.read())

fmt = "[%(asctime)s][%(levelname)s] %(message)s"
datefmt = "%Y/%m/%d-%H:%M:%S"

logging.basicConfig(
  handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
  format=fmt,
  datefmt=datefmt,
  level=logging.INFO,
)


async def run_machine(name: str, session: ClientSession) -> None:
  try:
    logging.info(f"[{name}] Starting library check...")
    machine = await connect(name, config)
    logging.info(f"[{name}] Connected. Gathering Python libraries.")
    projects = await gather_python_libs(machine)
    logging.info(
      f"[{name}] Gathered libraries from {len(projects)} projects. Checking versions..."
    )

    m_name = pretty_name(machine.name)
    try:
      await aiofiles.os.rmdir(f"log/{m_name}")
    except Exception:
      pass

    for project in projects:
      logging.info(f"[{name}][{project.name}] Checking versions...")
      check = await check_versions(project.dependencies, session)
      logging.info(f"[{name}][{project.name}] Versions checked. Writing log.")
      await write_log(project, check)
  except Exception:
    logging.exception(f"[{name}] Failed!")


async def check_all_machines() -> None:
  session = aiohttp.ClientSession()
  invalidate_cache()  # We want to get the latest every day.
  loop = asyncio.get_running_loop()
  tasks = []
  for machine in config["sources"]["targets"]:
    task = loop.create_task(run_machine(machine["name"], session))
    tasks.append(task)
  await asyncio.gather(*tasks)


async def main():
  # await check_all_machines()
  cron = aiocron.crontab(
    config["sources"]["check_interval"], check_all_machines, start=True
  )

  while True:
    await asyncio.sleep(3600)


asyncio.run(main())
