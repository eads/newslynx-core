from newslynx.lib.pkg.validate_email import validate_email


def validate(address):
    """
    Validates an email address via regex.
    """
    return validate_email(address, check_mx=False, verify=False)

if __name__ == '__main__':
    print validate('brianabelson@gmail')
