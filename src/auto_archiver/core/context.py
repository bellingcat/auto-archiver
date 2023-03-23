
class ArchivingContext:
    """
    Singleton context class.
    ArchivingContext._get_instance() to retrieve it if needed
    otherwise just 
    ArchivingContext.set(key, value)
    and 
    ArchivingContext.get(key, default)
    """
    _instance = None

    def __init__(self):
        self.configs = {}

    @staticmethod
    def get_instance():
        if ArchivingContext._instance is None:
            ArchivingContext._instance = ArchivingContext()
        return ArchivingContext._instance

    @staticmethod
    def set(key, value):
        ArchivingContext.get_instance().configs[key] = value

    @staticmethod
    def get(key: str, default=None):
        return ArchivingContext.get_instance().configs.get(key, default)

    # ---- custom getters/setters for widely used context values

    @staticmethod
    def set_tmp_dir(tmp_dir: str):
        ArchivingContext.get_instance().configs["tmp_dir"] = tmp_dir

    @staticmethod
    def get_tmp_dir() -> str:
        return ArchivingContext.get_instance().configs.get("tmp_dir")
