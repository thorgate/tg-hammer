from __future__ import unicode_literals

import pytest

from hammer.docker_network import DockerNetworkAllocator, OutOfNetworks
from hammer.docker_network import local_cmd, create_docker_network
from ipaddress import IPv4Network


def fake_cmd(args):
    return b''


def fake_allocator(used_networks=tuple(), **kwargs):
    """

    Arguments:
        used_networks(Iterable[IPv4Network])
        **kwargs: passed on to DockerNetworkAllocator

    Returns:
        DockerNetworkAllocator
    """
    dna = DockerNetworkAllocator(fake_cmd, **kwargs)

    dna._networks_in_use = lambda: used_networks

    return dna


def test_basic_functionality():
    allocator = fake_allocator()
    assigned = allocator.assign()
    assert isinstance(assigned, IPv4Network)


def test_excludes_used_network():
    allocator = fake_allocator()
    assigned = allocator.assign()

    allocator = fake_allocator([assigned])
    assigned_next = allocator.assign()

    assert isinstance(assigned, IPv4Network)
    assert assigned_next != assigned

    block_24bit = IPv4Network('10.0.0.0/8')
    allocator = fake_allocator([block_24bit])
    assigned = allocator.assign()

    assert isinstance(assigned, IPv4Network)
    assert not assigned.overlaps(block_24bit)


def test_can_specify_prefix():
    allocator = fake_allocator()

    assigned = allocator.assign(prefix=24)
    assert assigned.prefixlen == 24

    assigned = allocator.assign(prefix=26)
    assert assigned.prefixlen == 26


def test_out_of_networks():
    only_network = IPv4Network('10.0.0.0/24')
    allocator = fake_allocator(used_networks=[only_network], pool=[only_network])

    with pytest.raises(OutOfNetworks):
        allocator.assign(prefix=24)


def test_create_network_fake():
    allocator = fake_allocator()
    assert allocator.create('test_create_network', internal=True)


@pytest.mark.skip(reason='Requires access to an actual docker server')
def test_create_network():
    # If this test fails, make sure you don't have a network called test_create_network
    # before runnig the tests
    assert create_docker_network('test_create_network', internal=True, cmd=local_cmd)
    assert not create_docker_network('test_create_network', internal=True, cmd=local_cmd)


def test_plenty_of_networks():
    used_networks = set()

    for _ in range(128):
        allocator = fake_allocator(used_networks)

        assigned = allocator.assign()
        assert assigned not in used_networks

        used_networks.add(assigned)
