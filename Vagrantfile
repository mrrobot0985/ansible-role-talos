# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'open-uri'
require 'fileutils'

# Suppress harmless fog-libvirt warning caused by upstream plugin version mismatch
# (vagrant-libvirt 0.12.2 passes libvirt_ip_command, but fog-libvirt >= 0.13 no longer recognizes it)
begin
  require 'fog/core/logger'
  module Fog
    class Logger
      class << self
        alias_method :_warning_without_filter, :warning
        def warning(message)
          return if message.to_s.include?("libvirt_ip_command")
          _warning_without_filter(message)
        end
      end
    end
  end
rescue LoadError
  # fog-core not available yet, warning will show but is harmless
end

# === Configurable cluster size ===
$cp_count      = (ENV['TALOS_CP']      || 1).to_i
$worker_count  = (ENV['TALOS_WORKERS'] || 0).to_i

# === Memory settings (per node type) ===
$cp_memory     = (ENV['TALOS_CP_MEMORY']     || 3072).to_i
$worker_memory = (ENV['TALOS_WORKER_MEMORY'] || 2048).to_i

# === Talos version & ISO ===
$TALOS_VERSION = ENV['TALOS_VERSION'] || 'v1.11.3'
$iso_url       = "https://github.com/siderolabs/talos/releases/download/#{$TALOS_VERSION}/metal-amd64.iso"
$iso_path      = "/tmp/talos-#{$TALOS_VERSION}-metal-amd64.iso"
$log_dir       = File.expand_path(".vagrant/talos-logs")
FileUtils.mkdir_p($log_dir)

# Auto-download ISO once
unless File.exist?($iso_path)
  puts "Downloading Talos #{$TALOS_VERSION} ISO..."
  URI.open($iso_url) { |f| File.binwrite($iso_path, f.read) }
else
  puts "Using cached ISO: #{$iso_path}"
end

Vagrant.configure("2") do |config|
  config.vm.synced_folder ".", "/vagrant", disabled: true

  # === Control Plane Nodes ===
  (1..$cp_count).each do |i|
    config.vm.define "cp-#{i}" do |node|
      node.vm.hostname = "cp-#{i}"
      node.vm.provider :libvirt do |lv|
        lv.cpus   = 2
        lv.memory = $cp_memory
        lv.nested = true
        lv.cpu_mode = "host-passthrough"

        log_file = File.join($log_dir, "cp-#{i}.log")
        FileUtils.mkdir_p(File.dirname(log_file))
        lv.serial type: "file", source: { path: log_file }

        lv.storage :file, device: :cdrom, path: $iso_path
        lv.storage :file, size: "8G", type: "raw"
        lv.boot "cdrom"
        lv.boot "hd"
      end
    end
  end

  # === Worker Nodes ===
  (1..$worker_count).each do |i|
    config.vm.define "worker-#{i}" do |node|
      node.vm.hostname = "worker-#{i}"
      node.vm.provider :libvirt do |lv|
        lv.cpus   = 2
        lv.memory = $worker_memory
        lv.nested = true
        lv.cpu_mode = "host-passthrough"

        log_file = File.join($log_dir, "worker-#{i}.log")
        FileUtils.mkdir_p(File.dirname(log_file))
        lv.serial type: "file", source: { path: log_file }

        lv.storage :file, device: :cdrom, path: $iso_path
        lv.storage :file, size: "8G", type: "raw"
        lv.boot "cdrom"
        lv.boot "hd"
      end
    end
  end

  # === Optional: nice message on first up ===
  config.trigger.before :up, :only_on => "cp-1" do |trigger|
    trigger.run = { inline: "echo 'Starting Talos cluster: #{$cp_count} CP + #{$worker_count} workers'" }
  end
end