class InvalidCredentialException(Exception):
    """Raise exception when credentials does not match"""
    pass

class InactiveException(Exception):
    """raise exception when user is not active"""
    pass