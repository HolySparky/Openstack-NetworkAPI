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

from nova.network import api

from nova.api.openstack import common
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
from nova.compute import instance_types
from nova.network.quantum import manager
from nova import exception



def make_network(elem, detailed=False):
    elem.set('name')
    elem.set('id')
    if detailed:
        elem.set('name')
        elem.set('vms')
    
    xmlutil.make_links(elem, 'links')

network_manager = manager.QuantumManager()
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
	#nets=network_manager.get_all_networks(context)	
	nets=network_api.get_all(context)
	print nets
	return str(nets[0])


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
        #authorize(context)

        vals = body['network']
        name = vals['name']
	size = vals['size']
	cidr = vals['cidr']
	
	print name
	print size
	print cidr

        try:
	    network_manager.create_networks(context, name, cidr, false)
#def create_networks(self, context, label, cidr, multi_host, num_networks,
#                        network_size, cidr_v6, gateway, gateway_v6, bridge,
#                        bridge_interface, dns1=None, dns2=None, uuid=None,
#                        **kwargs)

#            flavor = instance_types.create(name, memory_mb, vcpus,
#                                           root_gb, ephemeral_gb, flavorid,
#                                           swap, rxtx_factor)
        except Exception:
		print "Errored~~~~~~~~~~~~~"
        return "Got it!"


def create_resource():
    return wsgi.Resource(Controller())
