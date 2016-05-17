#!/bin/bash

source /etc/apache2/envvars

sed -i "s/keystone_user/${KEYSTONE_USER}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_pass/${KEYSTONE_PASS}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_addr/${DB_HOST}/g" /etc/keystone/keystone.conf
sed -i "s/keystone_db/${KEYSTONE_DB}/g" /etc/keystone/keystone.conf

# bootstrap db
mysql -u root -p${ROOT_DB_PASS} -h ${DB_HOST} -e 'create database keystone'
mysql -u root -p${ROOT_DB_PASS} -h ${DB_HOST} -e "grant all privileges on keystone.* to '${KEYSTONE_USER}'@'%' identified by '${KEYSTONE_PASS}';"

keystone-manage db_sync

keystone-manage bootstrap --bootstrap-password ${KEYSTONE_PASS}

export OS_URL=http://127.0.0.1:35357/v3
export OS_TOKEN=adm_tok
export OS_IDENTITY_API_VERSION=3


openstack service create --name keystone --description "OpenStack Identity" identity
/usr/sbin/apache2ctl -D FOREGROUND
