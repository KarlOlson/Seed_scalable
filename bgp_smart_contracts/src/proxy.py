#!/usr/bin/python3.10
#To Run:
#Install scapy: $sudo pip install scapy
#Run Proxy Sniffer $sudo python3 <filename.py>
#Must run from sudo for packet processing privileges.
from netfilterqueue import NetfilterQueue
from scapy.all import *
import socket
import time
from Classes.Account import Account
from Utils.Utils import *
from ipaddress import IPv4Address
import os, sys

load_contrib('bgp') #scapy does not automatically load items from Contrib. Must call function and module name to load.

#####Synchronizes ASN with blockchain account data##################
tx_sender_name = "ACCOUNT"+str(sys.argv[1]) #must add an asn # after account, eg. ACCOUNT151 we do this programmatically later in program
tx_sender = Account(AccountType.TransactionSender, tx_sender_name)
tx_sender.load_account_keys()
tx_sender.generate_transaction_object("IANA", "CONTRACT_ADDRESS")
print("Transaction setup complete for: " + tx_sender_name)

################Establishes local IPTABLES Rule to begin processing packets############
QUEUE_NUM = 1
# insert the iptables FORWARD rule
os.system("iptables -I INPUT -j NFQUEUE --queue-num {}".format(QUEUE_NUM))

#Check whether packet is inbound from external location or generated by local router
#def pkt_check(packet):
   # hw=packet.get_hw()
   # print(str(hw))
   # print(str(Ether().src))
   # pkt = IP(packet.get_payload())
   # print(str(pkt.summary()))
   # if pkt[Ether].src != Ether().src:
       # print("Packet inbound on interface: "+ pkt.sniffed_on)
       # incoming(pkt)
   # else:
       # print("Packet outbound on interface: "+ pkt.sniffed_on)
       # outgoing(pkt)


def pkt_in(packet):
    pkt = IP(packet.get_payload())
    print(str(pkt.summary()))
    if (str(pkt.summary()).find('BGPHeader') > 0) and (pkt[BGPHeader].type == 2) : #Check if packet has a BGPHeader and if it is of type==2 (BGPUpdate). 
        print("BGP Update Header Detected")
        try:
            if pkt[BGPUpdate].path_attr[1].attribute.segments[0].segment_length == 1:
                print ("    Destination IP = " + pkt[IP].dst) #Local AS
                print ("    Source IP = " + pkt[IP].src) #Remote AS
                print ("    BGP Segment AS = " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length)) #even though it says segment length, that field is used to announce the A>
                print ("    BGP Segment Next Hop = " + str(pkt[BGPUpdate].path_attr[2].attribute.next_hop))
                print ("    BGP Segment NLRI = " + str(pkt[BGPUpdate].nlri[0].prefix))
                print ("End of BGP Update Packet")
                count = 0
                for i in pkt[BGPUpdate].nlri:
                    print ("NLRI check: " + str(pkt[BGPUpdate].nlri[count].prefix))
                    # chain mutable list = [AS, Network Prefix, CIDR]
                    adv_segment = [pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length, str(pkt[BGPUpdate].nlri[count].prefix).split('/')[0], str(pkt[BGPUpdate].nlri[count].prefix).split('/')[1], "Internal"]
                    print ("adv_segment="+str(adv_segment))
			        #print ("try seg:" + str(adv_segment[1]))
                    #call check on BGPchain to validate segment advertisement request
                    account_check=str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length)
                    print ("validating advertisement for ASN: "+account_check)
                    check=bgpchain_validate(adv_segment, tx_sender)
                    print ("segment check = "+str(check))
                    if check == 'Authorized':
                        print("NLRI " + str(count) + " passed authorization...checking next ASN")
                        count +=1
                        pass
                    else:
                        print ("AS " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length) + " Failed Authorization, Sending Notification...")
                        craft_negative_response_packet(pkt)
                        packet.drop() #Drops original packet without forwarding
                print ("All Advertised ASN's have passed check")
                packet.accept()
            else:
                print("Not a new neighbor path announcement")
                packet.accept()
        except: pass
    else:
        packet.accept()

