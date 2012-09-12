# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import webob
import math
from nova.network import api

from nova.api.openstack import common
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova.compute import instance_types
from nova.network.quantum import manager
from nova import exception
from nova import utils
from nova import context
from nova import db
from nova import flags

FLAGS = flags.FLAGS

def make_network(elem, detailed=False):
    elem.set('name')
    elem.set('id')
    if detailed:
        elem.set('name')
        elem.set('vms')
    
    xmlutil.make_links(elem, 'links')

network_api = api.API()
network_nsmap = {None: xmlutil.XMLNS_V11, 'atom': xmlutil.XMLNS_ATOM}


class NetworkTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('network', selector='network')
        make_network(root, detailed=True)
        return xmlutil.MasterTemplate(root, 1, nsmap=network_nsmap)


class MinimalNetworksTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('networks')
        elem = xmlutil.SubTemplateElement(root, 'network', selector='networks')
        make_network(elem)
        return xmlutil.MasterTemplate(root, 1, nsmap=network_nsmap)


class NetworksTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('networks')
        elem = xmlutil.SubTemplateElement(root, 'network', selector='networks')
        make_network(elem, detailed=True)
        return xmlutil.MasterTemplate(root, 1, nsmap=network_nsmap)


class Controller(wsgi.Controller):
    """Flavor controller for the OpenStack API."""

    #_view_builder_class = flavors_view.ViewBuilder
    @wsgi.serializers(xml=MinimalNetworksTemplate)
    def index(self, req):
        """Return all flavors in brief."""
        #flavors = self._get_flavors(req)
        #return self._view_builder.index(req, flavors)
	project_id=str(req.environ['HTTP_X_TENANT_ID'])
	context = req.environ['nova.context']
	context = context.elevated()

        networks = db.network_get_all(context)
        nets=[dict(network.iteritems()) for network in networks]

	virtual_interfaces = db.virtual_interface_get_all(context)
	vifs=[dict(vif.iteritems()) for vif in virtual_interfaces]
	
	#make a dict of relationships between Network_IDs and Instance_IDs {1:[1,2],...}
	net_vm_dict = {}
	for vif in vifs:
	    net_id=int(vif['network_id'])	
	    vm_id=int(vif['instance_id'])
	    if net_id in net_vm_dict:
		net_vm_dict[net_id].append(vm_id)
	    else:
		net_vm_dict[net_id] = [vm_id]
	print net_vm_dict


	#Go through the dict , filter by this project and get detailed infos	
	#instance_get(context, instance_id)
	net_list = []
	for netID in net_vm_dict:
	    try:
	        networks= db.network_get(context, netID)
	    except exception.NetworkNotFound:
		print " network not found"
		continue
	    net = dict(networks.iteritems())
	    print str(net['project_id'])
	    if net['project_id']==None or net['project_id']==project_id:
		print "my precious~~"
		net_info = {}
		net_info['id']=str(net['uuid'])
		net_info['name']=str(net['label'])
		net_info['cidr']=str(net['cidr'])
		net_info['vm']=[]
		net_list.append(net_info)	
		for vmID in  net_vm_dict[netID]:
		    vms = db.instance_get(context, vmID)
		    vm = dict(vms.iteritems())
		    if vm['project_id']==project_id:
		        print "My VM"
			vm_info = {}
			#Get vm infos for each VM
			vm_info['name']=str(vm['hostname'])
			vm_info['id']=str(vm['uuid'])
			vm_info['vm_state']=str(vm['vm_state'])
			#Get fixed_ips for each VM
			fixed_ips = db.fixed_ip_get_by_instance(context, vmID)
			fixed_ip_info = []
			for ip in fixed_ips:
			    fixed_ip_info.append(str(dict(ip.iteritems())['address']))
			vm_info['fixed_ips'] = fixed_ip_info
			#Get Floating_ips for each VM
			floating_ip_info = []
			for fixed_ip in fixed_ips:
			    
			    try:
			        floating_ips = db.floating_ip_get_by_fixed_ip_id(context, str(dict(fixed_ip.iteritems())['id']))
			    except exception.FloatingIpNotFoundForAddress:
				print "floating not found"
				continue
			    if floating_ips != None:
			        for floating_ip in floating_ips:
				    floating_ip_info.append(str(dict(floating_ip.iteritems())['address']))
			vm_info['floating_ips']=floating_ip_info
			net_info['vm'].append(vm_info)

	for net in nets:
	    if net['id'] in net_vm_dict:
		print "Existed network"
	    else:
		net_info = {}
                net_info['id']=str(net['uuid'])
                net_info['name']=str(net['label'])
                net_info['cidr']=str(net['cidr'])
                net_info['vm']=[]
                net_list.append(net_info)
	
	ret_net_list={}
	ret_net_list['networks']=net_list
	print ret_net_list

	return ret_net_list

	

    @wsgi.serializers(xml=NetworksTemplate)
    def detail(self, req):
        """Return all flavors in detail."""
        return "Details called"




    @wsgi.serializers(xml=NetworkTemplate)
    def show(self, req, id):
        """Return data about the given flavor id."""
        #try:
        #    flavor = instance_types.get_instance_type_by_flavor_id(id)
        #except exception.NotFound:
        #    raise webob.exc.HTTPNotFound()

        #return self._view_builder.show(req, flavor)
	return {
            "network": {
                "id": "ID",
                "name": "name",
            },
        }

    @wsgi.action("create")
    @wsgi.serializers(xml=NetworkTemplate)
    def _create(self, req, body):
	context = req.environ['nova.context']
	context = context.elevated()
	print "context!!"
	print context.to_dict()
        vals = body['network']
        name = vals['name']
	size = vals['size']
	project_id=str(req.environ['HTTP_X_TENANT_ID'])
	print FLAGS.network_manager	
	cidr = self.get_new_cidr(context, size)
	print cidr
	print"!!!!!!!!!!!!!!!!strat creating"
	self.create_network(context=context, label=name, fixed_range_v4=cidr, num_networks=1,
               network_size=size, multi_host=None, vlan_start=None,
               vpn_start=None, fixed_range_v6=None, gateway=None,
               gateway_v6=None, bridge=None, bridge_interface=None,
               dns1=None, dns2=None, project_id=project_id, priority=None,
               uuid=None, fixed_cidr=None)
	print cidr	
	db_net = db.network_get_by_cidr(context, cidr)
	net = dict(db_net.iteritems())
	ret_net={}
	ret_net['network']={'id':net['uuid'],'name':net['label'],'cidr':net['cidr']}
        return ret_net

    def get_new_cidr(self, context, size=256):
	cidr = ""
	cidrs = []		
	subnets = []
	mask=int(32-math.log(size,2))
	is_used = False
	#get all cidrs, if cidr=10.0.3.0/24 then subnet=3
	for network in db.network_get_all(context):
	    cidrs.append(str(network.cidr))
	    subnets.append(str(network.cidr).split('.')[2])
	#get a new unused subnet id
	for i in range(0,254):
	    is_used = False
	    for subnet in subnets:
		if i == int(subnet):
		    is_used = True
		    break
	    if is_used == False:
		break
	new_cidr = cidrs[0].split('.')
	new_cidr[2] = i
	new_cidr[-1] = '0/'+ str(mask)
	new_cidr_str = ""
	print "new cidr is:"
	print new_cidr
	for a in new_cidr:
	    new_cidr_str = new_cidr_str+str(a)+'.'
	new_cidr_str = new_cidr_str[0:-1]
	return new_cidr_str
	

    def list(self):
	"""List all created networks"""
        _fmt = "%-5s\t%-18s\t%-15s\t%-15s\t%-15s\t%-15s\t%-15s\t%-15s\t%-15s"
        print _fmt % (_('id'),
                          _('IPv4'),
                          _('IPv6'),
                          _('start address'),
                          _('DNS1'),
                          _('DNS2'),
                          _('VlanID'),
                          _('project'),
                          _("uuid"))
        for network in db.network_get_all(context):
            print _fmt % (network.id,
                          network.cidr,
                          network.cidr_v6,
                          network.dhcp_start,
                          network.dns1,
                          network.dns2,
                          network.vlan,
                          network.project_id,
                          network.uuid)
	    print FLAGS.fixed_range


    def create_network(self, context, label=None, fixed_range_v4=None, num_networks=None,
               network_size=None, multi_host=None, vlan_start=None,
               vpn_start=None, fixed_range_v6=None, gateway=None,
               gateway_v6=None, bridge=None, bridge_interface=None,
               dns1=None, dns2=None, project_id=None, priority=None,
               uuid=None, fixed_cidr=None):
        """Creates fixed ips for host by range"""
	print "creating~~~~~~~~~~"
        # check for certain required inputs
        if not label:
            raise exception.NetworkNotCreated(req='--label')
        if not (fixed_range_v4 or fixed_range_v6):
            req = '--fixed_range_v4 or --fixed_range_v6'
            raise exception.NetworkNotCreated(req=req)

        bridge = bridge or FLAGS.flat_network_bridge
        if not bridge:
            bridge_required = ['nova.network.manager.FlatManager',
                               'nova.network.manager.FlatDHCPManager']
            if FLAGS.network_manager in bridge_required:
                raise exception.NetworkNotCreated(req='--bridge')

        bridge_interface = bridge_interface or FLAGS.flat_interface or \
                           FLAGS.vlan_interface
        if not bridge_interface:
            interface_required = ['nova.network.manager.VlanManager']
            if FLAGS.network_manager in interface_required:
                raise exception.NetworkNotCreated(req='--bridge_interface')

	# sanitize other input using FLAGS if necessary
        if not num_networks:
            num_networks = FLAGS.num_networks
        if not network_size and fixed_range_v4:
            fixnet = netaddr.IPNetwork(fixed_range_v4)
            each_subnet_size = fixnet.size / int(num_networks)
            if each_subnet_size > FLAGS.network_size:
                network_size = FLAGS.network_size
                subnet = 32 - int(math.log(network_size, 2))
                oversize_msg = _('Subnet(s) too large, defaulting to /%s.'
                         '  To override, specify network_size flag.') % subnet
                print oversize_msg
            else:
                network_size = fixnet.size
        if not multi_host:
            multi_host = FLAGS.multi_host
        else:
            multi_host = multi_host == 'T'
        if not vlan_start:
            vlan_start = FLAGS.vlan_start
        if not vpn_start:
            vpn_start = FLAGS.vpn_start
        if not dns1 and FLAGS.flat_network_dns:
            dns1 = FLAGS.flat_network_dns

        if not network_size:
            network_size = FLAGS.network_size

        if fixed_cidr:
            fixed_cidr = netaddr.IPNetwork(fixed_cidr)

	# create the network
        net_manager = utils.import_object(FLAGS.network_manager)
        net_manager.create_networks(context,
                                    label=label,
                                    cidr=fixed_range_v4,
                                    multi_host=multi_host,
                                    num_networks=int(num_networks),
                                    network_size=int(network_size),
                                    vlan_start=int(vlan_start),
                                    vpn_start=int(vpn_start),
                                    cidr_v6=fixed_range_v6,
                                    gateway=gateway,
                                    gateway_v6=gateway_v6,
                                    bridge=bridge,
                                    bridge_interface=bridge_interface,
                                    dns1=dns1,
                                    dns2=dns2,
                                    project_id=project_id,
                                    priority=priority,
                                    uuid=uuid,
                                    fixed_cidr=fixed_cidr)

def create_resource():
    return wsgi.Resource(Controller())

