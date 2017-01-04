# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    config.vm.hostname = "collectd-rabbitmq"
    config.vm.box = "ubuntu/trusty64"
    config.vm.network :forwarded_port, guest: 5672, host: 5672
    config.vm.network :forwarded_port, guest: 15672, host: 1567
    config.vm.network :forwarded_port, guest: 80, host: 8080

    config.vm.synced_folder "./", "/vagrant"


    config.vm.provision "shell",
      inline: "apt-get -y install git"

    config.vm.provision "ansible_local" do |ansible|
      ansible.install = true
      ansible.install_mode = "pip"
      ansible.version = "2.1.0"
      ansible.playbook = "vagrant/playbook.yml"
      ansible.galaxy_role_file = "vagrant/requirements.yml"

    end

    config.vm.provider :virtualbox do |v|
        v.name = "collectd-rabbitmq"
    end

end