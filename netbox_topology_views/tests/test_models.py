from django.test import TestCase

from dcim.choices import InterfaceTypeChoices
from circuits.models import *
from dcim.models import *
from wireless.models import WirelessLink
from extras.models import Tag

from ..models import BaseNode, Topology

HIDE_UNCONNECTED_NO = False
HIDE_UNCONNECTED_YES = True
SAVE_COORDS_NO = False
SAVE_COORDS_YES = True
SHOW_CIRCUIT_NO = False
SHOW_CIRCUIT_YES = True
SHOW_PROVIDER_NETWORK_YES = True
SHOW_PROVIDER_NETWORK_NO = False
SHOW_POWER_NO = False
SHOW_POWER_YES = True

#TODO
# - Check number of endpoint in results nodes ?

class TopologyTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.site_a = Site.objects.create(name='site A', slug='site-a')

        cls.generic_manufacturer = Manufacturer.objects.create(name='Generic', slug='generic')

        # switchs
        cls.switch_role = DeviceRole.objects.create(name='Switch', slug='switch')
        cls.switch_type = DeviceType.objects.create(model='Generic Switch', slug='generic-switch', manufacturer=cls.generic_manufacturer)
        cls.switch1 = Device.objects.create(name='SW-SITEA-1', device_type=cls.switch_type, device_role=cls.switch_role, site=cls.site_a)
        cls.switch2 = Device.objects.create(name='SW-SITEA-2', device_type=cls.switch_type, device_role=cls.switch_role, site=cls.site_a)

        cls.switch1_if1 = Interface.objects.create(device=cls.switch1, name='Interface 1')
        cls.switch2_if1 = Interface.objects.create(device=cls.switch2, name='Interface 1')

        cls.switch1_psu = PowerPort.objects.create(device=cls.switch1, name="psu0")
        cls.switch2_psu = PowerPort.objects.create(device=cls.switch2, name="psu0")

        # patch-panels
        cls.patch_panel_role = DeviceRole.objects.create(name='Patch Panel', slug='patch-panel')
        cls.patch_panel_type = DeviceType.objects.create(model='Generic Patch Panel', slug='generic-patch-panel', manufacturer=cls.generic_manufacturer)
        cls.patch_panel1 = Device.objects.create(name='PP-SITEA-1', device_type=cls.patch_panel_type, device_role=cls.patch_panel_role, site=cls.site_a)
        cls.patch_panel2 = Device.objects.create(name='PP-SITEA-2', device_type=cls.patch_panel_type, device_role=cls.patch_panel_role, site=cls.site_a)

        cls.patch_panel1_rp1 = RearPort.objects.create(device=cls.patch_panel1, name='RP1', type='sc-pc', positions=2)
        cls.patch_panel2_rp1 = RearPort.objects.create(device=cls.patch_panel2, name='RP1', type='sc-pc', positions=2)
        cls.patch_panel1_rp1_cable = Cable(a_terminations=[cls.patch_panel1_rp1],b_terminations=[cls.patch_panel2_rp1])
        cls.patch_panel1_rp1_cable.save()

        cls.front_port1_1 = FrontPort.objects.create(device=cls.patch_panel1, name='FP1', type='sc-pc', rear_port=cls.patch_panel1_rp1, rear_port_position=1)
        cls.front_port1_2 = FrontPort.objects.create(device=cls.patch_panel1, name='FP2', type='sc-pc', rear_port=cls.patch_panel1_rp1, rear_port_position=2)
        cls.front_port2_1 = FrontPort.objects.create(device=cls.patch_panel2, name='FP1', type='sc-pc', rear_port=cls.patch_panel2_rp1, rear_port_position=1)
        cls.front_port2_2 = FrontPort.objects.create(device=cls.patch_panel2, name='FP2', type='sc-pc', rear_port=cls.patch_panel2_rp1, rear_port_position=2)

        # power
        cls.powerpanel1 = PowerPanel.objects.create(site=cls.site_a, name='POWERPANEL-A-1')
        cls.powerfeed1 = PowerFeed.objects.create(name="POWERFEED-A-1", power_panel=cls.powerpanel1)
        cls.powerfeed2 = PowerFeed.objects.create(name="POWERFEED-B-1", power_panel=cls.powerpanel1)

        cls.pdu_role = DeviceRole.objects.create(name='PDU', slug='pdu')
        cls.pdu_type = DeviceType.objects.create(model='Generic PDU', slug='generic-pdu', manufacturer=cls.generic_manufacturer)
        cls.pdu1 = Device.objects.create(name='PDU-A-1', device_type=cls.pdu_type, device_role=cls.pdu_role, site=cls.site_a)
        cls.pdu2 = Device.objects.create(name='PDU-B-1', device_type=cls.pdu_type, device_role=cls.pdu_role, site=cls.site_a)

        cls.pdu1_powerin = PowerPort.objects.create(device=cls.pdu1, name="power-in")
        cls.pdu2_powerin = PowerPort.objects.create(device=cls.pdu2, name="power-in")
        cls.pdu1_plug1 = PowerOutlet.objects.create(device=cls.pdu1, name="plug1", power_port=cls.pdu1_powerin)
        cls.pdu2_plug1 = PowerOutlet.objects.create(device=cls.pdu2, name="plug1", power_port=cls.pdu2_powerin)

        # circuits
        cls.generic_provider = Provider.objects.create(name='Generic Provider', slug='generic_provider')
        cls.provider_network1 = ProviderNetwork.objects.create(name='Provider Network 1', provider=cls.generic_provider)
        cls.mpls_circuit_type = CircuitType.objects.create(name='MPLS', slug='mpls')

        cls.circuit1 = Circuit.objects.create(provider=cls.generic_provider, type=cls.mpls_circuit_type, cid='MPLS-001')
        cls.circuit_termination_1_a = CircuitTermination.objects.create(circuit=cls.circuit1, site=cls.site_a, term_side='A')
        cls.circuit_termination_1_z = CircuitTermination.objects.create(circuit=cls.circuit1, site=cls.site_a, term_side='Z')

        cls.circuit2 = Circuit.objects.create(provider=cls.generic_provider, type=cls.mpls_circuit_type, cid='MPLS-002')
        cls.circuit_termination_2_a = CircuitTermination.objects.create(circuit=cls.circuit2, site=cls.site_a, term_side='A')
        cls.circuit_termination_2_z = CircuitTermination.objects.create(circuit=cls.circuit2, provider_network=cls.provider_network1, term_side='Z')

        # tags
        cls.tag_topo1 = Tag.objects.create(name='TOPO1', slug='topo1')
        cls.switch1.tags.add(cls.tag_topo1)
        cls.switch2.tags.add(cls.tag_topo1)
        cls.patch_panel1.tags.add(cls.tag_topo1)
        cls.patch_panel2.tags.add(cls.tag_topo1)
        cls.powerpanel1.tags.add(cls.tag_topo1)
        cls.powerfeed1.tags.add(cls.tag_topo1)
        cls.powerfeed2.tags.add(cls.tag_topo1)
        cls.pdu1.tags.add(cls.tag_topo1)
        cls.pdu2.tags.add(cls.tag_topo1)

    def assertNetboxModelsInTopology(self, netbox_models, topology):
        nodes_ids = sorted(map(BaseNode.get_uid, netbox_models))

        topology_nodes = sorted(map(lambda n : n.uid, topology.nodes()))

        self.assertEqual(nodes_ids, topology_nodes)

    def test_nodes_100(self):
        # Topology :
        #   [switch1] [pdu1] [powerfeed1] [powerpanel1]
        #   [switch2] [pdu2] [powerfeed2]
        #   [patch-panel1] [patch-panel2]
        #
        # Expected result :
        #   [switch1] [pdu1] [powerfeed1] [powerpanel1]
        #   [switch2] [pdu2] [powerfeed2]
        #   [patch-panel1] [patch-panel2]
        #
        self.patch_panel1_rp1_cable.delete() # remove cable between patchpanels rear-port

        queryset = Device.objects.filter(site=self.site_a)
        topology = Topology(
            show_circuit = True,
            show_power = True,
            hide_unconnected = False,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        all_topo1_nodes = [
            self.switch1,
            self.switch2,
            #self.powerfeed1,
            #self.powerfeed2,
            self.pdu1,
            self.pdu2,
            #self.powerpanel1,
            self.patch_panel1,
            self.patch_panel2
        ]
        self.assertNetboxModelsInTopology(all_topo1_nodes, topology)
        self.assertEqual(len(topology.edges()), 0)

    def test_hide_unconnected_100(self):
        # Topology :
        #   [switch1] [pdu1] [powerfeed1] [powerpanel1]
        #   [switch2] [pdu2] [powerfeed2]
        #   [patch-panel1|rp1] -- [rp1|patch-panel2]
        #
        # Expected result :
        #   [patch-panel1|rp1] -- [rp1|patch-panel2]
        #
        queryset = Device.objects.filter(site=self.site_a)
        topology = Topology(
            show_circuit = True,
            show_power = True,
            hide_unconnected = True,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.patch_panel1, self.patch_panel2], topology)
        self.assertEqual(len(topology.edges()), 1)

    def test_power_connections_100(self):
        # Topology :
        #   [switch1|psu0] -- [plug1|pdu1|power_in] -- [powerfeed1] -- [powerpanel1]
        #                                                                   /
        #   [switch2|psu0] -- [plug1|pdu2|power_in] -- [powerfeed2] -------
        #
        # Expected result :
        #   [switch1|psu0] -- [plug1|pdu1|power_in] -- [powerfeed1] -- [powerpanel1]
        #                                                                   /
        #   [switch2|psu0] -- [plug1|pdu2|power_in] -- [powerfeed2] -------
        #
        Cable(a_terminations=[self.pdu1_powerin],b_terminations=[self.powerfeed1]).save()
        Cable(a_terminations=[self.pdu2_powerin],b_terminations=[self.powerfeed2]).save()
        Cable(a_terminations=[self.pdu1_plug1],b_terminations=[self.switch1_psu]).save()
        Cable(a_terminations=[self.pdu2_plug1],b_terminations=[self.switch2_psu]).save()

        queryset = Device.objects.filter(site=self.site_a).exclude(device_role=self.patch_panel_role)
        topology = Topology(
            show_circuit = True,
            show_power = True,
            hide_unconnected = False,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.powerfeed1, self.powerfeed2, self.pdu1, self.pdu2, self.powerpanel1], topology)
        self.assertEqual(len(topology.edges()), 6)

    def test_switchs_directly_connected_101(self):
        # Topology :
        #   [switch1|if1] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [if1|switch2]
        #
        cable1 = Cable(a_terminations=[self.switch1_if1],b_terminations=[self.switch2_if1])
        cable1.save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = False,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2], topology)
        self.assertEqual(len(topology.edges()), 1)


    def test_switchs_connected_through_patch_panels_102(self):
        # Display patch-panels
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [[rp1|patch-panel2|fp1] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.switch2_if1],b_terminations=[self.front_port2_1, self.front_port2_2]).save()

        queryset = Device.objects.filter(site=self.site_a)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.patch_panel1, self.patch_panel2], topology)
        self.assertEqual(len(topology.edges()), 3)


    def test_switchs_connected_through_patch_panels_103(self):
        # Hide patch-panels
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.switch2_if1],b_terminations=[self.front_port2_1, self.front_port2_2]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2], topology)
        self.assertEqual(len(topology.edges()), 1)


    def test_switchs_connected_through_circuit_104(self):
        # Hide circuit
        #
        # Topology :
        #   [switch1|if1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.switch2_if1],b_terminations=[self.circuit_termination_1_z]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2], topology)
        self.assertEqual(len(topology.edges()), 1)

    def test_switchs_connected_through_circuit_105(self):
        # Show circuit
        #
        # Topology :
        #   [switch1|if1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.switch2_if1],b_terminations=[self.circuit_termination_1_z]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.circuit1], topology)
        self.assertEqual(len(topology.edges()), 2)
     

    def test_switchs_connected_through_circuit_and_passive_dev_105(self):
        # Display intermediate patch-panels and hide circuit
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.front_port2_1, self.front_port2_2],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.circuit_termination_1_z],b_terminations=[self.switch2_if1]).save()

        queryset = Device.objects.filter(site=self.site_a)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.patch_panel1, self.patch_panel2], topology)
        self.assertEqual(len(topology.edges()), 3)
    

    def test_switchs_connected_through_circuit_and_passive_dev_106(self):
        # Hide intermediate patch-panels and circuit
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.front_port2_1, self.front_port2_2],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.circuit_termination_1_z],b_terminations=[self.switch2_if1]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2], topology)
        self.assertEqual(len(topology.edges()), 1)


    def test_switchs_connected_through_circuit_and_passive_dev_107(self):
        # Hide intermediate patch-panels and show circuit
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.front_port2_1, self.front_port2_2],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.circuit_termination_1_z],b_terminations=[self.switch2_if1]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.circuit1], topology)
        self.assertEqual(len(topology.edges()), 2)


    def test_switchs_connected_through_circuit_and_passive_dev_108(self):
        # Show intermediate patch-panels and show circuit
        #
        # Topology :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        # Expected result :
        #   [switch1|if1] -- [fp1|patch-panel1|rp1] -- [rp1|patch-panel2|fp1] -- [A|circuit1|Z] -- [if1|switch2]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.front_port1_1, self.front_port1_2]).save()
        Cable(a_terminations=[self.front_port2_1, self.front_port2_2],b_terminations=[self.circuit_termination_1_a]).save()
        Cable(a_terminations=[self.circuit_termination_1_z],b_terminations=[self.switch2_if1]).save()

        queryset = Device.objects.filter(site=self.site_a)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.patch_panel1, self.patch_panel2, self.circuit1], topology)
        self.assertEqual(len(topology.edges()), 4)


    def test_switch_connected_to_provider_network_109(self):
        # Topology :
        #   [switch1|if1] -- [A|circuit2|Z] [provider_network]
        #
        # Expected result :
        #   [switch1|if1] -- [A|circuit2|Z] [provider_network]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.circuit_termination_2_a]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.circuit2, self.provider_network1], topology)
        self.assertEqual(len(topology.edges()), 2)

    def test_switchs_connected_to_same_provider_network_110(self):
        # Topology :
        #   [switch1|if1] -- [A|circuit2|Z] -- [provider_network1]
        #                                               /
        #   [switch2|if1] -- [A|circuit3|Z] ------------
        #
        # Expected result :
        #   [switch1|if1] -- [A|circuit2|Z] -- [provider_network1]
        #                                               /
        #   [switch2|if1] -- [Z|circuit3|A] ------------
        #
        circuit3 = Circuit.objects.create(provider=self.generic_provider, type=self.mpls_circuit_type, cid='MPLS-003')
        circuit_termination_3_z = CircuitTermination.objects.create(circuit=circuit3, site=self.site_a, term_side='Z')
        CircuitTermination.objects.create(circuit=circuit3, provider_network=self.provider_network1, term_side='A')
        
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.circuit_termination_2_a]).save()
        Cable(a_terminations=[self.switch2_if1],b_terminations=[circuit_termination_3_z]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.switch2, self.circuit2, circuit3, self.provider_network1], topology)
        self.assertEqual(len(topology.edges()), 4)

    def test_switch_connected_to_provider_network_111(self):
        # Hide circuit and show provider network
        # 
        # Topology :
        #   [switch1|if1] -- [A|circuit2|Z] -- [provider_network1]
        #
        # Expected result :
        #   [switch1|if1] -- [provider_network1]
        #
        Cable(a_terminations=[self.switch1_if1],b_terminations=[self.circuit_termination_2_a]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = True
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, self.provider_network1], topology)
        self.assertEqual(len(topology.edges()), 1)

    def test_switch_connected_to_incomplete_circuit_112(self):
        # Topology :
        #   [switch1|if1] -- [A|circuit3|Z]
        #
        # Expected result :
        #   [switch1|if1] -- [A|circuit3|Z]
        #
        circuit3 = Circuit.objects.create(provider=self.generic_provider, type=self.mpls_circuit_type, cid='MPLS-003')
        circuit_termination_3_a = CircuitTermination.objects.create(circuit=circuit3, site=self.site_a, term_side='A')

        Cable(a_terminations=[self.switch1_if1],b_terminations=[circuit_termination_3_a]).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = True,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)

        self.assertNetboxModelsInTopology([self.switch1, circuit3], topology)
        self.assertEqual(len(topology.edges()), 1)

    def test_switchs_connected_through_wirelesslink_112(self):
        # Topology :
        #   [switch1|if2] -- [wirelesslink] -- [if2|switch1]
        #
        # Expected result :
        #   [switch1|if2] -- [if2|switch1]
        #
        switch1_if2 = Interface.objects.create(device=self.switch1, name='Interface 2', type=InterfaceTypeChoices.TYPE_OTHER_WIRELESS)
        switch2_if2 = Interface.objects.create(device=self.switch2, name='Interface 2', type=InterfaceTypeChoices.TYPE_OTHER_WIRELESS)
        WirelessLink(interface_a=switch1_if2, interface_b=switch2_if2, ).save()

        queryset = Device.objects.filter(site=self.site_a, device_role=self.switch_role)
        topology = Topology(
            show_circuit = False,
            show_power = False,
            hide_unconnected = True,
            show_provider_network = False
        )
        topology.parse_queryset(queryset)
        
        self.assertNetboxModelsInTopology([self.switch1, self.switch2], topology)
        self.assertEqual(len(topology.edges()), 1)
