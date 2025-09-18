from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("CookieJWTAuthentication called")
        
        # 1. Try cookie
        raw_token = request.COOKIES.get("access_token")
        print("Cookie token:", raw_token)

        # 2. Fallback to Authorization header
        if raw_token is None:
            header = self.get_header(request)
            if header is not None:
                raw_token = self.get_raw_token(header)

        # 3. If still missing → unauthenticated
        if raw_token is None:
            print("No token found in cookie or header")
            return None

        # 4. Validate & return user
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
