import sys

try:
    import fabric.version  # NOQA

    is_fabric1 = True

    # This way we can have a single `expect UnexpectedExit` statement instead of having two separate code paths for fabric1/fabric2
    UnexpectedExit = SystemExit

    # This way we can have a single `expect Exit` when asserting for `abort` during tests
    Exit = SystemExit

except ImportError:
    from invoke.exceptions import UnexpectedExit  # NOQA

    is_fabric1 = False


if is_fabric1:
    from fabric.api import abort, prompt

else:
    from invoke.exceptions import Exit

    # Abort has been removed on fabric2
    def abort(message):
        raise Exit(message)

    # Simplified version of prompt from fabric1
    def prompt(text, default='', validate=None):
        # Set up default display
        if default != '':
            default_str = " [%s] " % str(default).strip()
        else:
            default_str = " "
        # Construct full prompt string
        prompt_str = text.strip() + default_str
        # Loop until we pass validation
        value = None
        while value is None:
            # Get input
            value = input(prompt_str) or default
            # Handle validation
            if validate:
                # Callable validate() must raise an exception if validation
                # fails.
                try:
                    value = validate(value)
                except Exception as e:
                    # Reset value so we stay in the loop
                    value = None
                    print("Validation failed for the following reason:")
                    print("    ({})\n".format(str(e)))
        # And return the value, too, just in case someone finds that useful.
        return value


def as_str(val):
    if sys.version_info >= (3, 0):
        if isinstance(val, bytes):
            return val.decode('utf-8')

        if not isinstance(val, str):
            return str(val)

    return val
