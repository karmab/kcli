#!/bin/bash

source `which util.sh`

backtotop
desc "Go to my samples directory"
run "cd $HOME/CODE/git/KARIM/kcli/samples"

backtotop
desc "List vms"
run "kcli list"

backtotop
desc "List cloud templates"
run "kcli list --templates"

backtotop
desc "Deploy a vm from a Template"
run "kcli vm -p Fedora-Cloud-Base-27-1.6.x86_64.qcow2"

backtotop
desc "List profiles"
run "kcli list --profiles"

backtotop
desc "Deploy a vm from a profile"
run "kcli vm -p centos test1"

backtotop
desc "Use a simple plan"
run "cat simpleplan.yml"

backtotop
desc "Deploy using a plan"
run "kcli plan -f simpleplan.yml"

backtotop
desc "Deploy a more advanced plan (also defining a network and forcing static configuration)"
run "cat staticip/john.yml"

backtotop
desc "Deploy this plan"
run "kcli plan -f staticip/john.yml"

backtotop
desc "Check network was created"
run "kcli list --networks"

backtotop
desc "Run ssh command"
run "kcli ssh test1 hostname"

backtotop
desc "Delete a vm"
run "kcli delete --yes test1"
