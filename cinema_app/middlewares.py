class NoLogoutForAdminSession:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.session.get_expiry_age():
            if request.user.is_superuser:
                request.session.set_expiry(0)

        response = self.get_response(request)
        return response
