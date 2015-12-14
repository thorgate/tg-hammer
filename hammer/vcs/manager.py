from .git import Git
from .hg import Mercurial


class VcsProxy(object):
    VCS_HANDLERS = [
        Mercurial,
        Git
    ]

    def __init__(self, project_root, **init_kwargs):
        self._data = {
            'project_root': project_root,
            'init_kwargs': init_kwargs,
        }

        self._real = 'VcsProxy'

    @classmethod
    def init(cls, project_root, **init_kwargs):
        """ Detect the vcs type the project uses and initialize
            the correct handler to use internally.

            :param project_root: Root directory of project
            :rtype: hammer.vcs.base.BaseVcs
        """

        return VcsProxy(project_root=project_root, **init_kwargs)

    @classmethod
    def detect(cls, project_root, **init_kwargs):
        for handler_cls in cls.VCS_HANDLERS:
            res = handler_cls.detect(project_root, **init_kwargs)

            # Found a match
            if res:
                return handler_cls

        handlers = ', '.join([x.TAG for x in cls.VCS_HANDLERS])
        raise EnvironmentError('No suitable VCS type detected (tried %s)' % handlers)

    # ============
    # Proxy logic
    # ============

    def __getattribute__(self, name):
        real = object.__getattribute__(self, "_real")

        if real == 'VcsProxy':
            data = object.__getattribute__(self, "_data")

            cls = VcsProxy.detect(project_root=data['project_root'], **data['init_kwargs'])
            real = cls(project_root=data['project_root'], **data['init_kwargs'])

            self._real = real

        return getattr(real, name)

    def __str__(self):  # pragma: no cover
        return str(object.__getattribute__(self, "_real"))

    def __repr__(self):  # pragma: no cover
        return repr(object.__getattribute__(self, "_real"))
