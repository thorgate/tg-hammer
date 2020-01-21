# -*- coding: utf-8 -*-
import os

import pytest

from hammer.util import UnexpectedExit, Exit


def test_fixture_correct_data(repo):
    if repo.vcs_type == 'git':
        assert repo
        assert repo.vcs_type == 'git'
        assert getattr(repo, '_repo', None) == repo.vcs_type
        assert getattr(repo, '_real_dir', None) == '.git'

    else:
        assert repo
        assert repo.vcs_type == 'hg'
        assert getattr(repo, '_repo', None) == repo.vcs_type
        assert getattr(repo, '_real_dir', None) == '.hg'


def test_repo_exists_and_is_correct_type(repo):
    assert repo
    assert hasattr(repo, '_repo')
    assert repo.vcs_type == getattr(repo, '_repo')
    assert os.path.exists(repo.repo_dir)

    assert os.path.exists(os.path.join(repo.repo_dir, getattr(repo, '_real_dir')))

    assert repo.check_status()


def test_repo_create_initial_commit(repo):
    assert repo.create_commits_master_1()
    assert repo.get_commit_messages() == ['3.txt', '2.txt', '1.txt']


def test_vcs_detect(repo):
    obj = repo.get_vcs()

    assert obj
    assert obj.NAME == repo.handler_name
    assert obj.TAG == repo.vcs_type


def test_vcs_remote_url(repo, get_context):
    context = get_context('staging.hammer')

    obj = repo.get_vcs(context=context)

    # Should return None if no remote url
    assert obj.repo_url() is None

    # Set remote url
    repo.add_remote()

    # Check it again
    got = obj.repo_url()
    assert got == repo.expected_remote

    # Push to remote (actually just a different dir on the master machine)
    repo.push()


def test_vcs_clone(repo, get_context):
    # set host string
    context = get_context('staging.hammer')

    obj = repo.get_vcs(context=context)
    obj.sudo('rm -rf /srv/%s_project' % repo.vcs_type)
    obj.clone()

    # Also test vcs_version result
    version_info = obj.version()

    assert list(version_info) == [
        repo.commit_hash['3.txt'],
        repo.default_branch,
        '3.txt',
        repo.user_full,
    ]

    # Also test that we get correct branch
    assert obj.get_branch() == repo.default_branch


def test_vcs_deploy(repo, get_context):
    # make another commit
    repo.store_commit_hash('5.txt')

    # test that it was stored
    assert repo.commit_hash.get('5.txt', None)

    # Push to remote
    repo.push()

    # set host string
    context = get_context('staging.hammer')

    # Run deploy
    obj = repo.get_vcs(context=context)

    # Remember the version info
    version_info = list(obj.version())

    # The version info should still be same
    assert version_info == list(obj.version())

    # Run deploy (without commit hash)
    obj.update()

    # The version info should be correct
    assert list(obj.version()) == [
        repo.commit_hash['5.txt'],
        repo.default_branch,
        '5.txt',
        repo.user_full,
    ]

    # Also test that we get correct branch
    assert obj.get_branch() == repo.default_branch

    # make another commit
    repo.store_commit_hash('6.txt')

    # test that it was stored
    assert repo.commit_hash.get('6.txt', None)

    # Push to remote
    repo.push()

    # The version info should still be same
    assert list(obj.version()) == [
        repo.commit_hash['5.txt'],
        repo.default_branch,
        '5.txt',
        repo.user_full,
    ]

    # Run deploy (without commit hash)
    obj.update()

    # The version info should be correct
    assert list(obj.version()) == [
        repo.commit_hash['6.txt'],
        repo.default_branch,
        '6.txt',
        repo.user_full,
    ]

    # Also test that we get correct branch
    assert obj.get_branch() == repo.default_branch


