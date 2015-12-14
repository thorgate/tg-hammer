# -*- mode: ruby -*-
# vi: set ft=ruby :


Vagrant.configure(2) do |config|

  config.vm.define "master", primary: true do |master|
    master.vm.box = "ubuntu/trusty64"
    master.vm.hostname = "hammer.repo.host"
    master.vm.network "private_network", ip: "192.168.10.21"

    master.vm.provision "shell", inline: <<-SHELL
      grep -q -F '192.168.10.21 hammer.repo.host' /etc/hosts || echo '192.168.10.21 hammer.repo.host' >> /etc/hosts
      grep -q -F '192.168.10.22 staging.hammer' /etc/hosts || echo '192.168.10.22 staging.hammer' >> /etc/hosts

      grep -q -F 'RSAAuthentication yes' /etc/ssh/sshd_config || echo 'RSAAuthentication yes' >> /etc/ssh/sshd_config
      grep -q -F 'PubkeyAuthentication yes' /etc/ssh/sshd_config || echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config
      /etc/init.d/ssh restart

      add-apt-repository -y ppa:tortoisehg-ppa/releases
      apt-get update
      apt-get install -y g++ build-essential
      apt-get install -y gettext curl git nano
      apt-get install -y mercurial
      apt-get install -y python python-dev python-virtualenv python3.4 python3.4-dev

      useradd -m -d /var/vcs -s /bin/bash -c 'vcs' vcs

      mkdir -p /var/vcs
      mkdir -p /var/vcs/.ssh
      mkdir -p /repos/

      mkdir -p /repos/git
      chown -R vcs:vcs /repos/git

      mkdir -p /repos/hg
      chown -R vcs:vcs /repos/hg

      chmod 777 /repos/git
      chmod 777 /repos/hg

      cp /home/vagrant/.ssh/authorized_keys /var/vcs/.ssh/authorized_keys
      echo `cat /vagrant/tests/ssh/test_key.pub` >> /var/vcs/.ssh/authorized_keys
      chmod 700 /var/vcs/.ssh
      chown -R vcs:vcs /var/vcs

      cp /vagrant/tests/ssh/test_key /home/vagrant/.ssh/test_key
      cp /vagrant/tests/ssh/test_key.pub /home/vagrant/.ssh/test_key.pub

      rm /home/vagrant/.ssh/config
      echo "Host hammer.repo.host" >> /home/vagrant/.ssh/config
      echo "    IdentityFile /home/vagrant/.ssh/test_key" >> /home/vagrant/.ssh/config
      echo "    User vcs" >> /home/vagrant/.ssh/config
      echo "Host staging.hammer" >> /home/vagrant/.ssh/config
      echo "    IdentityFile /home/vagrant/.ssh/test_key" >> /home/vagrant/.ssh/config

      chmod 700 -R /home/vagrant/.ssh
      chown -R vagrant:vagrant /home/vagrant/.ssh

      pip install virtualenvwrapper
    SHELL

    master.vm.provision "shell", privileged: false, inline: <<-SHELL
      export WORKON_HOME=/home/vagrant/.virtualenvs
      mkdir -p $WORKON_HOME

      chown -R vagrant:vagrant $WORKON_HOME

      echo "WORKON_HOME=$WORKON_HOME" > /home/vagrant/.workon
      echo "source /usr/local/bin/virtualenvwrapper.sh" >> /home/vagrant/.workon

      grep -q -F 'source ~/.workon' /home/vagrant/.bashrc || echo 'source ~/.workon' >> /home/vagrant/.bashrc
    SHELL

    master.vm.provision "shell", privileged: false, inline: <<-SHELL
      . ~/.workon
      mkvirtualenv hammer
      workon hammer
      cd /vagrant
      ./setup.py develop
      pip install -r requirements/development.txt
    SHELL
  end

  config.vm.define "slave" do |slave|
    slave.vm.box = "ubuntu/trusty64"
    slave.vm.hostname = "staging.hammer"
    slave.vm.network "private_network", ip: "192.168.10.22"

    slave.vm.provision "shell", inline: <<-SHELL
      grep -q -F '192.168.10.21 hammer.repo.host' /etc/hosts || echo '192.168.10.21 hammer.repo.host' >> /etc/hosts
      grep -q -F '192.168.10.22 staging.hammer' /etc/hosts || echo '192.168.10.22 staging.hammer' >> /etc/hosts

      grep -q -F 'RSAAuthentication yes' /etc/ssh/sshd_config || echo 'RSAAuthentication yes' >> /etc/ssh/sshd_config
      grep -q -F 'PubkeyAuthentication yes' /etc/ssh/sshd_config || echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config
      /etc/init.d/ssh restart

      add-apt-repository -y ppa:tortoisehg-ppa/releases
      apt-get update
      apt-get install -y g++ build-essential
      apt-get install -y gettext curl git nano
      apt-get install -y mercurial
      apt-get install -y python python-dev python-virtualenv python3.4 python3.4-dev

      cp /vagrant/tests/ssh/test_key /home/vagrant/.ssh/test_key
      cp /vagrant/tests/ssh/test_key.pub /home/vagrant/.ssh/test_key.pub

      echo `cat /vagrant/tests/ssh/test_key.pub` >> /home/vagrant/.ssh/authorized_keys

      touch /home/vagrant/.ssh/config
      rm /home/vagrant/.ssh/config
      echo "Host hammer.repo.host" >> /home/vagrant/.ssh/config
      echo "    User vcs" >> /home/vagrant/.ssh/config
      echo "    IdentityFile /home/vagrant/.ssh/test_key" >> /home/vagrant/.ssh/config

      chmod 700 -R /home/vagrant/.ssh
      chown -R vagrant:vagrant /home/vagrant/.ssh

      mkdir -p /srv
      chmod 7777 -R /srv/

    SHELL
  end
end
