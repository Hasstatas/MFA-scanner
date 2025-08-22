import re
from .overview import Strategy

class ApplicationControl(Strategy):
    id = "AC"
    name = "Application Control"

    def description(self) -> str:
        return ("Prevent the execution of executables, libraries, scripts, installers and other specific type of files on standard user/temp folders")