def test_stable_branch(repo, get_context):
    # make another commit (stable branch)
    repo.store_commit_hash('stable-1', branch='stable')
    assert repo.commit_hash.get('stable-1', None)
    repo.push(branch='stable')

    # Make a different commit (master)
    repo.store_commit_hash('dogs.png', branch=[repo.default_branch])
    assert repo.commit_hash.get('dogs.png', None)
    repo.push()

    # Setup another server on the target host
    context = get_context('staging.hammer')

    # get vcs object and set a new code dir
    obj = repo.get_vcs(code_dir='/srv/%s_stable' % repo.vcs_type, context=context)
    assert obj.code_dir == '/srv/%s_stable' % repo.vcs_type

    # Ensure target is empty
    obj.sudo('rm -rf %s' % obj.code_dir)

    # deploy stable branch to target
    obj.clone('stable')

    # The version info should be correct
    assert list(obj.version()) == [
        repo.commit_hash['stable-1'],
        'stable',
        'stable-1',
        repo.user_full,
    ]

    # make another commit (stable branch)
    repo.store_commit_hash('message of stable-2', branch=['stable'], extra_files=[
        'anwser.sh',
        'coffee.py',
        'stash.geo',
        ['1.txt', 'Hello world!'],
    ])
    assert repo.commit_hash.get('message of stable-2', None)
    repo.push(branch='stable')

    # Run vcs_log to verify we are still in the clear
    result = obj.deployment_list()

    assert 'forwards' in result
    assert 'revset' in result
    assert result['revset']
    assert result['forwards'] == [
        '%(hash)s %(branch)s %(user)s %(message)s' % {
            'hash': repo.commit_hash['message of stable-2'],
            'branch': 'stable',
            'user': repo.user_full,
            'message': 'message of stable-2',
        }
    ]

    # Also check that we get correct changed files
    files = obj.changed_files(result['revset'])
    assert sorted(files) == [
        'A anwser.sh',
        'A coffee.py',
        'A message of stable-2',
        'A stash.geo',
        'M 1.txt',
    ]

    # The version info should still be same as the original commit
    #  e.g. we verify that the above functions don't actually change
    #  the working tree.
    assert list(obj.version()) == [
        repo.commit_hash['stable-1'],
        'stable',
        'stable-1',
        repo.user_full,
    ]

    # Deploy it
    obj.update()

    # Check that we have the correct version
    assert list(obj.version()) == [
        repo.commit_hash['message of stable-2'],
        'stable',
        'message of stable-2',
        repo.user_full,
    ]

    # Add new commit to master
    repo.store_commit_hash('world is kind', branch=[repo.default_branch], extra_files=[
        ['3.txt', 'world is kind!'],
    ])
    assert repo.commit_hash.get('world is kind', None)
    repo.push()

    # Run vcs_log to verify we are still in the clear
    assert obj.deployment_list() == {'message': "Already at target revision"}

    # Merge ->stable
    repo.merge_to_stable('0:merge->stable')
    assert repo.commit_hash.get('0:merge->stable', None)
    repo.push('stable')

    # Run vcs_log to verify we are still in the clear
    result = obj.deployment_list()
    assert 'forwards' in result
    assert 'revset' in result
    assert result['revset']

    merge_msg = '0:merge->stable' if repo.vcs_type == 'hg' else "Merge branch 'master' into stable"
    expected_forwards = [
        '%(hash)s %(branch)s %(user)s %(message)s' % {
            'hash': repo.commit_hash['0:merge->stable'],
            'branch': 'stable',
            'user': repo.user_full,
            'message': merge_msg,
        }
    ]

    # Git will also create the commits on stable
    #  if not merged with fast-forward
    if repo.vcs_type == 'git':
        expected_forwards = [
            '%s stable %s dogs.png' % (repo.commit_hash['dogs.png'], repo.user_full),
            '%s stable %s world is kind' % (repo.commit_hash['world is kind'], repo.user_full),
        ] + expected_forwards

    assert result['forwards'] == expected_forwards

    # Also check that we get correct changed files
    files = obj.changed_files(result['revset'])
    assert sorted(files) == [
        'A dogs.png',
        'A world is kind',
        'M 3.txt',
    ]

    # Deploy & Check version
    obj.update()
    assert list(obj.version()) == [
        repo.commit_hash['0:merge->stable'],
        'stable',
        merge_msg,
        repo.user_full,
    ]

    # get reverse log
    target_version = repo.commit_hash['message of stable-2']
    result = obj.deployment_list(target_version)

    # check if its valid
    assert 'backwards' in result
    assert 'revset' in result
    assert result['revset']

    if repo.vcs_type == 'git':
        expected_backwards = [
            '%(hash)s %(branch)s %(user)s %(message)s' % {
                'hash': repo.commit_hash['0:merge->stable'],
                'branch': 'stable',
                'user': repo.user_full,
                'message': merge_msg,
            },
            '%s master|stable %s world is kind' % (repo.commit_hash['world is kind'], repo.user_full),
            '%s master|stable %s dogs.png' % (repo.commit_hash['dogs.png'], repo.user_full)
        ]
    else:
        expected_backwards = [
            '%(hash)s %(branch)s %(user)s %(message)s' % {
                'hash': repo.commit_hash['0:merge->stable'],
                'branch': 'stable',
                'user': repo.user_full,
                'message': merge_msg,
            },
            '%s %s %s world is kind' % (repo.commit_hash['world is kind'], repo.default_branch, repo.user_full),
        ]

    assert result['backwards'] == expected_backwards

    # Test changed files
    files = obj.changed_files(result['revset'])
    assert sorted(files) == [
        'A dogs.png',
        'A world is kind',
        'M 3.txt',
    ]

    # Test changed files with single regex
    files = obj.changed_files(result['revset'], r'(\.png|\.txt)$')
    assert sorted(files) == [
        'A dogs.png',
        'M 3.txt',
    ]

    # Test changed files with multi regex
    files = obj.changed_files(result['revset'], [r'^A .+\.png$', r'^M '])

    assert sorted(files) == [
        'A dogs.png',
        'M 3.txt',
    ]

    # Apply backwards action
    obj.update(target_version)
    assert list(obj.version()) == [
        repo.commit_hash['message of stable-2'],
        'stable',
        'message of stable-2',
        repo.user_full,
    ]

    # Go back to tip
    obj.update()
    assert list(obj.version()) == [
        repo.commit_hash['0:merge->stable'],
        'stable',
        merge_msg,
        repo.user_full,
    ]

    # Go back again
    obj.update(target_version)
    assert list(obj.version()) == [
        repo.commit_hash['message of stable-2'],
        'stable',
        'message of stable-2',
        repo.user_full,
    ]

    # Go back to tip using commit hash
    obj.update(repo.commit_hash['0:merge->stable'])
    assert list(obj.version()) == [
        repo.commit_hash['0:merge->stable'],
        'stable',
        merge_msg,
        repo.user_full,
    ]


