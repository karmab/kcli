if you want to provision the ldap you can use the following command

```
ldapadd -vvvv -h localhost:389 -c -x -D cn=admin,dc=karmalabs,dc=com -W -f ou.ldif
ldapadd -vvvv -h localhost:389 -c -x -D cn=admin,dc=karmalabs,dc=com -W -f users.ldif
```
