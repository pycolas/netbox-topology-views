from pathlib import Path
from typing import Optional
import itertools

from circuits.models import Circuit, CircuitTermination, ProviderNetwork
from dcim.models import (
    Cable,
    CableTermination,
    CabledObjectModel,
    ConsolePort,
    ConsoleServerPort,
    Device,
    device_components,
    DeviceRole,
    FrontPort,
    Interface,
    PowerFeed,
    PowerOutlet,
    PowerPanel,
    PowerPort,
    RearPort,
)
from wireless.models import WirelessLink
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.templatetags.static import static
from netbox.models.features import (
    ChangeLoggingMixin,
    ExportTemplatesMixin,
    WebhooksMixin,
)

from netbox_topology_views.utils import (
    CONF_IMAGE_DIR,
    IMAGE_DIR,
    Role,
    find_image_url,
    get_model_role,
    image_static_url,
)


class RoleImage(ChangeLoggingMixin, ExportTemplatesMixin, WebhooksMixin):
    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    objects: "models.Manager[RoleImage]"

    image = models.CharField("Path within the netbox static directory", max_length=255)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    __role: Optional[Role] = None

    @property
    def role(self) -> Role:
        if self.__role:
            return self.__role

        model_class = self.content_type.model_class()

        if not model_class:
            raise ValueError(f"Invalid content type: {self.content_type}")

        if model_class == DeviceRole:
            device_role: DeviceRole = DeviceRole.objects.get(pk=self.object_id)
            self.__role = Role(slug=device_role.slug, name=device_role.name)
            return self.__role

        self.__role = get_model_role(model_class)
        return self.__role

    def __str__(self):
        return f"{self.role} - {self.image}"

    def get_image(self) -> Path:
        """Get Icon

        returns the model's image's absolute path in the filesystem
        raises ValueError if the file cannot be found
        """
        path = Path(settings.STATIC_ROOT) / self.image

        if not path.exists():
            raise ValueError(f"{self.role} path '{path}' does not exists")

        return path

    def get_default_image(self, dir: Path = CONF_IMAGE_DIR):
        """Get default image

        will attempt to find image in given directory with any file extension,
        otherwise will try to find a `role-unknown` image

        fallback is `STATIC_ROOT/netbox_topology_views/img/role-unknown.png`
        """
        if url := find_image_url(self.role.slug, dir):
            return url

        # fallback to default role unknown image
        return image_static_url(IMAGE_DIR / "role-unknown.png")

    def get_image_url(self, dir: Path = CONF_IMAGE_DIR) -> str:
        try:
            self.get_image()
        except ValueError:
            return self.get_default_image(dir)
        return static(f"/{self.image}")



# Could inherit from django.model to store it in netbox database
class BaseNode:

    @classmethod
    def get_uid(cls, netbox_object):
        if isinstance(netbox_object, Device):
            return str(netbox_object.id)
        elif isinstance(netbox_object, Circuit):
            return f'c{netbox_object.id}'
        elif isinstance(netbox_object, ProviderNetwork):
            return f'pn{netbox_object.id}'
        elif isinstance(netbox_object, PowerPanel):
            return f'p{netbox_object.id}'
        elif isinstance(netbox_object, PowerFeed):
            return f'f{netbox_object.id}'
        else:
            raise NotImplementedError(f'Unsupported netbox model {type(netbox_object)}')

    def __init__(self, netbox_object):
        self.uid = self.get_uid(netbox_object)

        self.is_device = isinstance(netbox_object, Device)
        self.is_circuit = isinstance(netbox_object, Circuit)
        self.is_power_panel = isinstance(netbox_object, PowerPanel)
        self.is_power_feed = isinstance(netbox_object, PowerFeed)
        self.is_provider_network = isinstance(netbox_object, ProviderNetwork)

        if self.is_circuit:
            self.name = netbox_object.cid
        else:
            self.name = netbox_object.name
        
        self.netbox_object = netbox_object
        self.display = True
        self._edges = []
    
    def add_edge(self, edge):
        self._edges.append(edge)

    def has_edges(self):
        return len(self._edges) > 0
    
    def __str__(self):
        if self.is_circuit:
            return f'Circuit {self.netbox_object.cid}'
        elif self.is_provider_network:
            return f'ProviderNetwork {self.name}'
        elif self.is_power_panel:
            return f'PowerPanel {self.name}'
        elif self.is_power_feed:
            return f'PowerFeed {self.name}'
        elif self.name == None:
            return 'Unnamed'
        else:
            return self.name

