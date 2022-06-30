#!/usr/bin/python3.8                                                                                            Proxy_chain2.py                                                                                                             >
#To Run:
#Install scapy: $sudo pip install scapy
#Run Proxy Sniffer $sudo python3.8 <filename.py>
#Must run from sudo for packet processing privileges.

from scapy.all import *
import socket
import time
from Classes.Account import Account
from Utils.Utils import *
from ipaddress import IPv4Address
import sys

load_contrib('bgp') #scapy does not automatically load items from Contrib. Must call function and module name to load.

tx_sender_name = "ACCOUNT1"
tx_sender = Account(AccountType.TransactionSender, tx_sender_name)
tx_sender.load_account_keys()
tx_sender.generate_transaction_object("IANA", "CONTRACT_ADDRESS")
print("Transaction setup complete for: " + tx_sender_name)

#Check whether packet is inbound from external location or generated by local router
def pkt_check(pkt):
    #print("Packet received, determining direction...")
    if pkt[Ether].src != Ether().src:
        print("Packet inbound on interface: "+ pkt.sniffed_on)
        packet = incoming(pkt)
    else:
        print("Packet outbound on interface: "+ pkt.sniffed_on)
        packet = outgoing(pkt)
    return packet
	
def incoming(pkt):
    print("Checking for BGP Update Header")
    if (str(pkt.summary()).find('BGPHeader') > 0) and (pkt[BGPHeader].type == 2) : #dont actually need if filtering on BGP in or>
        print("BGP Update Header Detected")
	try:
            if pkt[BGPUpdate].path_attr[1].attribute.segments[0].segment_length == 1:
                print ("    Destination IP = " + pkt[IP].dst) #Remote AS
                print ("    Source IP = " + pkt[IP].src) #Local AS
                print ("    BGP Segment AS = " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length))
                print ("    BGP Segment Next Hop = " + str(pkt[BGPUpdate].path_attr[2].attribute.next_hop))
                print ("    BGP Segment NLRI = " + str(pkt[BGPUpdate].nlri[0].prefix))
                print ("End of BGP Update Packet")
                count = 0
                for i in pkt[BGPUpdate].nlri:
                    print ("NLRI check: " + str(pkt[BGPUpdate].nlri[count].prefix))
            # chain mutable list = [AS, Network Prefix, CIDR]
                    adv_segment = [pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length, str(pkt[BGPUpdate].nlri[count].prefix).split('/')[0], str(pkt[BGPUpdate].nlri[count].prefix).split('/')[1], "Internal"]

#print ("try seg:" + str(adv_segment[1]))
            #call check on BGPchain to validate segment advertisement request
                    check=bgpchain_validate(adv_segment, tx_sender_name)
                    if check == 'Authorized':
                       print("NLRI " + str(count) + " passed authorization...checking next ASN")
                       count +=1
                       pass
                    else:
                       print ("AS " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length) + " Failed Authorization, Sending Notification...")
                       craft_negative_response_packet(pkt, interface='ens3')
                       return False #Drops original packet without forwarding
                print ("All Advertised ASN's have passed check")
                return True
            else:
                return True
	except:
           print("BGPUpdate was to announce ASN dropped. No check performed.")
    else:
         return True
				
def outgoing(pkt):
    print("Checking for BGP Update Header")
    if (str(pkt.summary()).find('BGPHeader') > 0) and (pkt[BGPHeader].type == 2) : #dont actually need if filtering on BGP in sniff() function
        print("BGP Update Header Detected")
	try:
            if pkt[BGPUpdate].path_attr[1].attribute.segments[0].segment_length == 1:
                print ("    Destination IP = " + pkt[IP].dst) #Remote AS
                print ("    Source IP = " + pkt[IP].src) #Local AS
                print ("    BGP Segment AS = " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length))
                print ("    BGP Segment Next Hop = " + str(pkt[BGPUpdate].path_attr[2].attribute.next_hop))
                print ("    BGP Segment NLRI = " + str(pkt[BGPUpdate].nlri[0].prefix))
                print ("End of BGP Update Packet")
                count = 0
                for i in pkt[BGPUpdate].nlri:
                    print ("NLRI check: " + str(pkt[BGPUpdate].nlri[count].prefix))
            # chain mutable list = [AS, Network Prefix, CIDR]
                    adv_segment = [pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length, str(pkt[BGPUpdate].nlri[count].prefix).split('/')[0], str(pkt[BGPUpdate].nlri[count].prefix).split('/')[1], "Internal"]

            #print ("try seg:" + str(adv_segment[1]))
            #call check on BGPchain to validate segment advertisement request
                    check=bgpchain_validate(adv_segment, tx_sender_name)
                    if check == 'Authorized':
                       print("NLRI " + str(count) + " passed authorization...checking next ASN")
                       count +=1
                       pass
                    else:
                       print ("AS " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length) + " Failed Authorization, Sending Notification...")
                       craft_negative_response_packet(pkt, interface='ens3')
                       return False #Drops original packet without forwarding
                print ("All Advertised ASN's have passed check")
                return True
            else:
                return True
	except:
           print("Update was to announce ASN dropped. No check performed.")
    else:
         return True
                
def craft_negative_response_packet(pkt):
    #packet = Ethernet / IP Layer / TCP Layer / BGP Header / BGP payload
    ether=Ether()
    ip = IP(src=pkt[IP].dst, dst=pkt[IP].src)
    tcp = TCP(sport=pkt[TCP].dport, dport=pkt[TCP].sport, seq=pkt[TCP].ack) #Alternative: tcp=TCP(dport=179) and leave rest alone.
    bgp_hdr = BGPHeader(type=3, marker=pkt[BGPHeader].marker)
    bgp_note= BGPNotification(error_code=3, error_subcode=6) #code 3, subcode 6 = invalid origin attrib. Made-up from avail codes. No real meaning.
    packet_resp= ether / ip / tcp / bgp_hdr / bgp_note # assemble packet
    packet_resp.show()
    sendp(packet_resp)
  
#Placeholder chain check function. Needs to be updated with smart contract calls.  
def bgpchain_validate(segment, tx_sender_name="Remote AS"):
    inIP = IPv4Address(segment[1])
    print(inIP)
    inSubnet = int(segment[2])
    print(type(inSubnet))
    inASN = int(segment[0])
    print(type(inASN), inASN)
    print("test")
    # Validate the prefix<=>ASN mapping. Returns an enum.
    print ("Checking segment: AS" + str(segment[0])+ " , " + str(segment[1]) + "/" + str(segment[2] + " for account: " + tx_sender_name))
    validationResult = tx_sender.tx.sc_validatePrefix(int(inIP), inSubnet, inASN)
    #print(validationResult)
    if validationResult==validatePrefixResult.prefixValid:
        print("Segment Validated.")
        return "Authorized"
    else:
        print("Segment Validation Failed. Error: " + str(validationResult))
        return False
 
def interface_check():
    if_list=[]
    for interface in get_if_list():
        if interface =="lo" or interface=="dummy0":
            pass
        else:
            if_list.append(interface)
    return if_list


if __name__=='__main__':
    print("Listening for packets...")
    sys_interfaces=interface_check()
    #scapy.all.show_interfaces()
    #print(conf.iface)
    sniff(iface=sys_interfaces, prn=pkt_check) # filter='bgp', iface='ens3'
	
#Good commands to troubleshoot with:
    #scapy.all.show_interfaces()
    #print(conf.iface)
