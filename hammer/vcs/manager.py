from .git import Git
from .hg import Mercurial


class VcsProxy(object):
    VCS_HANDLERS = [
        Mercurial,
        Git
    ]

    def __init__(self, real):
        # Check the real instance type
        assert isinstance(real, tuple(self.VCS_HANDLERS))

        # Store it
        self._real = real

    @classmethod
    def init(cls, project_root, **init_kwargs):
        """ Detect the vcs type the project uses and initialize
            the correct handler to use internally.

            :param project_root: Root directory of project
            :rtype: hammer.vcs.base.BaseVcs
        """

        for handler_cls in cls.VCS_HANDLERS:
            res = handler_cls.detect(project_root, **init_kwargs)

            # Found a match
            if res:
                # Construct a proxy instance and return it
                return VcsProxy(handler_cls(project_root=project_root, **init_kwargs))

        handlers = ', '.join([x.TAG for x in cls.VCS_HANDLERS])
        raise EnvironmentError('No suitable VCS type detected (tried %s)' % handlers)

    # ============
    # Proxy logic
    # ============

    def __getattribute__(self, name):
        if name == 'VCS_HANDLERS':
            return object.__getattribute__(self, 'VCS_HANDLERS')

        return getattr(object.__getattribute__(self, "_real"), name)

    def __str__(self):  # pragma: no cover
        return str(object.__getattribute__(self, "_real"))

    def __repr__(self):  # pragma: no cover
        return repr(object.__getattribute__(self, "_real"))
