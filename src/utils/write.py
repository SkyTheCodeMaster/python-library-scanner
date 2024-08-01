from __future__ import annotations

import datetime
import tomllib
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os
import pytz

if TYPE_CHECKING:
  from .dataclasses import Project

# Write the output to `log/MACHINE/PROJECT.txt` files
"""
Machine/Project | YYYY/MM/DD
----------------------------
Outdated Libraries:

----------------------------
Up to Date Libraries:
"""

with open("config.toml") as f:
  config = tomllib.loads(f.read())
  tz = pytz.timezone(config["log"]["timezone"])


def pretty_name(name: str) -> str:
  return name.strip().lower().replace(" ", "_").replace("-", "_")


async def write_log(project: Project, check_result: dict[str, str]) -> None:
  m_name = pretty_name(project.machine.name)
  p_name = pretty_name(project.name)
  await aiofiles.os.makedirs(f"log/{m_name}", exist_ok=True)

  date = datetime.datetime.now(tz=tz)
  header = f"{m_name}/{p_name} | {date.strftime('%F')}"

  chunk = f"{header}\n{project.path}\n{'-'*len(header)}\nOutdated Libraries:\n"

  uptodate = []

  for library, result in check_result.items():
    if result == "OK":
      uptodate.append(library)
    else:
      chunk += f"{library}: {result}\n"

  up = "\n".join(uptodate)
  chunk += f"{'-'*len(header)}\nUp to Date Libraries:\n{up}"

  file = await aiofiles.open(f"log/{m_name}/{p_name}.txt", "w")
  await file.write(chunk)
  await file.close()
