from keyword import iskeyword


def is_valid_identifier(key: str) -> bool:
    return isinstance(key, str) and key.isidentifier()

def is_valid_variable_name(name: str) -> bool:
    return isinstance(name, str) and name.isidentifier() and not iskeyword(name)

