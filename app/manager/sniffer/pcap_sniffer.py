# -*- coding: utf-8 -*-

"""
*********************************************************************************
*                                                                               *
* pcap_sniffer.py -- Packet Capture (pcap)                                      *
*                                                                               *
* Methods and Classes to sniff the network traffic through pyshark.             *
*                                                                               *
* pyshark repository:                                                           *
* https://github.com/KimiNewt/pyshark                                           *
*                                                                               *
* pyshark license:                                                              *
* https://raw.githubusercontent.com/KimiNewt/pyshark/master/LICENSE.txt         *
*                                                                               *
********************** IMPORTANT BLACK-WIDOW LICENSE TERMS **********************
*                                                                               *
* This file is part of black-widow.                                             *
*                                                                               *
* black-widow is free software: you can redistribute it and/or modify           *
* it under the terms of the GNU General Public License as published by          *
* the Free Software Foundation, either version 3 of the License, or             *
* (at your option) any later version.                                           *
*                                                                               *
* black-widow is distributed in the hope that it will be useful,                *
* but WITHOUT ANY WARRANTY; without even the implied warranty of                *
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                 *
* GNU General Public License for more details.                                  *
*                                                                               *
* You should have received a copy of the GNU General Public License             *
* along with black-widow.  If not, see <http://www.gnu.org/licenses/>.          *
*                                                                               *
*********************************************************************************
"""

import pyshark

from pyshark.packet.fields import LayerField
from pyshark.packet.layer import Layer
from pyshark.packet.packet import Packet

from app.service import Log
from app.helper.util import regex_is_string
from app.helper.validators import is_hex

from .pcap_sniffer_util import MacManufacturer
from .pcap_sniffer_util import PcapLayerField


