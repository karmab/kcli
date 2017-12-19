#!/bin/bash

source `which util.sh`

backtotop
desc "Go to my samples directory"
run "cd $HOME/CODE/git/KARIM/kcli/samples"

backtotop
desc "Render Parameters using jinja2"
run "cat renderedplan.yml"

backtotop
desc "Override those parameters at run time"
run "kcli plan -f renderedplan.yml -P password=leia"

backtotop
desc "Look at the generated metadata"
run "grep leia /tmp/user-data"

backtotop
desc "Render Parameters using jinja2 with a more complex plan"
run "cat renderedplan_advanced.yml"

backtotop
desc "Deploy this more complex plan"
run "kcli plan -f renderedplan_advanced.yml -P net2=localnet"

backtotop
desc "Note that our vm was deployed with two networks (localnet existed priorly)"
run "kcli info vm4"

backtotop
desc "filter products by group. Not there's a lot of fun new products like helm, asb, fission, kubevirt, istio,..."
run "kcli list --products --group openshift"

backtotop
desc "report available parameters for overriding"
run "kcli product ovirt --info"

backtotop
desc "Base profiles"
run "sed -n '/anakin/,//p' ~/.kcli/profiles.yml"

backtotop
desc "Deploy a luke vm"
run "kcli vm -p luke skywalker"

backtotop
desc "Note memory is from luke profile, and rest came from its father (anakin) ( sorry if it's a spoiler)"
run "kcli info skywalker"

backtotop
desc "Execute commands against a list of hypervisors"
run "kcli -C bumblefoot,twix stop vm4"

backtotop
desc "Specify destination hypervisors in a plan"
run "cat spreadplan.yml"

backtotop
desc "Launch this spread plan"
run "kcli -C all plan -f spreadplan.yml spreadplan"

backtotop
desc "Note vms are indeed spread"
run "kcli -C all list"

backtotop
desc "Delete this plan ( indicating to check on each hypervisor)"
run "kcli -C all plan -y -d spreadplan"

backtotop
desc "Customize output of kcli list"
run "kcli info vm3 skywalker -f ip -v"
