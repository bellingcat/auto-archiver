from loguru import logger


class ArchivingContext:
    """
    Singleton context class.
    ArchivingContext._get_instance() to retrieve it if needed
    otherwise just 
    ArchivingContext.set(key, value)
    and 
    ArchivingContext.get(key, default)

    When reset is called, all values are cleared EXCEPT if they were .set(keep_on_reset=True)
        reset(full_reset=True) will recreate everything including the keep_on_reset status
    """
    _instance = None

    def __init__(self):
        self.configs = {}
        self.keep_on_reset = set()

    @staticmethod
    def get_instance():
        if ArchivingContext._instance is None:
            ArchivingContext._instance = ArchivingContext()
        return ArchivingContext._instance

    @staticmethod
    def set(key, value, keep_on_reset: bool = False):
        ac = ArchivingContext.get_instance()
        ac.configs[key] = value
        if keep_on_reset: ac.keep_on_reset.add(key)

    @staticmethod
    def get(key: str, default=None):
        return ArchivingContext.get_instance().configs.get(key, default)

    @staticmethod
    def reset(full_reset: bool = False):
        ac = ArchivingContext.get_instance()
        if full_reset: ac.keep_on_reset = set()
        ac.configs = {k: v for k, v in ac.configs.items() if k in ac.keep_on_reset}

    # ---- custom getters/setters for widely used context values

    @staticmethod
    def set_tmp_dir(tmp_dir: str):
        ArchivingContext.get_instance().configs["tmp_dir"] = tmp_dir

    @staticmethod
    def get_tmp_dir() -> str:
        return ArchivingContext.get_instance().configs.get("tmp_dir")
