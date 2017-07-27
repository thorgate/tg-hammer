"""
Provides an unused network

Provides workaround for limit of 31 networks with default docker setup
by providing a free network that can be specified to docker manually.


Known performance issues when creating many docker networks,
after 50 or so networks the time it takes to create a new network
starts becoming very noticeable (several seconds) and seems to grow with O(N^2)
together with the number of iptables rules, because docker creates iptables rules
from each bridge to each bridge.
This is not an issue when creating `--internal` networks, so prefer that when possible.
"""
from __future__ import unicode_literals, absolute_import
from subprocess import check_output, CalledProcessError
from collections import deque
from itertools import chain
from ipaddress import IPv4Network, IPv4Interface
from fabric.api import sudo

__all__ = ['create_docker_network', 'DockerNetworkAllocator', 'OutOfNetworks']


DEFAULT_NETWORK_POOL = (
    IPv4Network('10.0.0.0/8'),
    IPv4Network('172.16.0.0/12'),
    IPv4Network('192.168.0.0/20'))


class OutOfNetworks(RuntimeError):
    pass


def remote_cmd(cmd):
    # Fabric doesn't have any way to call commands with
    # an actual list of arguments, and their shell_escape is
    # a complete joke...
    res = sudo(cmd)

    if res.return_code != 0:
        raise CalledProcessError(
            returncode=res.return_code,
            cmd=cmd,
            output='-- stdout -- \n%s\n-- stderr--\n%s\n' % (res.stdout, res.stderr))

    return res.stdout


def local_cmd(cmd):
    # I know... see remote_cmd
    return check_output(['sh', '-c', cmd])


def create_docker_network(name, internal=False, cmd=remote_cmd, prefix=24, pool=None):
    allocator = DockerNetworkAllocator(cmd, pool=pool)
    return allocator.create(name, internal=internal, prefix=prefix)


class DockerNetworkAllocator(object):
    def __init__(self, cmd, pool=None):
        """
        Docker network allocator

        Arguments:
            cmd(Callable[str, str]): Call a command
            pool(List[IPv4Network]): Pool of networks to assign from
        """
        self._cmd = cmd

        if pool is None:
            pool = DEFAULT_NETWORK_POOL

        # Ensure it is sorted so we can be efficient when finding a free network
        self.pool = list(sorted(pool))

    def _docker(self, args):
        # lord have mercy
        cmd = ' '.join("'{}'".format(arg) for arg in chain(['docker'], args))
        output = self._cmd(cmd).decode('utf8').strip()

        if output == '':
            return []

        return [line.strip() for line in output.split('\n')]

    def _networks_in_use(self):
        return list(chain(
            (
                # Locally used networks
                IPv4Interface(inet).network
                for inet in self._cmd("ip -4 addr | grep 'inet ' | awk '{ print $2 }'").split()
                if inet != ''
            ),
            (
                # Already routed ipv4 networks
                IPv4Network(network)
                for network in self._cmd("ip -4 route list | grep '^[0-9]' | awk '{ print $1 }'").split()
                if network != ''
            )
        ))

    def _proposed_network(self, prefix):
        networks_in_pool = (
            subnet
            for network in self.pool
            for subnet in network.subnets(new_prefix=prefix)
        )

        used_networks = deque(sorted(self._networks_in_use()))

        for network in networks_in_pool:

            # This while block is purely for optimization,
            # due to sorting of both networks_in_pool and used_networks
            # this used network can never interfere again, so don't waste time on it.
            while used_networks and \
                    used_networks[0].broadcast_address < network.network_address and \
                    not network.overlaps(used_networks[0]):
                used_networks.popleft()

            if not any(network.overlaps(used) for used in used_networks):
                return network

    def assign(self, prefix=24):
        """
        Arguments:
            prefix_length(int): Network prefix length  (e.g. `24`  for `/24`)
        """
        proposed_network = self._proposed_network(prefix)

        if proposed_network is None:
            raise OutOfNetworks("Out of networks, contact your server administrator")

        return proposed_network

    def create(self, name, internal=False, prefix=24):
        """
        Create a new docker network if it does not already exist

        Arguments:
            name(str): Network name
            internal(bool): Internal network (--internal)
            prefix(int): Network prefix

        Returns:
            bool: True if network was created, False if it already existed
        """
        existing = self._docker(['network', 'ls', '--format', '{{.Name}}'])

        if name in existing:
            return False

        cmd = chain(
            ('docker', 'network', 'create'),
            ('--internal',) if internal else (),
            ('--subnet', self.assign(prefix=prefix).exploded, name))
        self._cmd(' '.join(cmd))

        return True