def test_vcs_deploy_with_branchname(repo, get_context):
    if repo.vcs_type == 'git':
        branch_name = 'featureXXX/YYY/ZZZ'

        # Make another commit
        repo.store_commit_hash('7.txt', branch=branch_name)

        # test that it was stored
        assert repo.commit_hash.get('7.txt', None)

        # Push to remote
        repo.push(branch=branch_name)

        # set host string
        context = get_context('staging.hammer')

        # Run deploy
        obj = repo.get_vcs(context=context)

        # Run deploy with branch name
        obj.update(revision=branch_name)

        # The version info should be correct
        assert list(obj.version()) == [
            repo.commit_hash['7.txt'],
            branch_name,
            '7.txt',
            repo.user_full,
        ]

        # Also test that we get correct branch
        assert obj.get_branch() == branch_name

        # Clean up this test (somewhat)
        obj.update(repo.default_branch)


def test_vcs_deploy_with_wrong_branchname_or_revision(repo, get_context):
    if repo.vcs_type == 'git':
        # set host string
        context = get_context('staging.hammer')

        # Run deploy
        obj = repo.get_vcs(context=context)

        # Run deploy with branch that does not exist in origin.
        with pytest.raises(Exit):
            obj.update(revision='feature-branch/does-not-exist-in-remote-server')

        # Run deploy with a revision hash that does not exist in the repo.
        with pytest.raises(UnexpectedExit):
            obj.update(revision='4c92374f88ad10bf4b658355d2784540e4192927')


