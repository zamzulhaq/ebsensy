def has_role(roles, target_role):
    """
    Helper to check if a target role exists in the user's role list.
    roles can be a list of strings or a single string.
    """
    if not roles:
        return False
    
    if isinstance(roles, str):
        return roles == target_role
    
    return target_role in roles