def pkt_out(packet):
    pkt = IP(packet.get_payload())
    print(str(pkt.summary()))
    if (str(pkt.summary()).find('BGPHeader') > 0) and (pkt[BGPHeader].type == 2) : #Check if packet has a BGPHeader and if it is of type==2 (BGPUpdate). 
        print("BGP Update Header Detected")
        try:
            if pkt[BGPUpdate].path_attr[1].attribute.segments[0].segment_length == 1:
                print ("    Destination IP = " + pkt[IP].dst) #Remote AS
                print ("    Source IP = " + pkt[IP].src) #Local AS
                print ("    BGP Segment AS = " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length)) #even though it says segment length, that field is used to announce the A>
                print ("    BGP Segment Next Hop = " + str(pkt[BGPUpdate].path_attr[2].attribute.next_hop))
                #print ("    BGP Segment NLRI = " + str(pkt[BGPUpdate].nlri[0].prefix))
                #print ("End of BGP Update Packet")
                count = 0
                for i in pkt[BGPUpdate].nlri:
                    print ("NLRI check: " + str(pkt[BGPUpdate].nlri[count].prefix))
                    # chain mutable list = [AS, Network Prefix, CIDR]
                    adv_segment = [pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length, str(pkt[BGPUpdate].nlri[count].prefix).split('/')[0], str(pkt[BGPUpdate].nlri[count].prefix).split('/')[1], "Internal"]
                    print ("adv_segment="+str(adv_segment))
			        #print ("try seg:" + str(adv_segment[1]))
                    #call check on BGPchain to validate segment advertisement request
                    account_check=str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length)
                    print ("validating advertisement for ASN: "+account_check)
                    check=bgpchain_validate(adv_segment, tx_sender)
                    print ("segment check = "+str(check))
                    if check == 'Authorized':
                        print("NLRI " + str(count) + " passed authorization...checking next ASN")
                        count +=1
                        pass
                    else:
                        print ("AS " + str(pkt[BGPUpdate].path_attr[1].attribute.segments[1].segment_length) + " Failed Authorization, Sending Notification...")
                        craft_negative_response_packet(pkt)
                        packet.drop() #Drops original packet without forwarding
                print ("All Advertised ASN's have passed check")
                packet.accept()
            else:
                print("Not a new neighbor path announcement")
                packet.accept()
        except: pass
    else:
        packet.accept()
        
def craft_negative_response_packet(pkt):
    #packet = Ethernet / IP Layer / TCP Layer / BGP Header / BGP payload
    ether=Ether()
    ip = IP(src=pkt[IP].dst, dst=pkt[IP].src)
    tcp = TCP(sport=pkt[TCP].dport, dport=pkt[TCP].sport, seq=pkt[TCP].ack) #Alternative: tcp=TCP(dport=179) and leave rest alone.
    bgp_hdr = BGPHeader(type=3, marker=pkt[BGPHeader].marker)
    bgp_note= BGPNotification(error_code=3, error_subcode=6) #code 3, subcode 6 = invalid origin attrib. Made-up from avail codes. No real meaning.
    packet_resp= ether / ip / tcp / bgp_hdr / bgp_note # assemble packet
    #packet_resp.show()
    sendp(packet_resp)
  
#Placeholder chain check function. Needs to be updated with smart contract calls.  
def bgpchain_validate(segment, tx_sender):
    print ("Validating segment.....")
    print ("tx_sender="+tx_sender+"or "+ str(tx_sener))
    inIP = IPv4Address(segment[1])
    print (inIP)
    inSubnet = int(segment[2])
    print (str(inSubnet))
    inASN = int(segment[0])
    print (str(inASN))
    #print(type(inASN), inASN)
    #print("tes")
    # Validate the prefix<=>ASN mapping. Returns an enum.
    print ("Checking segment: ASN" + str(segment[0])+ ", for ownership of:" + str(segment[1]) + "/" + str(segment[2]))
    print ("testing tx_sender: "+str(tx_sender))
    validationResult = tx_sender.tx.sc_validatePrefix(int(inIP), inSubnet, inASN)
    print("valid result ="+str(validationResult))
    if validationResult==validatePrefixResult.prefixValid:
        print("Segment Validated.")
        return "Authorized"
    else:
        print("Segment Validation Failed. Error: " + str(validationResult))
        return False
 
#def interface_check():
#    if_list=[]
#    for interface in get_if_list():
#        if interface =="lo" or interface=="dummy0":
#            pass
#       else:
#            if_list.append(interface)
#    return if_list


if __name__=='__main__':

# instantiate the netfilter queue
   nfqueue = NetfilterQueue()
 
   try:
      nfqueue.bind(1, pkt_in)
       #nfqueue.bind(2, pkt_in)
      nfqueue.run()
   except KeyboardInterrupt:
      print('')
      # remove that rule we just inserted, going back to normal.
      os.system("iptables --flush")
      nfqueue.unbind()