def test_vcs_deployment_list(repo, get_context):
    branch_name = 'top_secret'

    # Make a commit to top_secret
    repo.store_commit_hash('8.txt', branch=branch_name)

    # Test that it was stored
    assert repo.commit_hash.get('8.txt', None)

    # Push to remote
    repo.push(branch=branch_name)

    # Make a commit to master
    repo.store_commit_hash('9.txt', branch=[repo.default_branch])

    # Test that it was stored
    assert repo.commit_hash.get('9.txt', None)

    # Push to remote
    repo.push(branch=repo.default_branch)

    # set host string
    context = get_context('staging.hammer')
    obj = repo.get_vcs(context=context)

    # Need to do this to avoid asking the user which branch to use.
    original_get_branch = obj._real.get_branch
    obj._real.get_branch = lambda *args: repo.default_branch
    deployment_list = obj.deployment_list()
    obj._real.get_branch = original_get_branch

    assert 'forwards' in deployment_list
    assert 'revset' in deployment_list

    inner_list = deployment_list['forwards']

    list_without_hashes = [' '.join(i.split()[1:]) for i in inner_list]

    if repo.vcs_type == 'git':
        assert list_without_hashes == [
            '{} Testing user <test@test.sdf> 9.txt'.format(repo.default_branch)
        ]
    else:
        assert list_without_hashes == [
            '{} Testing user <test@test.sdf> dogs.png'.format(repo.default_branch),
            '{} Testing user <test@test.sdf> world is kind'.format(repo.default_branch),
            '{} Testing user <test@test.sdf> 9.txt'.format(repo.default_branch)
        ]

    obj.update(branch_name)

    # Make a commit to top_secret
    repo.store_commit_hash('10.txt', branch=[branch_name])

    # Push to top_secret
    repo.push(branch=branch_name)

    deployment_list = obj.deployment_list()

    assert 'forwards' in deployment_list
    assert 'revset' in deployment_list

    inner_list = deployment_list['forwards']

    list_without_hashes = [' '.join(i.split()[1:]) for i in inner_list]

    assert list_without_hashes == ['{} Testing user <test@test.sdf> 10.txt'.format(branch_name)]


def test_deployment_list_revision_flag(repo, get_context):
    # set host string
    context = get_context('staging.hammer')
    obj = repo.get_vcs(context=context)

    evil_branch = 'feature-branch/does-not-exist-in-remote-server'

    # Test if adding a commit_id that does exist fails appropriately.
    with pytest.raises(UnexpectedExit):
        obj.deployment_list(revision='4c92374f88ad10bf4b658355d2784540e4192927')

    if repo.vcs_type == 'git':
        # Test that adding a short commit_id fails appropriately.
        with pytest.raises(Exit):
            obj.deployment_list(revision='4c9237')

        # Test that deploying a branch which starts with origin fails appropriately.
        with pytest.raises(Exit):
            obj.deployment_list(revision='origin/{}'.format(evil_branch))

    # Test that adding a commit_id which does exist in the repo fails appropriately.
    with pytest.raises(Exit if repo.vcs_type == 'git' else UnexpectedExit):
        obj.deployment_list(revision=evil_branch)

    # get reverse log
    target_version = repo.commit_hash['message of stable-2']
    obj.deployment_list(target_version)

    # Add the evil branch to the repo
    repo.store_commit_hash('11.txt', branch=evil_branch)
    repo.push(branch=evil_branch)

    deployment_list = obj.deployment_list(revision=evil_branch)
    assert 'forwards' in deployment_list
    assert 'revset' in deployment_list

    inner_list = deployment_list['forwards']
    forwards_list_without_hashes = [' '.join(i.split()[1:]) for i in inner_list]

    if repo.vcs_type == 'git':
        assert forwards_list_without_hashes == [
            '{}|top_secret Testing user <test@test.sdf> 10.txt'.format(evil_branch),
            '{} Testing user <test@test.sdf> 11.txt'.format(evil_branch),
        ]
    else:
        assert forwards_list_without_hashes == [
            'top_secret Testing user <test@test.sdf> 10.txt',
            '{} Testing user <test@test.sdf> 11.txt'.format(evil_branch),
        ]

    revset = deployment_list['revset']

    if repo.vcs_type == 'git':
        assert revset == ' ..origin/{}'.format(evil_branch)
    else:
        assert revset == '.::{}'.format(evil_branch)

    obj.update(target_version)


