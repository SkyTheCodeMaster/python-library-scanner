from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from packaging.specifiers import SpecifierSet

if TYPE_CHECKING:
  from typing import Optional

  from asyncssh import SSHClientConnection as Connection

NAME_IGNORE_FOLDERS: list[str] = [
  ".venv",
  "bin",
  "include",
  "lib",
  "lib64",
  "pip",
  "python3.10",
  "python3.11",
  "python3.8",
  "python3.9",
  "requirements.txt",
  "site-packages",
  "src",
  "venv",
]


class Project:
  dependencies: list[Dependancy]  # name, version
  machine: Machine  # The machine where this project lives.
  path: str  # Absolute path to the project
  _cached_name: str

  def __init__(
    self,
    dependencies: list[Dependancy] = None,
    machine: Machine = None,
    path: str = None,
  ) -> None:
    self.dependencies = dependencies
    self.machine = machine
    self.path = path

  def _is_venv(self, path: pathlib.Path) -> bool:
    # First check if the path parent is a venv folder.
    venv = False
    if path.parent.name in NAME_IGNORE_FOLDERS:
      venv = True
    if venv:
      return venv
    # Check if the folder IS a venv folder
    if path.name in NAME_IGNORE_FOLDERS:
      venv = True
    if venv:
      return venv

  @property
  def name(self) -> str:
    if hasattr(self, "_cached_name"):
      return self._cached_name

    path = pathlib.Path(self.path)
    while self._is_venv(path):
      path = path.parent

    if path.name == "src":
      path = path.parent

    # We should have arrived at the top-level folder name. If not, oops!
    self._cached_name = path.name
    return path.name


class Machine:
  conn: Connection
  entry: dict[str, str]
  key: Key
  name: str

  def __init__(
    self,
    conn: Connection = None,
    entry: dict[str, str] = None,
    key: Key = None,
    name: str = None,
  ) -> None:
    self.conn = conn
    self.entry = entry
    self.key = key
    self.name = name


class Key:
  file: Optional[str]
  name: str
  passphrase: Optional[str]
  passwd: Optional[str]

  def __init__(
    self,
    file: Optional[str] = None,
    name: str = None,
    passphrase: Optional[str] = None,
    passwd: Optional[str] = None,
  ) -> None:
    self.file = file
    self.name = name
    self.passphrase = passphrase
    self.passwd = passwd


class Dependancy:
  library: str
  type: str  # >, <, ==, >=, <=
  version: str

  def __init__(
    self, library: str = None, type: str = None, version: str = None
  ) -> None:
    self.library = library
    self.type = type
    self.version = version

  def __hash__(self) -> int:
    return hash((self.library, self.type, self.version))

  @property
  def specifier(self) -> SpecifierSet:
    return SpecifierSet(f"{self.type}{self.version}")
