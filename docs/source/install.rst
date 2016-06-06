Install
=======

Install tg-hammer::

    pip install tg-hammer


Then use it in your fabfile::

    from hammer.vcs import Vcs


    # Provide configuration to the VCS logic
    # Note: You can omit both of these keys when you
    #       want them to be retrieved from fabrics `env` dictionary
    vcs_config = {
        'use_sudo': False,              # Set to True if your target machine requires elevated privileges when running vcs commands
        'code_dir': '/srv/project',     # Directory on the target machine that will be operated on
    }
    vcs = Vcs.init(project_root='path to root dir of project', **vcs_config)

    # Now you can use the vcs api
    vcs.repo_url()  # > git@github.com:thorgate/tg-hammer.git