def test_multiple_commits_question(repo, monkeypatch, get_context):
    if repo.vcs_type == 'git':
        repo.store_commit_hash('12.txt', branch=['master'])
        repo.merge_to_stable('1:merge->stable')
        assert repo.commit_hash.get('1:merge->stable', None)

        repo.push(branch='master')
        repo.push(branch='stable')

        # set host string
        context = get_context('staging.hammer')

        obj = repo.get_vcs(context=context)
        obj.update(repo.commit_hash['1:merge->stable'])

        branch = obj.get_branch(repo.commit_hash['1:merge->stable'])
        assert branch == 'stable'

        monkeypatch.setattr('hammer.vcs.git.ask_input', lambda x: '2')

        branch = obj.get_branch(repo.commit_hash['12.txt'])
        assert branch == 'stable'

        assert obj._branch_cache == {repo.commit_hash['1:merge->stable']: 'stable',
                                     repo.commit_hash['12.txt']: 'stable'}

        obj._branch_cache[repo.commit_hash['1:merge->stable']] = 'very_very_very_stable'

        branch = obj.get_branch(repo.commit_hash['1:merge->stable'])

        assert branch == 'very_very_very_stable', repr((branch, 'very_very_very_stable'))


def test_commit_messages_with_formatting_chars(repo, get_context):
    repo.store_commit_hash('HELLO %', branch=[repo.default_branch])
    repo.store_commit_hash('Commit {} message', branch=[repo.default_branch])
    repo.store_commit_hash('Django {% include %} template', branch=[repo.default_branch])
    repo.push(branch=repo.default_branch)

    context = get_context('staging.hammer')

    obj = repo.get_vcs(context=context)

    # This line failed before fixing the percent sign error.
    obj.deployment_list(revision=repo.commit_hash['HELLO %'])

    # These one failed a bit later
    obj.deployment_list(revision=repo.commit_hash['Commit {} message'])
    obj.deployment_list(revision=repo.commit_hash['Django {% include %} template'])


def test_normalize_does_not_fail_when_detached_in_branch_name(repo):
    if repo.vcs_type == 'git':
        bad_branches = ['blaw blaw blaw detached at blaw blaw blaw', 'blaw blaw blaw detached from blaw blaw blaw']

        obj = repo.get_vcs()
        for branch in bad_branches:
            normalized_branch = obj.normalize_branch(branch)
            assert normalized_branch is None


def test_vcs_special_characters(repo, get_context):
    repo.reset()

    context = get_context('staging.hammer')
    obj = repo.get_vcs(code_dir='/srv/%s_dummy' % repo.vcs_type, context=context)
    repo.add_remote()

    repo.store_commit_hash('bar')
    repo.push()

    obj.clone(repo.default_branch)

    repo.store_commit_hash('foo.txt', branch='another', message=u'look-an-unicode-character💀 in commit message')
    repo.push('another')
    obj.update('another')

    expected_message = u'look-an-unicode-character💀 in commit message' \
        if repo.vcs_type == 'git' \
        else u'look-an-unicode-character? in commit message'

    version_info = obj.version()
    assert list(version_info) == [
        repo.commit_hash['foo.txt'],
        'another',
        expected_message,
        repo.user_full,
    ]
