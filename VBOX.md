# Virtual Box

plugin for virtualbox tries to replicate most of the functionality so that experience is transparent to the end user.
Note that the plugin:

- only works for localhost
- makes use of directories as pools to store vms and templates
- converts under the hood cloud images to vdi disks
- dont leverage copy on write... 

## requisites 

if using *macosx*, note that the virtualbox sdk is only compatible with system python ( so use /usr/bin/python when installing kcli so it uses this interpreter, and not the one from brew)

### install pyvbox

```
pip install pyvbox
```

### download sdk and install it

```
export VBOX_INSTALL_PATH=/usr/lib/virtualbox
sudo -E python vboxapisetup.py install
```

then in your *.kcki/config.yml*, you will need a client section defining your virtualbox

```
localhost:
 type: vbox

```

## known issues

there's little control made on the available space when creating disks from profiles, plans or products.

while it's generally not an issue on remote kvm hosts and/or when using copy on write, you might get this kind of exceptions when trying disks with size beyond what's in your system :

```
virtualbox.library.VBoxErrorObjectNotFound: 0x80bb0001 (Object corresponding to the supplied arguments does not exist (VBOX_E_OBJECT_NOT_FOUND))
```
