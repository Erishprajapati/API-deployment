from django.contrib.auth import get_user_model, authenticate
from typing import Union, Type
from authentication.exceptions import InactiveException, InvalidCredentialException

User = get_user_model()
class AuthenticateService:
    @staticmethod
    def authenticate_user(request, username:str, password:str)->Union[Type[User], str, None]:
        """authentication of user"""

        user = User.objects.filter(username = username).first()
        if user is None:
            raise InvalidCredentialException()
        if not user.is_active:
            raise InactiveException()
        user = authenticate(request, username = username, password = password)


        if not user:
            raise InvalidCredentialException()
        return user