# Could inherit from django.model to store it in netbox database
class Edge:
    def __init__(self, title, origin, destination, intermediates = None, link = None):
        self.title = title
        self.origin = origin
        self.destination = destination
        self.intermediates = intermediates
        self.link = link
    
    def has_intermediates(self):
        return self.intermediates != None and len(self.intermediates) > 0
    
    def has_link(self):
        return self.link != None

# Could inherit from django.model to store it in netbox database
# Maybe an abstract BaseTopology, with more specific models like L1Topology (physical view, like this one), 
# L2 Topology (Vlans..), L3 Topology, ..
# Or maybe a single class with some kind of layers ?
class Topology:

    def __init__(self, show_circuit = True, show_power = False, hide_unconnected = False, show_provider_network = True, save_coords = True):
        self.show_circuit = show_circuit
        self.show_power = show_power
        self.hide_unconnected = hide_unconnected
        self.show_provider_network = show_provider_network
        self.save_coords = save_coords

        self._device_ids = []
        self._site_ids = []
        self._nodes = {}
        self._edges = []
        self._cable = []

    def edges(self):
        return self._edges

    def get_all_nodes(self):
        return list(self._nodes.values())

    def get_visible_nodes(self):
        return list(filter(lambda n: n.display, self._nodes.values()))

    def parse_queryset(self, queryset):
        # cumulate results in case of multiple calls
        self._device_ids += [d.id for d in queryset]
        self._site_ids += [d.site_id for d in queryset]

        # Browse Pathendpoint
        console_ports = ConsolePort.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        console_srv_ports = ConsoleServerPort.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        power_ports = PowerPort.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        power_outlets = PowerOutlet.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        interfaces = Interface.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        path_endpoints = itertools.chain(console_ports, console_srv_ports, power_ports, power_outlets, interfaces)

        for endpoint in path_endpoints:
            self._browse_segments(endpoint.trace())

        # Browse remaining endpoints (hop by hop)
        rear_ports = RearPort.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        front_ports = FrontPort.objects.filter(device_id__in=self._device_ids, cable__isnull=False).select_related('device')
        endpoints = itertools.chain(rear_ports, front_ports)

        for endpoint in endpoints:
            segment = (endpoint.cable.a_terminations, [endpoint.cable], endpoint.cable.b_terminations)
            self._browse_segments([segment])

        # Wireless links
        wlan_links = WirelessLink.objects.filter( Q(_interface_a_device_id__in=self._device_ids) & Q(_interface_b_device_id__in=self._device_ids))

        for link in wlan_links:
            segment = ([link.interface_a], [link], [link.interface_b])
            self._browse_segments([segment])

        # Create nodes related to queryset and not discovered before
        for device in queryset:
            self._get_or_create_node(device)

        if self.show_power:
            power_panels = PowerPanel.objects.filter( Q(site_id__in=self._site_ids) )
            power_panels_ids = []
            for power_panel in power_panels:
                self._get_or_create_node(power_panel)
                power_panels_ids.append(power_panel.id)

            power_feeds = PowerFeed.objects.filter( Q(power_panel_id__in=power_panels_ids) )
            for power_feed in power_feeds:
                self._get_or_create_node(power_feed)
            
        if self.show_provider_network:
            # TODO : same with ProviderNetwork ?
            pass
        
        self._update_nodes_visibility()

    def _browse_segments(self, segments):
        origin = None
        origin_endpoints = None
        origin_cable = None
        destination = None
        destination_endpoints = None
        destination_cable = None
        segment_link = None # can be a circuit, cable...
        intermediates = {}

        results = self._parse_segments(segments)

        for (node, endpoints, link) in results:
            if not node.display :
                if node.uid not in intermediates:
                    intermediates[node.uid] = node
            else:
                if segment_link == None:
                    segment_link = link

                if origin_cable == None and isinstance(link, Cable):
                    origin_cable = link
                elif destination_cable == None and isinstance(link, Cable):
                    destination_cable = link

                if origin == None:
                    origin = node
                    origin_endpoints = endpoints

                elif destination == None:
                    destination = node
                    destination_endpoints = endpoints

                if origin and destination:
                    if ((origin_cable != None and origin_cable in self._cable) or (destination_cable != None and destination_cable in self._cable)):
                        continue
                    else:
                        self._cable.append(origin_cable)
                        if destination_cable != None and destination_cable != origin_cable:
                            self._cable.append(destination_cable)

                        edge = self._create_edge(origin, origin_endpoints, destination, destination_endpoints, segment_link, intermediates)
                        origin.add_edge(edge)
                        destination.add_edge(edge)
                        self._edges.append(edge)

                    # reset
                    origin = None
                    origin_endpoints = None
                    origin_cable = None
                    destination = None
                    destination_endpoints = None
                    destination_cable = None
                    segment_link = None 
                    intermediates = {}

    # TODO endpoints can be attached to different devices, so search for all nodes
    def _parse_segments(self, segments):
        for segment in segments:
            near_endpoints, links, far_endpoints = segment
            #print(segment)

            link = None
            if links != None and len(links) > 0:
                link = links[0]
            
            if isinstance(near_endpoints[0], CircuitTermination):
                yield (self._get_or_create_node(near_endpoints[0].circuit), near_endpoints, link)
            elif isinstance(near_endpoints[0], CabledObjectModel):
                yield (self._get_or_create_node(near_endpoints[0].device), near_endpoints, link)

            if isinstance(far_endpoints[0], CircuitTermination):
                yield (self._get_or_create_node(far_endpoints[0].circuit), far_endpoints, link)
            elif isinstance(far_endpoints[0], PowerFeed):
                power_feed_node = self._get_or_create_node(far_endpoints[0])
                yield (power_feed_node, [], link)

                if far_endpoints[0].power_panel:
                    power_panel_node = self._get_or_create_node(far_endpoints[0].power_panel)
                    yield (power_feed_node, [], None)
                    yield (power_panel_node, [], None)
            elif isinstance(far_endpoints[0], CabledObjectModel):
                yield (self._get_or_create_node(far_endpoints[0].device), far_endpoints, link)
            elif isinstance(far_endpoints[0], ProviderNetwork):
                yield (self._get_or_create_node(far_endpoints[0]), far_endpoints, far_endpoints[0])            

    def _create_edge(self, origin, origin_endpoints, destination, dest_endpoints, link, intermediates):
        if len(origin_endpoints) > 0:
            origin_endpoint_txt = f' [{",".join(map(str, origin_endpoints))}]'
        else:
            origin_endpoint_txt = ''

        if len(dest_endpoints) > 0:
            dest_endpoint_txt = f' [{",".join(map(str, dest_endpoints))}]'
        else:
            dest_endpoint_txt = ''

        title = f'Link between {origin}{origin_endpoint_txt} and {destination}{dest_endpoint_txt}'

        return Edge(title, origin, destination, intermediates, link)

    def _get_or_create_node(self, netbox_object):
        if netbox_object is None:
            return None
        else:
            uid = BaseNode.get_uid(netbox_object)

            if uid in self._nodes:
                return self._nodes[uid]
            else:
                node = BaseNode(netbox_object) 
                self._update_node_visibility(node, is_creation = True)
                self._nodes[uid] = node
                return node

    def _update_node_visibility(self, node, is_creation = False):
        if node.is_device:
            node.display = node.netbox_object.id in self._device_ids
        elif node.is_circuit:
            node.display = self.show_circuit
        elif node.is_provider_network:
            node.display = self.show_provider_network
        elif node.is_power_feed or node.is_power_panel:
            node.display = self.show_power

        if not is_creation and self.hide_unconnected and not node.has_edges():
            node.display = False

    def _update_nodes_visibility(self):
        for node in self._nodes.values():
            self._update_node_visibility(node)
