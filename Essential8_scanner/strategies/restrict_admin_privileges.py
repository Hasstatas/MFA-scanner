from .overview import Strategy

class RestrictAdminPrivileges(Strategy):
    id = "RAP"
    name = "Restrict Admin Privileges"
    def description(self) -> str:
        return "Privileged access to systems and applications are validated when requested and follow a proper procedure"