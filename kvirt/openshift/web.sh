mkdir /etc/web
while [ "$( ls -1 /etc/web | wc -l)" != "2" ] ; do 
 curl -fs -kL https://{{ api_ip }}:22623/config/master -o /etc/web/master
 sleep 5
done
python3 -m http.server --directory /etc/web 8080
