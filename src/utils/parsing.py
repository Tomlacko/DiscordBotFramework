from keyword import iskeyword

def is_valid_variable_name(name: str) -> bool:
    return len(name)>0 and name.isidentifier() and not iskeyword(name)

#WRONG, dots are supported
# def is_valid_import_path(import_path: str) -> bool:
#     if len(import_path) == 0:
#         return False
#     for part in import_path.split('.'):
#         if not is_valid_variable_name(part):
#             return False
#     return True