from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from .dataclasses import Dependancy, Project

if TYPE_CHECKING:
  from asyncssh import SSHClientConnection as Connection

  from .dataclasses import Machine

REQUIREMENT_PATTERN = re.compile("(.*?)(==|>=|<=|<|>)(.*)")

LOG = logging.getLogger(__name__)


def generate_find_command(
  files: list[str], excluded_dirs: list[str] = []
) -> str:
  excluded = " -o ".join(
    [rf"-path '{excluded_dir}' -prune" for excluded_dir in excluded_dirs]
  )
  filenames = " -o ".join([rf"-name '{name}'" for name in files])

  if excluded:
    return rf"find / {excluded} -o \( {filenames} \) 2>/dev/null"
  else:
    return rf"find / \( {filenames} \) 2>/dev/null"


def clean_output(files: list[str]) -> list[str]:
  cleaned = []

  for file in files:
    if file.endswith("pip") or file.endswith("requirements.txt"):
      cleaned.append(file)

  return cleaned


def _process_deps(deps: list[str]) -> list[Dependancy]:
  out: list[Dependancy] = []
  for line in deps.split("\n"):
    if line.lstrip().startswith("#"):
      continue
    match = REQUIREMENT_PATTERN.match(line)
    if match:
      if match.group(2) is None and match.group(3) is None:
        dep = Dependancy(match.group(1), "==", "latest")
      else:
        dep = Dependancy(match.group(1), match.group(2), match.group(3))
      out.append(dep)

  return out


async def freeze_pips(path: str, conn: Connection) -> list[Dependancy]:
  result = await conn.run(f"{path} freeze")

  lines: str
  if isinstance(result.stdout, bytes):
    lines = result.stdout.decode()
  else:
    lines = result.stdout

  return _process_deps(lines)


async def read_requirements(path: str, conn: Connection) -> list[Dependancy]:
  result = await conn.run(f"cat {path}")

  lines: str
  if isinstance(result.stdout, bytes):
    lines = result.stdout.decode()
  else:
    lines = result.stdout

  return _process_deps(lines)


def merge_lists(projs: list[Project]) -> list[Project]:
  found_projects: dict[str, Project] = {}
  # Create a set from the projects dependencies if they have to be merged.

  for project in projs:
    if project.name not in found_projects:
      found_projects[project.name] = project
    else:
      old_list = found_projects[project.name].dependencies
      new_list = project.dependencies
      merged_list = old_list + new_list
      merged_set = set(merged_list)
      found_projects[project.name] = Project(
        list(merged_set), project.machine, project.path
      )

  return list(found_projects.values())


# Gather a list of libraries and locations from a machine
async def gather_python_libs(machine: Machine) -> list[Project]:
  # Commands to run:
  # generate_find_command()
  #   ^^ The above will find all requirements files and pip binaries.
  # clean_output()
  #   ^^ The above will extract only the lines ending in `pip` or `requirements.txt` (The python library sources)
  # freeze_pips()
  #   ^^ Run `pip freeze` and return lists of dependencies
  # read_requirements()
  #   ^^ `cat requirements.txt` and return lists of dependencies
  # merge_lists()
  #   ^^ Take in all lists, identify projects which are the same (venvs have both requirements and pip)

  if "ignore_paths" in machine.entry:
    ignore = machine.entry["ignore_paths"]
  else:
    ignore = []
  cmd = generate_find_command(["requirements.txt", "pip"], ignore)
  LOG.info(f"[{machine.name}][Gather] Running command `{cmd}`")

  find_result = await machine.conn.run(cmd)

  LOG.info(
    f"[{machine.name}][Gather] Finished running command. Cleaning output."
  )

  find_lines: str
  if isinstance(find_result.stdout, bytes):
    find_lines = find_result.stdout.decode()
  else:
    find_lines = find_result.stdout

  lines = find_lines.split("\n")

  LOG.info(
    f"[{machine.name}][Gather] Found {len(lines)} candidates for projects"
  )

  cleaned = clean_output(lines)

  LOG.info(
    f"[{machine.name}][Gather] Output cleaned. {len(cleaned)} remain. Running commands"
  )

  projects: list[Project] = []
  for file in cleaned:
    if file.endswith("pip"):
      LOG.info(f"[{machine.name}][Gather] Running pip for {file}")
      deps = await freeze_pips(file, machine.conn)
    else:
      LOG.info(f"[{machine.name}][Gather] Running cat for {file}")
      deps = await read_requirements(file, machine.conn)

    project = Project(deps, machine, file)
    projects.append(project)

  LOG.info(f"[{machine.name}][Gather] Gathered all data, running merge...")

  merged_projects = merge_lists(projects)

  LOG.info(f"[{machine.name}][Gather] Finished merging! All Done.")

  return merged_projects
