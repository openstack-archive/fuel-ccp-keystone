#!/bin/bash

source /etc/apache2/envvars

sed -i "s/keystone_user/${KEYSTONE_USER}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_pass/${KEYSTONE_PASS}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_addr/${DB_HOST}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_db/${KEYSTONE_DB}/g" /etc/keystone/keystone.conf

nc -z -v -w5 ${DB_HOST} 3306
if [ $? -ne 0 ]
then
    exit 1
fi


controller=`hostname -i`

# bootstrap db
mysql -u root -p${ROOT_DB_PASS} -h ${DB_HOST} -e "create database ${KEYSTONE_DB}"
mysql -u root -p${ROOT_DB_PASS} -h ${DB_HOST} -e "grant all privileges on ${KEYSTONE_DB}.* to '${KEYSTONE_USER}'@'%' identified by '${KEYSTONE_PASS}';"

keystone-manage db_sync

keystone-manage bootstrap --bootstrap-password ${KEYSTONE_PASS}

/usr/sbin/apachectl start

export OS_URL=http://127.0.0.1:35357/v3
export OS_TOKEN=adm_tok
export OS_IDENTITY_API_VERSION=3

id=`openstack service list | awk '/ identity / {print $2}' | wc -l`

if [ "$id" -eq "0" ]
then
    openstack service create --name keystone --description "OpenStack Identity" identity

    openstack endpoint create --region RegionOne \
	  identity public http://$controller:5000/v3

    openstack endpoint create --region RegionOne \
	  identity internal http://$controller:5000/v3

    openstack endpoint create --region RegionOne \
	  identity admin http://$controller:35357/v3
fi
/usr/sbin/apachectl stop

sleep 5

/usr/sbin/apache2ctl -D FOREGROUND
