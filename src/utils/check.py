from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
  from aiohttp import ClientSession

  from .dataclasses import Dependancy

LOG = logging.getLogger(__name__)

library_cache: dict[str, Version] = {}
# Library name (lowered) to latest version


def invalidate_cache() -> None:
  global library_cache
  library_cache = {}


async def check_latest_version(
  name: str, session: ClientSession, *, use_cache: bool = True
) -> Version:
  if use_cache and name.lower() in library_cache:
    return library_cache[name.lower()]

  LOG.debug(f"[Checker] Getting version of {name}...")
  async with session.get(f"https://pypi.org/pypi/{name.lower()}/json") as resp:
    if resp.status != 200:
      raise Exception("Library not found!")
    data = await resp.json()
    library_cache[name.lower()] = Version(data["info"]["version"])

  return library_cache[name.lower()]


async def check_versions(
  deps: list[Dependancy], session: ClientSession
) -> dict[str, str]:
  """Take in dependencies, return a dict of name -> msg
  Messages include "OK", "Has: x.y.z Latest: w.y.z"""
  out: dict[str, str] = {}

  for dep in deps:
    try:
      latest = await check_latest_version(dep.library, session)
      if latest in dep.specifier:
        out[dep.library] = "OK"
      else:
        out[dep.library] = f"Has: {str(dep.version)} Latest: {str(latest)}"
    except Exception as e:
      out[dep.library] = "Exception " + str(e)

  return out
