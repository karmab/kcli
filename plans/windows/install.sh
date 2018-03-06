curl -o /etc/yum.repos.d/mssql-server.repo https://packages.microsoft.com/config/rhel/7/mssql-server-2017.repo
yum install -y mssql-server
export MSSQL_SA_PASSWORD="BIGsecret2018@"
/opt/mssql/bin/mssql-conf --noprompt setup setup_option
