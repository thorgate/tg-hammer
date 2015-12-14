import os


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


def test_vcs_remote_url(repo):
    obj = repo.get_vcs()

    # Should return None if no remote url
    assert obj.repo_url() is None

    # Set remote url
    repo.add_remote()

    # Check it again
    assert obj.repo_url() == repo.expected_remote

    # Push to remote (actually just a different dir on the master machine)
    repo.push()


def test_vcs_clone(repo, monkeypatch):
    # set host string
    monkeypatch.setattr('fabric.state.env.host_string', 'staging.hammer')
    monkeypatch.setattr('fabric.state.env.use_ssh_config', True)

    from fabric.api import sudo
    sudo('rm -rf /srv/%s_project' % repo.vcs_type)

    obj = repo.get_vcs()
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


def test_vcs_deploy(repo, monkeypatch):
    # make another commit
    repo.store_commit_hash('5.txt')

    # test that it was stored
    assert repo.commit_hash.get('5.txt', None)

    # Push to remote
    repo.push()

    # set host string
    monkeypatch.setattr('fabric.state.env.host_string', 'staging.hammer')
    monkeypatch.setattr('fabric.state.env.use_ssh_config', True)

    # Run deploy
    obj = repo.get_vcs()

    # Remember the version info
    version_info = list(obj.version())

    # Run pull
    obj.pull()

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

    # Run pull
    obj.pull()

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


def test_stable_branch(repo, monkeypatch):
    # make another commit (stable branch)
    repo.store_commit_hash('stable-1', branch='stable')
    assert repo.commit_hash.get('stable-1', None)
    repo.push(branch='stable')

    # Make a different commit (master)
    repo.store_commit_hash('dogs.png', branch=[repo.default_branch])
    assert repo.commit_hash.get('dogs.png', None)
    repo.push()

    # Setup another server on the target host
    monkeypatch.setattr('fabric.state.env.host_string', 'staging.hammer')
    monkeypatch.setattr('fabric.state.env.use_ssh_config', True)

    # get vcs object and set a new code dir
    obj = repo.get_vcs(code_dir='/srv/%s_stable' % repo.vcs_type)
    assert obj.code_dir == '/srv/%s_stable' % repo.vcs_type

    # Ensure target is empty
    from fabric.api import sudo
    sudo('rm -rf %s' % obj.code_dir)

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
            '%s master|stable %s dogs.png' % (repo.commit_hash['dogs.png'], repo.user_full),
            '%s master %s world is kind' % (repo.commit_hash['world is kind'], repo.user_full),
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

    expected_backwards = [
        '%(hash)s %(branch)s %(user)s %(message)s' % {
            'hash': repo.commit_hash['0:merge->stable'],
            'branch': 'stable',
            'user': repo.user_full,
            'message': merge_msg,
        },
        '%s %s %s world is kind' % (repo.commit_hash['world is kind'], repo.default_branch, repo.user_full),
    ]

    if repo.vcs_type == 'git':
        expected_backwards += ['%s master|stable %s dogs.png' % (repo.commit_hash['dogs.png'], repo.user_full)]

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
