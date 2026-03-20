from rest_framework.response import Response


def res_error(msg, status_code):
    return Response({"detail": msg}, status=status_code)
