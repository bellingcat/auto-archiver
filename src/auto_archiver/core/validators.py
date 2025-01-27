# used as validators for config values.

def example_validator(value):
    return "example" in value

def positive_number(value):
    return value > 0