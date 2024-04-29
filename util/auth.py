def extract_credentials(request):
    body = request.body.decode("utf-8")
    body = body.split("&")
    username = body[0].split("=")[1]
    password = body[1].split("=")[1]
    out = []
    out.append(username)
    password = password.replace("%21", "!")
    password = password.replace("%40", "@")
    password = password.replace("%23", "#")
    password = password.replace("%24", "$")
    password = password.replace("%26", "&")
    password = password.replace("%28", "(")
    password = password.replace("%29", ")")
    password = password.replace("%2D", "-")
    password = password.replace("%3D", "=")
    password = password.replace("%5F", "_")
    password = password.replace("%25", "%")
    out.append(password)
    return out

def validate_password(password):
    valid = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&()-_=+"
    if len(password) < 8:
        return False
    elif not any(char.islower() for char in password):
        return False
    elif not any(char.isupper() for char in password):
        return False
    elif not any(char.isdigit() for char in password):
        return False
    elif not any(char in {'!', '@', '#', '$', '%', '^', '&', '(', ')', '-', '_', '='} for char in password):
        return False
    elif not all(char in valid for char in password):
        return False
    return True