class PcapSniffer:
    """
    Packet Capture Manager
    """
    mac_manufacturer = None

    def __init__(
            self,
            filters: str = None,
            src_file: str = None,
            dest_file: str = None,
            interfaces: list = None,
            limit_length: int = None,
            pkt_count: int = None,
            callback=None
    ):
        """
        Packet capture method
        :param filters: https://wiki.wireshark.org/DisplayFilters
        :param src_file: Il file .pcap da cui leggere i pacchetti ascoltati (o None, per Live sniffing)
        :param dest_file: Il file in cui scrivere il .pcap dei pacchetti ascoltati (o None)
        :param interfaces: The list of interfaces to sniff (or None, to sniff all interfaces)
        :param limit_length: The limit length of each packet field (they will be truncated), or None
        :param pkt_count: Max packets to sniff, or None
        :param callback: The callback method to call (or None)
        """
        if PcapSniffer.mac_manufacturer is None:
            PcapSniffer.mac_manufacturer = MacManufacturer()
        self.count = 0  # Sniffed packets
        self.filters = filters
        self.src_file = src_file
        self.dest_file = dest_file
        self.limit_length = limit_length
        self.user_callback = callback
        self.interfaces = interfaces
        if src_file is not None:
            Log.info('Analyzing file: ' + src_file)
            self.capture = pyshark.FileCapture(
                input_file=src_file,
                display_filter=filters,
                output_file=dest_file,
                # include_raw=True,
                # use_json=True
                # debug=APP_DEBUG
            )
        else:
            Log.info('Analyzing live traffic')
            self.capture = pyshark.LiveCapture(
                interface=interfaces,
                display_filter=filters,
                output_file=dest_file,
                # include_raw=True,
                # use_json=True
                # debug=APP_DEBUG
            )
        self.capture.apply_on_packets(self._callback, packet_count=pkt_count)

    @staticmethod
    def sniff(
            filters: str = None,
            src_file: str = None,
            dest_file: str = None,
            interfaces: list = None,
            limit_length: int = None,
            pkt_count: int = None,
            callback=None
    ):
        """
        Packet capture method
        :param filters: https://wiki.wireshark.org/DisplayFilters
        :param src_file: Il file .pcap da cui leggere i pacchetti ascoltati (o None, per Live sniffing)
        :param dest_file: Il file in cui scrivere il .pcap dei pacchetti ascoltati (o None)
        :param interfaces: The list of interfaces to sniff (or None, to sniff all interfaces)
        :param limit_length: The limit length of each packet field (they will be truncated), or None
        :param pkt_count: Max packets to sniff, or None
        :param callback: The callback method to call (or None)
        :rtype: PcapSniffer
        """
        return PcapSniffer(filters, src_file, dest_file, interfaces, limit_length, pkt_count, callback)

    @staticmethod
    def print_pkt(pkt_dict: dict):
        """
        Print the pkt_dict
        :param pkt_dict: The pkt dict created by PcapSniffer._callback(pkt)
        """
        for key, value in pkt_dict.items():
            if key == 'layers':
                for layer_dict in value:
                    PcapSniffer._print_layer(layer_dict)
            elif key == 'frame_info':
                PcapSniffer._print_layer(value)
            else:
                print(str(key) + ': ' + str(value))

    def _callback(self, pkt: Packet):
        """
        :param pkt: The pyshark packet
        """
        pkt_dict = {
            'number': str(pkt.number),
            'time': str(pkt.frame_info.time_relative),
            # TODO: source
            # TODO: source_host
            # TODO: destination
            # TODO: destination_host
            # TODO: protocol
            'length': str(pkt.length),
            'captured_length': str(pkt.captured_length),
            'interface_captured': str(pkt.interface_captured),
            'highest_layer': str(pkt.highest_layer),
            'sniff_time': str(pkt.sniff_time),
            'sniff_timestamp': str(pkt.sniff_timestamp),
            'transport_layer': str(pkt.transport_layer),
            'frame_info': PcapSniffer._get_layer_dict(pkt.frame_info),
            'layers': []
        }
        for layer in pkt.layers:
            pkt_dict['layers'].append(PcapSniffer._get_layer_dict(layer))
        if self.user_callback is not None:
            self.user_callback(pkt_dict)
        else:
            PcapSniffer.print_pkt(pkt_dict)
        self.count += 1

    @staticmethod
    def _field_is_binary(field: PcapLayerField):
        field_label = field.label
        equal_index = field_label.find(' = ')
        binary_key = field_label[0:equal_index]
        return equal_index >= 0 and regex_is_string('^(\.| |0|1)+$', binary_key)

    # noinspection PyProtectedMember
    @staticmethod
    def _get_layer_dict(layer: Layer) -> (dict, dict):
        """
        TODO: Manage Tags + get src and dst ip/(mac & vendor)
        :param layer: The layer to process
        :return: The dictionary of layer, The dictionary of src and dest ip/mac (looked up)
        """

        field_tree = dict()  # tree dict { name => pkt }

        def update_field_tree_keys(local_field_tree_keys: list) -> (list, dict):
            """
            Insert into the field_tree the input keys recursively
            Eg. local_field_tree_keys = ['a', 'b', 'c']
                field_tree['a']['b']['c'] = dict()
            :param local_field_tree_keys: the dictionary keys used to create the parent dicts of field
            :return: The family (as list) and the node (as dict) of field to insert
            """
            local_field_node = field_tree
            local_field_tree_family = []
            for local_field_tree_key in local_field_tree_keys:
                local_field_tree_child = local_field_node.get(local_field_tree_key)
                if local_field_tree_child is None:
                    local_field_tree_child = dict()
                    local_field_node[local_field_tree_key] = local_field_tree_child
                local_field_tree_family.insert(0, local_field_tree_child)
                local_field_node = local_field_tree_child
            return local_field_tree_family, local_field_node

        pcap_layer_field_root = PcapLayerField(sanitized_name='root')

        # noinspection PyProtectedMember
        def local_get_field_tree(local_field: LayerField) -> PcapLayerField:
            """
            :param local_field: The LayerField to insert in dict
            """
            try:
                parent_poss = (int(local_field.pos), int(local_field.pos) - int(local_field.size))
            except TypeError:
                parent_poss = ()
                local_field.pos = 0
                local_field.size = 0

            if local_field.name is None:
                local_field.name = ''

            field_tree_keys = local_field.name.split('.')
            family, node = update_field_tree_keys(field_tree_keys)

            def find_pcap_layer_field_parent(local_member: dict, only_hex: bool = False) -> PcapLayerField or None:
                """
                If exists, found the big brother of local_field, otherwise, the parent
                :param local_member: The family tree of local_field (as dict)
                :param only_hex: True if the member_parent of local_field should has an hexadecimal value
                :return: If exits, the big brother of local_field, otherwise, the parent or None
                """
                parent = None
                for key, member_parent in local_member.items():
                    member_parent: PcapLayerField or dict
                    if not only_hex and isinstance(member_parent, dict):
                        # Check brothers
                        member_brother = find_pcap_layer_field_parent(member_parent, True)
                        if member_brother is not None:
                            return member_brother   # brother
                    if key in parent_poss and member_parent.name != local_field.name:
                        member_parent: PcapLayerField
                        if not only_hex:
                            parent = member_parent  # parent (but the preferred is brother)
                        elif is_hex(member_parent.value) and \
                                member_parent.pos == int(local_field.pos) and \
                                not PcapSniffer._field_is_binary(member_parent):
                            return member_parent    # brother
                return parent

            pcap_layer_field_parent = None
            for member in family:
                pcap_layer_field_parent = find_pcap_layer_field_parent(member)
                if pcap_layer_field_parent is not None:
                    break

            if pcap_layer_field_parent is None:
                pcap_layer_field_parent = pcap_layer_field_root

            local_field_sanitized_name = layer._sanitize_field_name(local_field.name)
            local_pcap_layer_field = PcapLayerField(
                local_field,
                local_field_sanitized_name,
                pcap_layer_field_parent
            )
            node[int(local_field.pos)] = local_pcap_layer_field  # Update dictionary tree
            return local_pcap_layer_field

        src_dest_dict = {
            'source': None,
            'source_host': None,
            'destination': None,
            'destination_host': None
        }

        field_insert = set()
        for field in layer._get_all_fields_with_alternates():
            field: LayerField
            field_unique_key = str(field.pos) + '_' + str(field.name)
            if field_unique_key in field_insert and False:
                continue
            pcap_layer_field = local_get_field_tree(field)
            if pcap_layer_field is not None:
                # TODO: check if pcap_layer_field is (src, dest) ip/mac
                field_insert.add(field_unique_key)

        return {
            'name': layer.layer_name.upper(),
            'fields': pcap_layer_field_root.get_dict().get('children')
        }

    @staticmethod
    def _print_layer(layer_dict: dict):
        """
        Print the layer_dict
        :param layer_dict: The layer dict created by PcapSniffer._callback(pkt)
        """
        print('Layer: ' + str(layer_dict.get('name')))
        for field_dict in layer_dict.get('fields'):
            PcapSniffer._print_field(field_dict)

    @staticmethod
    def _print_field(field_dict: dict, depth: int = 0):
        """
        Print the field_dict
        :param field_dict: The field dict returned by PcapLayerField.get_dict()
        """
        field_header = '   |' * depth + '   ├── '
        field_label = field_dict.get('label')
        field_key = field_header + '[ ' + str(field_label) + ' ]'
        field_value = field_dict.get('value')
        if field_value is None:
            field_value = ''
        if len(field_value) > 30:
            field_value = field_value[0:30] + '...'
        else:
            field_key += ' = '
        alternate_values = field_dict.get('alternate_values')
        if alternate_values is not None:
            field_key_len = len(field_key)
            for alternate_value in field_dict.get('alternate_values'):
                field_value += '\n' + (field_key_len * ' ') + alternate_value
        pos = str(field_dict.get('pos'))
        size = str(field_dict.get('size'))
        name = str(field_dict.get('name'))
        print(field_key + field_value + ' (pos=' + pos + ', size=' + size + ', name=' + name + ')')
        for field_child in field_dict.get('children'):
            PcapSniffer._print_field(field_child, depth + 1)
