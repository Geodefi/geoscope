import sys
from web3 import Web3

from .globals.exceptions import PythonVersionException
from .classes import Stateful
from .classes import Logable


def check_python_version() -> None:
    """
    Checks that the python version running is sufficient and exits if not.
    """
    if sys.version_info <= (3, 9) and sys.version_info >= (3, 10):
        raise PythonVersionException
        sys.exit()


class Telescope(Logable):
    """
    Telescope is a Daemon:
    * Telescope listens beacon chain, while refreshing the connection periodically.
    * When there is a new block, telescope updates its database(state).
      * After the update given triggers are checked.
        * According to changes (pending, effective, non-effective); A Trigger updates its own state.
      * When a trigger is triggered, given actions of the triggers are executed.
    """

    # TODO_comment: telescope should not fail when a daemon fails, but maybe sometimes some exceptions should cause that.

    def __init__(self):
        check_python_version()
        Logable.__init__(self, log_filename="Telescope")

        # TODO_unrelated delete this:  Note that instead of doing this we can create multiple daemons
        # for example one can handle checkpoints and data verification
        # one can be very slow and solely focus on validator proposal verification
        # and one can be responsible from updating validator balance and price merkle roots.

    def run():
        # initiate daemons with triggers as params
        # check for checkpoints
        # handle state for all stateful instances (config)
        # daemons.run()

        pass
