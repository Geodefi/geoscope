from os import path, getcwd
from typing import Callable
from enum import Enum
import pandas as pd

from ..globals.exceptions import (
    StateCreationException,
    DuplicateStateException,
    UnknownKeyException,
    VerificationException,
)
from .logable import Logable
from ..globals.config import CONFIG


class Status(str, Enum):
    INITIATED = "initiated"
    VERIFYING = "verifying"
    WAITING = "waiting"
    ACTIVE = "active"
    UPDATING = "updating"
    STOPPED = "stopped"


class MetaState:
    """
    This base class allows user to read all of the instances of Stateful to be able to display/report it when needed.
    Also, it makes sure that all instances have a unique name on creation.
    """

    names: set = set([])
    instances: dict = dict({})

    def __init__(self, name: str):
        if name in MetaState.names:
            raise DuplicateStateException
        MetaState.names.add(name)
        MetaState.instances[name] = self


class Stateful(MetaState, Logable):
    """
    When a bigdata is stored in the memory, it is good to have a way to create a standard way to handle it.
    So, we are using a pandas dataframe.
    State can be saved to the storage with a checkpoint and can be read back with rollup.
    State can be verified when needed with verify() after calling register_verification().
    Thus, this base class is inherited by all other base classes that will rely on data manipulation.
    Dataframe types are always ensured, and optionally but as a defult it is always sorted.
    """

    def __init__(self, name: str, index: str, columns: dict[str, str]):
        try:
            if not name or not columns:
                raise

            if index in columns:
                raise
            MetaState.__init__(self, name=name)
            Logable.__init__(self, name=name)

            self.name = name
            self.__index = index
            self.__columns = columns
            self.state: pd.DataFrame = pd.DataFrame(
                {col: pd.Series(dtype=t) for col, t in columns.items()},
                index=pd.Index([], name=index),
            )
        except:
            raise StateCreationException

    @property
    def file_name(self) -> str:
        return f"{self.name}.json"

    @property
    def file_path(self) -> str:
        return path.join(getcwd(), CONFIG.state.directory, self.file_name)

    def set_status(self, status: Status):
        self.logger.debug(f"{self.name}:status:{status}")
        self.status: Status = status

    def register_verification(self, verification: Callable):
        """
        Sets a function as a verification mechanism to be used when verify() is called.
        This is optional, StateDaemon will not verify/save/rollup if not set.
        """
        self.verifiable: bool = True
        self.verification: Callable = verification

    def checkpoint(self):
        """
        Saves the state as a json file to given path
        """
        try:
            self.state.reset_index().to_json(self.file_path)
        except:  # pathnotfound
            raise

    def rollup(self):
        """
        Reads the checkpoint for the given state.
        Does nothing if no checkpoint is found at the given directory.
        """
        if path.exists(self.file_path):
            try:
                self.logger.info(f"{self.name}: checkpoint detected.")
                self.state: pd.DataFrame = pd.read_json(
                    self.file_path,
                    dtype=self.__columns,
                    convert_dates=False,  # dont convert columns to dates
                    convert_axes=False,  # dont convert axes to 'proper' dtypes
                )
                self.state.set_index(self.__index, inplace=True)
                self._sort()

            except:
                raise
        else:
            self.logger.info(f"{self.name}: no checkpoint detected.")
            pass

    def verify(self, *args, **kwargs):
        """
        if register_verification() is called, verifies the state when needed:
        self.verification should be a function

        Else, does nothing.
        """
        if kwargs.get("mode") not in ["fix", "alert", "quit"]:
            raise

        if self.verifiable:
            try:
                prev_status: Status = self.status
                self.set_status(Status.VERIFYING)
                self.verification(*args, **kwargs)
                self.set_status(prev_status)

            except:
                raise VerificationException

        else:
            pass

    def _sort(self):
        """
        Sort the state
        """
        self.state.sort_index(inplace=True)

    def update(self, index, data: dict, sort: bool = True):
        """
        A global way to update one row of the state.
        Takes a dictionary as {column_name:data,...} and mutates the state.
        Then, sorts by index and reenforces the state types.
        """
        prev_status: Status = self.status
        self.set_status(Status.UPDATING)

        try:  # can fail to update
            if not set(data.keys()).issubset(set(self.__columns.keys())):
                raise UnknownKeyException

            for x, y in data.items():
                self.state.at[index, x] = y

            if sort:
                self._sort()

            # enforce column dtypes for the state
            self.state.astype(self.__columns)

            self.set_status(prev_status)
        except:
            raise

    def update_many(
        self,
        data: dict[dict],
        as_index: str = None,
        sort: bool = True,
        mode: str = "cell",
    ):
        """
        A global way to update many rows of the state.
        Takes a dictionary as {index:{column_name:data,...}...} and mutates the state.
        Then, sorts by index and reenforces the state types.
        """

        prev_status: Status = self.status
        self.set_status(Status.UPDATING)

        try:  # can fail
            if as_index:
                self.state.reset_index(inplace=True).set_index(
                    as_index, inplace=True
                )

            if len(self.state.index) == 0:
                # if df is empty it is safe to assume that dict has all the keys,
                # handle in case of an error tho, so no fillna.
                self.state: pd.DataFrame = pd.DataFrame().from_dict(
                    data, orient="index"
                )
                self.state.index.name: str = self.__index

            elif mode == "merge":
                # if all the column values are present in the given data, then we can actually merge.
                # faster than pandas merge
                # keeps the data in case of a conflict
                new_data: dict = self.state.to_dict(orient="index") | data
                # todo_task_now: check if this fails when
                self.state: pd.DataFrame = pd.DataFrame().from_dict(
                    new_data, orient="index"
                )
                self.state.index.name: str = self.__index

            elif mode == "cell":
                for idx, row in data.items():
                    for k, v in row.items():
                        self.state.at[idx, k] = v

            else:
                raise  # unknown mode
        except:
            raise

        if as_index:
            self.state.reset_index(inplace=True).set_index(
                self.__index, inplace=True
            )

        if sort:
            self._sort()

        # enforce column dtypes for the state -> this is not optional for a reason.
        self.state.astype(self.__columns)

        self.set_status(prev_status)
