try:
    from fabric import colors

    def style_args(bold):
        return dict(bold=bold)

except ImportError:
    import colors

    def style_args(bold):
        return dict(style='bold') if bold else dict()


def green(*args, **kwargs):
    bold = kwargs.pop('bold', False)
    kwargs.update(style_args(bold))

    return colors.green(*args, **kwargs)


def red(*args, **kwargs):
    bold = kwargs.pop('bold', False)
    kwargs.update(style_args(bold))

    return colors.red(*args, **kwargs)


def yellow(*args, **kwargs):
    bold = kwargs.pop('bold', False)
    kwargs.update(style_args(bold))

    return colors.yellow(*args, **kwargs)
