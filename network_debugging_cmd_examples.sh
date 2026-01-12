#!/bin/bash

# Installing nmap command
apt-get update && apt-get install -y nmap

echo "---- ping (Packet Internet Groper) ----"
echo "Des: It's used to check if the networked device is reachable. Using -c flag with 5 to only send 5 requests."
ping -c 5 www.google.com
echo "------------------------"
echo "---- telnet(Teletype Network) ----"
echo "Des: It's used to check whether a port is opened. Command:telnet [domainname or ip] [port]"
telnet google.com 80
echo "------------------------"
echo "---- traceroute ----"
echo "Des: It will list all the routers it passes through until it reaches its destination"
traceroute www.google.com
echo "------------------------"
echo "---- dig(Domain Information Groper) ----"
echo "Des: It's used for querying DNS nameservers for information about host addresses, mail exchanges and nameservers."
dig www.google.com
echo "------------------------"
echo "---- nslookup(Name Server Lookup) ----"
echo "Des: It's used to find out the corresponding IP address or DNS record by using the hostname."
nslookup www.google.com
echo "------------------------"
echo "---- nmap(Network Map) ----"
echo "Des: It's used to scan for open ports in hosts and services."
nmap www.google.com