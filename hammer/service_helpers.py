import os

from copy import copy
from StringIO import StringIO

from fabric import colors
from fabric.api import abort, env, get, put, require, sudo


DAEMON_TYPES = {
    'systemd': {
        'daemon_cmd': 'systemctl %(action)s %(name)s',
        'target_dir': '/etc/systemd/system',
        'file_extension': 'service',
    },
    'supervisor': {
        'daemon_cmd': 'supervisorctl %(action)s %(name)s',
        'target_dir': '/etc/supervisord/conf.d/',
        'file_extension': 'conf',
    },
    'upstart': {
        'daemon_cmd': 'service %(name)s %(action)s',
        'target_dir': '/etc/init',
        'file_extension': 'conf',
    },
}


def get_service_daemon(daemon_type=None, daemon_target_dir=None):
    require('service_daemon')

    daemon_type = daemon_type or env.service_daemon

    if daemon_type not in DAEMON_TYPES:
        abort('Provided `service_daemon` %s is invalid. Supported daemon types are: %s' % (daemon_type, ', '.join(DAEMON_TYPES)))

    daemon_conf = copy(DAEMON_TYPES[daemon_type])

    # Support loading target_dir from env
    daemon_conf['target_dir'] = daemon_target_dir or getattr(env, 'service_daemon_target_dir', daemon_conf['target_dir'])

    if not daemon_conf['target_dir']:
        abort('`env.service_daemon_target_dir` must not be empty')

    return daemon_type, daemon_conf


def install_services(services, daemon_type=None, daemon_target_dir=None):
    """Install provided services by uploading configuration files to the detected ``daemon_type`` specific directory

    :param services: List of services to install where each item is a tuple with the signature: ``(target_name, file_data)``
    :param daemon_type: Can be used to override ``env.service_daemon`` value
    :param daemon_target_dir: Can be used to override ``env.service_daemon_target_dir`` value

    **Warning:**
        For supervisor the default include dir is `/etc/supervisord/conf.d/`, this directory must be included
        in the global supervisor configuration.
    """

    daemon_type, daemon_conf = get_service_daemon(daemon_type=daemon_type, daemon_target_dir=daemon_target_dir)

    for target_name, file_data in services:
        target_path = os.path.join(daemon_conf['target_dir'], '%s.%s' % (target_name, daemon_conf['file_extension']))

        put(local_path=StringIO(file_data), remote_path=target_path, use_sudo=True)

    if daemon_type == 'supervisor':
        # Ensure configuration files are reloaded
        manage_service('', 'reread', daemon_type=daemon_type)
        manage_service('', 'update', daemon_type=daemon_type)

    elif daemon_type == 'systemd':
        # Ensure configuration files are reloaded
        manage_service('', 'daemon-reload', daemon_type=daemon_type)

        # Ensure services are started on startup
        manage_service([target_name for target_name, file_data in services], 'enable', daemon_type=daemon_type)


def install_services_cp(services, daemon_type=None, daemon_target_dir=None):
    """Install provided services by copying the remote file to the detected ``daemon_type`` specific directory

    :param services: List of services to install where each item is a tuple with the signature:
        ``(target_name, remote_file_path[, transform])``
    :param daemon_type: Can be used to override ``env.service_daemon`` value
    :param daemon_target_dir: Can be used to override ``env.service_daemon_target_dir`` value

    The remote_file_path supports the following keywords:

    -  ``${DAEMON_TYPE}``: Replaced with the detected daemon type (see `DAEMON_TYPES`)
    -  ``${DAEMON_FILE_EXTENSION}``: Replaced with the `file_extension` value for the detected daemon type (see `DAEMON_TYPES`)

    `transform` is an optional function w/ signature `(target_name, remote_file_data) -> (target_name, remote_file_data)` which
      can be used for dynamic service configuration

    **Warning:**
        For supervisor the default include dir is `/etc/supervisord/conf.d/`, this directory must be included
        in the global supervisor configuration.
    """

    prepared_services = []
    daemon_type, daemon_conf = get_service_daemon(daemon_type=daemon_type, daemon_target_dir=daemon_target_dir)

    for parts in services:
        if len(parts) == 3:
            target_name, remote_file_path, transform = parts

        else:
            target_name, remote_file_path = parts
            transform = None

        # Construct remote path
        remote_file_path = remote_file_path.replace('${DAEMON_TYPE}', daemon_type)
        remote_file_path = remote_file_path.replace('${DAEMON_FILE_EXTENSION}', daemon_conf['file_extension'])

        # Download the remote file
        buf = StringIO()
        get(remote_file_path, buf)

        the_item = (target_name, buf.getvalue())

        if transform:
            the_item = transform(*the_item)

        # store it in prepared services
        prepared_services.append(the_item)

    # Use standard install_services to install them
    return install_services(prepared_services, daemon_type=daemon_type, daemon_target_dir=daemon_target_dir)


def manage_service(names, action, raise_errors=True, daemon_type=None):
    """Perform `action` on services

    :param names: Can be a list of services or a name of a single service to control
    :param action: Action that should be executed for the given services
    :param raise_errors: A way to control if errors generated by command should be captured by fabric or not. By default
    it is set to raise errors
    :param daemon_type: Can be used to override env.service_daemon value
    """
    if not isinstance(names, (list, tuple)):
        names = [names, ]

    daemon_type, daemon_conf = get_service_daemon(daemon_type=daemon_type)

    for name in names:
        full_cmd = daemon_conf['daemon_cmd'] % {
            'name': name,
            'action': action,
        }

        if raise_errors:
            sudo(full_cmd)
        else:
            try:
                sudo(full_cmd, warn_only=True)

            except Exception as e:
                print(colors.red('Failed: %s', full_cmd))
                print(e)
                print('')
