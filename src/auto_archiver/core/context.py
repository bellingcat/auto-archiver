""" ArchivingContext provides a global context for managing configurations and temporary data during the archiving process.

This singleton class allows for:
- Storing and retrieving key-value pairs that are accessible throughout the application lifecycle.
- Marking certain values to persist across resets using `keep_on_reset`.
- Managing temporary directories and other shared data used during the archiving process.

### Key Features:
- Creates a single global instance.
- Reset functionality allows for clearing configurations, with options for partial or full resets.
- Custom getters and setters for commonly used context values like temporary directories.

"""

class ArchivingContext:
    """
    Singleton context class for managing global configurations and temporary data.

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